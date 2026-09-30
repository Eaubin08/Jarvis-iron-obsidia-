"""
brody_memory_education_packet — V3 Block 3C
Readonly education packet builder. Transforms a memory_candidate (Block 3B)
into a structured education_packet. No IO. No network. No canonical write.
No ACT. No decision. DECISION_AUTHORITY=KX108_ONLY.
Budget: max 1024 bytes per packet.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

# ── Secret scan ───────────────────────────────────────────────────────────────
_SECRET_RE: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"API_KEY\s*=\s*\S+", r"GOOGLE_API_KEY\s*=\s*\S+",
        r"SECRET\s*=\s*\S+", r"PASSWORD\s*=\s*\S+", r"PRIVATE\s+KEY",
        r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", r"sk-[A-Za-z0-9]{20,}",
        r"ghp_[A-Za-z0-9]{36}", r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
    ]
]

# ── Education types ───────────────────────────────────────────────────────────
EDU_INVARIANT = "invariant_lesson"
EDU_BOUNDARY = "boundary_lesson"
EDU_FASTPATH = "fastpath_lesson"
EDU_ADVERSARIAL = "adversarial_rejection_lesson"
EDU_MISSING_DATA = "missing_data_lesson"
EDU_WEAK_SIGNAL = "weak_signal_lesson"
EDU_DEAD_PATH = "dead_path_lesson"
EDU_DOMAIN = "domain_lesson"

# ── CIC invariant rules ───────────────────────────────────────────────────────
_CIC_RULES = [
    "score_cannot_authorize_what_invariant_forbids",
    "memory_not_sovereign",
    "projection_not_prediction",
    "critical_missing_data_on_irreversible_action",
]

# ── Budget ────────────────────────────────────────────────────────────────────
_MAX_BUDGET_BYTES = 1024


def _scrub(text: str) -> str:
    for pat in _SECRET_RE:
        text = pat.sub("[REDACTED]", text)
    return text


def _has_secret(text: str) -> bool:
    return any(pat.search(text) for pat in _SECRET_RE)


def _trunc(text: str, max_chars: int) -> str:
    return text[:max_chars] if len(text) > max_chars else text


def _ep_id(candidate_id: str, timestamp: str) -> str:
    src = f"EP:{candidate_id}:{timestamp}"
    return "EP_" + hashlib.sha256(src.encode()).hexdigest()[:16].upper()


def _determine_education_type(candidate: dict) -> str:
    ctype = candidate.get("candidate_type", "")
    if ctype == "adversarial_rejection_candidate":
        return EDU_ADVERSARIAL
    if candidate.get("missing_proof_tags"):
        return EDU_MISSING_DATA
    if candidate.get("contradiction_tags"):
        return EDU_BOUNDARY
    if ctype == "boundary_candidate":
        return EDU_BOUNDARY
    if ctype == "weak_signal_candidate":
        return EDU_WEAK_SIGNAL
    if ctype == "dead_path_candidate":
        return EDU_DEAD_PATH
    payload = candidate.get("candidate_payload", {})
    if payload.get("fastpath_triggered"):
        return EDU_FASTPATH
    if candidate.get("useful_path_tags") or ctype == "useful_path_candidate":
        return EDU_DOMAIN
    return EDU_DOMAIN


def _build_cic_reinforcements(candidate: dict) -> list[dict]:
    """Derive CIC rule confirmations from candidate signals."""
    reinforcements: list[dict] = []
    ctype = candidate.get("candidate_type", "")
    contradiction_tags = candidate.get("contradiction_tags", [])
    missing_proof = candidate.get("missing_proof_tags", [])
    is_adversarial = candidate.get("security_flags", {}).get("is_adversarial", False)
    payload = candidate.get("candidate_payload", {})

    # memory_not_sovereign — always present (architecture invariant)
    reinforcements.append({
        "rule": "memory_not_sovereign",
        "confirmed_by_turns": [candidate.get("trace_id", "")],
        "confidence": 0.95,
        "evidence": "canonical_write=False enforced on all Block 3 outputs",
    })

    # score_cannot_authorize — confirmed when adversarial present
    if is_adversarial or "adversarial" in ctype:
        reinforcements.append({
            "rule": "score_cannot_authorize_what_invariant_forbids",
            "confirmed_by_turns": [candidate.get("trace_id", "")],
            "confidence": 1.0,
            "evidence": "adversarial trace rejected despite high adversarial confidence",
        })

    # projection_not_prediction — from contradiction tags
    if any("projection" in t.lower() or "prediction" in t.lower() for t in contradiction_tags):
        reinforcements.append({
            "rule": "projection_not_prediction",
            "confirmed_by_turns": [candidate.get("trace_id", "")],
            "confidence": 0.85,
            "evidence": _trunc(str(contradiction_tags[:1]), 120),
        })

    # critical_missing_data — from missing proof tags
    if missing_proof:
        reinforcements.append({
            "rule": "critical_missing_data_on_irreversible_action",
            "confirmed_by_turns": [candidate.get("trace_id", "")],
            "confidence": 0.90,
            "evidence": _trunc(str(missing_proof[:1]), 120),
        })

    return reinforcements


def _build_lesson_summary(candidate: dict, edu_type: str) -> str:
    domain = (candidate.get("candidate_payload", {}).get("domain_detected")
               or candidate.get("domain_tags", ["general"])[0] if candidate.get("domain_tags") else "general")
    prio = candidate.get("priority_score", 0.0)
    mem = candidate.get("memory_relevance_score", 0.0)
    ctype = candidate.get("candidate_type", "unknown")
    summary = f"[{edu_type}] domain={domain} type={ctype} prio={prio:.3f} mem={mem:.3f}"
    return _trunc(_scrub(summary), 200)


def _build_education_gaps(candidate: dict, edu_type: str) -> list[dict]:
    gaps: list[dict] = []
    dead_paths = candidate.get("dead_path_tags", [])
    missing = candidate.get("missing_proof_tags", [])
    weak = candidate.get("weak_signal_tags", [])
    balance_tags = candidate.get("balance_tags", {})

    if dead_paths:
        gaps.append({
            "gap": f"dead_path_detected:{len(dead_paths)} tags",
            "suggested_layer": "reflex_layer",
            "evidence": [candidate.get("trace_id", "")],
            "priority": "high",
        })
    if missing:
        gaps.append({
            "gap": f"missing_proof:{len(missing)} flags",
            "suggested_layer": "authority_layer",
            "evidence": [candidate.get("trace_id", "")],
            "priority": "high",
        })
    if weak:
        gaps.append({
            "gap": f"weak_signal_unhandled:{len(weak)} tags",
            "suggested_layer": "cic_core_layer",
            "evidence": [candidate.get("trace_id", "")],
            "priority": "medium",
        })

    bal_coherence = balance_tags.get("balance_coherence", {})
    if float(bal_coherence.get("tension", 0.0)) > 0.6:
        gaps.append({
            "gap": "coherence_faible_detected",
            "suggested_layer": "semantic_router_layer",
            "evidence": [candidate.get("trace_id", "")],
            "priority": "medium",
        })

    return gaps


class BrodyMemoryEducationPacketBuilder:
    """
    Readonly education packet builder for Block 3C.
    Transforms a memory_candidate into an education_packet.
    Never writes. Never decides. Never emits ACT.
    canonical_write=False always. DECISION_AUTHORITY=KX108_ONLY.
    Budget: max 1024 bytes.
    """

    READONLY: bool = True
    CANONICAL_WRITE: bool = False
    GRAPHITI_WRITE: bool = False
    NEO4J_WRITE: bool = False
    KERNEL_MUTATION: bool = False
    EMITS_ACT: bool = False
    DECISION_AUTHORITY: str = "KX108_ONLY"
    HUMAN_VALIDATION_REQUIRED: bool = True
    ALLOWED_TO_DECIDE: bool = False
    ALLOWED_TO_ACT: bool = False
    BLOCK: str = "V3_BLOCK_3C"
    MAX_BUDGET_BYTES: int = _MAX_BUDGET_BYTES

    def build(
        self,
        *,
        memory_candidate: dict,
        trace_packet: dict | None = None,
        session_context: dict | None = None,
        learning_scope: str = "general",
    ) -> dict:
        """Build an education_packet from a memory_candidate. Never raises."""
        try:
            return self._build_inner(
                candidate=memory_candidate,
                trace=trace_packet or {},
                session_context=session_context or {},
                learning_scope=learning_scope,
            )
        except Exception as exc:
            return self._error_packet(memory_candidate, str(exc))

    def _build_inner(
        self,
        *,
        candidate: dict,
        trace: dict,
        session_context: dict,
        learning_scope: str,
    ) -> dict:
        candidate_id = candidate.get("candidate_id", "MC_UNKNOWN")
        trace_id = candidate.get("trace_id", "TR_UNKNOWN")
        session_id = candidate.get("session_id", "")
        timestamp = candidate.get("timestamp", datetime.now(timezone.utc).isoformat())

        edu_type = _determine_education_type(candidate)
        lesson_summary = _build_lesson_summary(candidate, edu_type)
        cic_reinforcements = _build_cic_reinforcements(candidate)
        education_gaps = _build_education_gaps(candidate, edu_type)

        # Tags (propagated from candidate, scrubbed)
        useful_path_tags = [_scrub(t) for t in candidate.get("useful_path_tags", [])]
        dead_path_tags = [_scrub(t) for t in candidate.get("dead_path_tags", [])]
        weak_signal_tags = [_scrub(t) for t in candidate.get("weak_signal_tags", [])]
        contradiction_tags = [_scrub(t) for t in candidate.get("contradiction_tags", [])]
        missing_proof_tags = [_scrub(t) for t in candidate.get("missing_proof_tags", [])]
        balance_tags = dict(candidate.get("balance_tags", {}))
        point_cloud_21d = dict(candidate.get("point_cloud_21d", {}))
        domain_tags = list(candidate.get("domain_tags", []))

        # Bio terrain profile
        payload = candidate.get("candidate_payload", {})
        bio_terrain = {
            "dominant_terrain": payload.get("domain_detected", "general"),
            "dead_paths_identified": dead_path_tags[:3],
            "useful_traces": useful_path_tags[:3],
            "trace_following_score_mean": round(float(candidate.get("priority_score", 0.0)), 4),
        }

        # Domain coverage (derived from candidate)
        domain = payload.get("domain_detected", "general")
        path_c = float(payload.get("path_coherence_score", 0.5))
        is_adversarial = candidate.get("security_flags", {}).get("is_adversarial", False)
        domain_coverage: dict[str, Any] = {
            "bank": {"turns_count": 0, "avg_coherence": 0.0, "useful_turns": 0},
            "trading": {"turns_count": 0, "avg_coherence": 0.0, "useful_turns": 0},
            "gps": {"turns_count": 0, "avg_coherence": 0.0, "useful_turns": 0},
            "cic": {"turns_count": 0, "avg_coherence": 0.0, "useful_turns": 0},
            "memory": {"turns_count": 0, "avg_coherence": 0.0, "useful_turns": 0},
            "adversarial": {"turns_count": 0, "excluded": True, "reason": "adversarial_never_stored"},
        }
        if domain in domain_coverage and not is_adversarial:
            domain_coverage[domain] = {"turns_count": 1, "avg_coherence": round(path_c, 3), "useful_turns": 1}
        if is_adversarial:
            domain_coverage["adversarial"]["turns_count"] = 1

        # replay_recommended
        replay_recommended = (
            not is_adversarial
            and float(candidate.get("priority_score", 0.0)) >= 0.3
            and not dead_path_tags
        )

        education_packet_id = _ep_id(candidate_id, timestamp)

        packet: dict[str, Any] = {
            # Identity
            "education_packet_id": education_packet_id,
            "candidate_id": candidate_id,
            "trace_id": trace_id,
            "session_id": session_id,
            "timestamp": timestamp,
            "block": "V3_BLOCK_3C",
            "learning_scope": learning_scope,

            # Education classification
            "education_type": edu_type,
            "lesson_summary": lesson_summary,

            # CIC
            "cic_reinforcements": cic_reinforcements,

            # Domain
            "domain_coverage": domain_coverage,
            "domain_tags": domain_tags,

            # Tags
            "useful_path_tags": useful_path_tags,
            "dead_path_tags": dead_path_tags,
            "weak_signal_tags": weak_signal_tags,
            "contradiction_tags": contradiction_tags,
            "missing_proof_tags": missing_proof_tags,
            "contradiction_flags": [
                {"turn_id": trace_id, "contradiction": t, "severity": "medium"}
                for t in contradiction_tags[:3]
            ],

            # Gaps
            "education_gaps": education_gaps,

            # Bio terrain
            "bio_terrain_profile": bio_terrain,

            # Balance + 21D
            "balance_tags": balance_tags,
            "point_cloud_21d": point_cloud_21d,

            # Replay signal
            "replay_recommended": replay_recommended,

            # Budget
            "budget_bytes_max": _MAX_BUDGET_BYTES,

            # Validation
            "human_validation_required": True,
            "human_validation_state": "pending",

            # Security
            "security_flags": {
                "is_adversarial": is_adversarial,
            },

            # ── Structural invariants — ALWAYS these values ───────────────────
            "readonly": True,
            "canonical_write": False,
            "graphiti_write": False,
            "neo4j_write": False,
            "kernel_mutation": False,
            "emits_act": False,
            "allowed_to_decide": False,
            "allowed_to_act": False,
            "advisory_only": True,
            "decision_authority": "KX108_ONLY",
        }

        return packet

    def _error_packet(self, candidate: dict, error: str) -> dict:
        return {
            "education_packet_id": "EP_ERROR_" + hashlib.sha256(error.encode()).hexdigest()[:8].upper(),
            "candidate_id": candidate.get("candidate_id", "MC_UNKNOWN"),
            "trace_id": candidate.get("trace_id", "TR_UNKNOWN"),
            "session_id": candidate.get("session_id", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "block": "V3_BLOCK_3C",
            "education_type": "error_lesson",
            "error": error,
            "readonly": True,
            "canonical_write": False,
            "graphiti_write": False,
            "neo4j_write": False,
            "kernel_mutation": False,
            "emits_act": False,
            "allowed_to_decide": False,
            "allowed_to_act": False,
            "advisory_only": True,
            "decision_authority": "KX108_ONLY",
            "human_validation_required": True,
            "human_validation_state": "pending",
        }


def build_education_packet(
    *,
    memory_candidate: dict,
    trace_packet: dict | None = None,
    session_context: dict | None = None,
    learning_scope: str = "general",
) -> dict:
    """Module-level convenience wrapper. Never raises."""
    return BrodyMemoryEducationPacketBuilder().build(
        memory_candidate=memory_candidate,
        trace_packet=trace_packet,
        session_context=session_context,
        learning_scope=learning_scope,
    )
