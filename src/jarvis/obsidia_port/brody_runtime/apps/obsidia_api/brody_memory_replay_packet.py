"""
brody_memory_replay_packet — V3 Block 3C
Readonly replay packet builder. Transforms a memory_candidate (Block 3B)
into a replay_packet for receipt_replay_layer in future sessions.
No IO. No network. No canonical write. No ACT. No decision.
DECISION_AUTHORITY=KX108_ONLY. Budget: max 1536 bytes.
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

# ── Replay types ──────────────────────────────────────────────────────────────
REPLAY_INVARIANT = "invariant_replay"
REPLAY_BOUNDARY = "boundary_replay"
REPLAY_ADVERSARIAL = "adversarial_rejection_replay"
REPLAY_MISSING_DATA = "missing_data_replay"
REPLAY_DOMAIN = "domain_replay"
REPLAY_FASTPATH = "fastpath_replay"
REPLAY_DEAD_PATH = "dead_path_replay"

# ── Budget ────────────────────────────────────────────────────────────────────
_MAX_BUDGET_BYTES = 1536
_PROMPT_MAX_CHARS = 100
_RESPONSE_MAX_CHARS = 200

# ── Forbidden transitions — always present in every replay packet ─────────────
_FORBIDDEN_TRANSITIONS: list[str] = [
    "ACT=YES",
    "canonical_write=True",
    "kernel_mutation=True",
    "graphiti_write=True",
    "neo4j_write=True",
    "emits_act=True",
    "allowed_to_decide=True",
    "allowed_to_act=True",
    "DECISION_AUTHORITY!=KX108_ONLY",
    "human_validation_bypass",
    "NCP_active=True",
    "scraping_active=True",
]


def _scrub(text: str) -> str:
    for pat in _SECRET_RE:
        text = pat.sub("[REDACTED]", text)
    return text


def _has_secret(text: str) -> bool:
    return any(pat.search(text) for pat in _SECRET_RE)


def _trunc(text: str, max_chars: int) -> str:
    return text[:max_chars] if len(text) > max_chars else text


def _rp_id(candidate_id: str, timestamp: str) -> str:
    src = f"RP:{candidate_id}:{timestamp}"
    return "RP_" + hashlib.sha256(src.encode()).hexdigest()[:16].upper()


def _determine_replay_type(candidate: dict) -> str:
    ctype = candidate.get("candidate_type", "")
    if ctype == "adversarial_rejection_candidate":
        return REPLAY_ADVERSARIAL
    if candidate.get("missing_proof_tags"):
        return REPLAY_MISSING_DATA
    if candidate.get("contradiction_tags"):
        return REPLAY_BOUNDARY
    if ctype == "boundary_candidate":
        return REPLAY_BOUNDARY
    payload = candidate.get("candidate_payload", {})
    if payload.get("fastpath_triggered"):
        return REPLAY_FASTPATH
    if ctype == "dead_path_candidate":
        return REPLAY_DEAD_PATH
    return REPLAY_DOMAIN


def _compute_replay_usefulness_score(candidate: dict) -> float:
    """Replay usefulness [0.0–1.0]. Adversarial always 0."""
    is_adv = candidate.get("security_flags", {}).get("is_adversarial", False)
    if is_adv:
        return 0.0

    prio = float(candidate.get("priority_score", 0.0))
    mem = float(candidate.get("memory_relevance_score", 0.0))
    has_useful = 1.0 if candidate.get("useful_path_tags") else 0.0
    has_dead = -0.3 if candidate.get("dead_path_tags") else 0.0

    raw = 0.5 * prio + 0.3 * mem + 0.2 * has_useful + has_dead
    return round(min(1.0, max(0.0, raw)), 4)


def _build_replay_steps(candidate: dict, replay_type: str) -> list[dict]:
    """Build structured replay steps from candidate signals."""
    steps: list[dict] = []
    payload = candidate.get("candidate_payload", {})
    is_adv = candidate.get("security_flags", {}).get("is_adversarial", False)

    # Step 1 — context injection (always)
    steps.append({
        "step": 1,
        "action": "inject_context",
        "description": "Inject candidate context into receipt_replay_layer",
        "readonly": True,
        "emits_act": False,
        "canonical_write": False,
    })

    # Step 2 — type-specific
    if is_adv:
        steps.append({
            "step": 2,
            "action": "flag_adversarial",
            "description": "Mark interaction as adversarial_rejection — exclude from candidate pool",
            "readonly": True,
            "emits_act": False,
            "canonical_write": False,
        })
    elif replay_type == REPLAY_MISSING_DATA:
        steps.append({
            "step": 2,
            "action": "highlight_missing_data",
            "description": "Surface missing_proof_tags to future session for HOLD detection",
            "readonly": True,
            "emits_act": False,
            "canonical_write": False,
        })
    elif replay_type == REPLAY_BOUNDARY:
        steps.append({
            "step": 2,
            "action": "surface_contradiction",
            "description": "Surface contradiction_tags and CIC boundary signals",
            "readonly": True,
            "emits_act": False,
            "canonical_write": False,
        })
    elif replay_type == REPLAY_FASTPATH:
        steps.append({
            "step": 2,
            "action": "preserve_fastpath_signal",
            "description": f"Preserve fastpath context: {payload.get('fastpath_type', 'unknown')}",
            "readonly": True,
            "emits_act": False,
            "canonical_write": False,
        })
    elif replay_type == REPLAY_DEAD_PATH:
        steps.append({
            "step": 2,
            "action": "mark_dead_path",
            "description": "Mark dead_path_tags to avoid in future sessions",
            "readonly": True,
            "emits_act": False,
            "canonical_write": False,
        })
    else:
        steps.append({
            "step": 2,
            "action": "enrich_domain_context",
            "description": f"Enrich domain context for {payload.get('domain_detected', 'general')}",
            "readonly": True,
            "emits_act": False,
            "canonical_write": False,
        })

    # Step 3 — human validation gate (always)
    steps.append({
        "step": 3,
        "action": "human_validation_gate",
        "description": "Present to human validation before any promotion. Status: pending.",
        "readonly": True,
        "emits_act": False,
        "canonical_write": False,
        "human_validation_required": True,
    })

    return steps


def _build_expected_invariants(candidate: dict) -> list[dict]:
    """List of invariants that must hold for this replay."""
    return [
        {"invariant": "memory_not_sovereign", "must_hold": True,
         "evidence": "canonical_write=False enforced"},
        {"invariant": "score_cannot_authorize_what_invariant_forbids", "must_hold": True,
         "evidence": "human_validation_required on all candidates"},
        {"invariant": "emits_act=False", "must_hold": True,
         "evidence": "no ACT path in Block 3C"},
        {"invariant": "readonly=True", "must_hold": True,
         "evidence": "Block 3C structural guarantee"},
    ]


def _build_replay_entry(candidate: dict, replay_type: str) -> dict:
    """Build a single replay entry from a candidate."""
    payload = candidate.get("candidate_payload", {})
    prompt_raw = payload.get("message_excerpt", "")
    response_raw = payload.get("response_excerpt", "")
    prompt_excerpt = _trunc(_scrub(prompt_raw), _PROMPT_MAX_CHARS)
    response_excerpt = _trunc(_scrub(response_raw), _RESPONSE_MAX_CHARS)

    layers_active = list(payload.get("active_layers", ["authority_layer", "cic_core_layer"])
                         if "active_layers" in payload else ["authority_layer", "cic_core_layer"])

    balance_tags = candidate.get("balance_tags", {})
    dominant_balance = "balance_memoire"
    max_tension = 0.0
    for bal_name, bal_data in balance_tags.items():
        if isinstance(bal_data, dict):
            t = float(bal_data.get("tension", 0.0))
            if t > max_tension:
                max_tension = t
                dominant_balance = bal_name

    return {
        "replay_id": f"RID_{candidate.get('candidate_id', 'MC_UNKNOWN')[:12]}",
        "turn_id": candidate.get("trace_id", "TR_UNKNOWN"),
        "prompt_excerpt": prompt_excerpt,
        "response_excerpt": response_excerpt,
        "layers_active": layers_active[:4],
        "dominant_balance": dominant_balance,
        "education_score": round(float(candidate.get("priority_score", 0.0)), 4),
        "cluster": candidate.get("candidate_type", "general"),
        "path_coherence_score": round(float(payload.get("path_coherence_score", 0.5)), 4),
        "domain": payload.get("domain_detected", "general"),
        "replay_value": "high" if float(candidate.get("priority_score", 0.0)) >= 0.5 else "medium",
        "readonly": True,
        "canonical_write": False,
        "emits_act": False,
    }


class BrodyMemoryReplayPacketBuilder:
    """
    Readonly replay packet builder for Block 3C.
    Transforms a memory_candidate into a replay_packet.
    Never writes. Never decides. Never emits ACT.
    canonical_write=False always. DECISION_AUTHORITY=KX108_ONLY.
    Budget: max 1536 bytes.
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
        replay_scope: str = "general",
    ) -> dict:
        """Build a replay_packet from a memory_candidate. Never raises."""
        try:
            return self._build_inner(
                candidate=memory_candidate,
                trace=trace_packet or {},
                replay_scope=replay_scope,
            )
        except Exception as exc:
            return self._error_packet(memory_candidate, str(exc))

    def _build_inner(
        self,
        *,
        candidate: dict,
        trace: dict,
        replay_scope: str,
    ) -> dict:
        candidate_id = candidate.get("candidate_id", "MC_UNKNOWN")
        trace_id = candidate.get("trace_id", "TR_UNKNOWN")
        session_id = candidate.get("session_id", "")
        timestamp = candidate.get("timestamp", datetime.now(timezone.utc).isoformat())
        is_adversarial = candidate.get("security_flags", {}).get("is_adversarial", False)

        replay_type = _determine_replay_type(candidate)
        replay_usefulness_score = _compute_replay_usefulness_score(candidate)
        replay_steps = _build_replay_steps(candidate, replay_type)
        expected_invariants = _build_expected_invariants(candidate)

        # Replay summary
        payload = candidate.get("candidate_payload", {})
        domain = payload.get("domain_detected", "general")
        ctype = candidate.get("candidate_type", "unknown")
        replay_summary = _trunc(
            _scrub(f"[{replay_type}] domain={domain} type={ctype} "
                   f"usefulness={replay_usefulness_score:.3f}"),
            200,
        )

        # Build replay entry (single entry per candidate in Block 3C)
        replay_entry = _build_replay_entry(candidate, replay_type)

        # Compute budget used
        replays_json = json.dumps([replay_entry], ensure_ascii=False)
        budget_bytes_used = len(replays_json.encode("utf-8"))

        # session_centroid_21D from point_cloud
        pc = candidate.get("point_cloud_21d", {})
        session_centroid = {k: v for k, v in pc.get("axes", {}).items()}

        replay_packet_id = _rp_id(candidate_id, timestamp)

        packet: dict[str, Any] = {
            # Identity
            "replay_packet_id": replay_packet_id,
            "candidate_id": candidate_id,
            "trace_id": trace_id,
            "session_id": session_id,
            "timestamp": timestamp,
            "block": "V3_BLOCK_3C",
            "replay_scope": replay_scope,

            # Type + summary
            "replay_type": replay_type,
            "replay_summary": replay_summary,

            # Steps + invariants
            "replay_steps": replay_steps,
            "expected_invariants": expected_invariants,
            "forbidden_transitions": _FORBIDDEN_TRANSITIONS,

            # Replay content
            "replays": [replay_entry],
            "replay_count": 1,
            "replay_usefulness_score": round(min(1.0, max(0.0, replay_usefulness_score)), 4),
            "replay_risk_flags": list(candidate.get("risk_flags", [])),

            # Budget
            "budget_bytes_used": budget_bytes_used,
            "budget_bytes_max": _MAX_BUDGET_BYTES,

            # Downstream
            "downstream_layer": "receipt_replay_layer",

            # 21D centroid
            "session_centroid_21D": session_centroid,

            # Validation
            "human_validation_required": True,
            "human_validation_state": "pending",

            # Security
            "security_flags": {"is_adversarial": is_adversarial},

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
            "replay_packet_id": "RP_ERROR_" + hashlib.sha256(error.encode()).hexdigest()[:8].upper(),
            "candidate_id": candidate.get("candidate_id", "MC_UNKNOWN"),
            "trace_id": candidate.get("trace_id", "TR_UNKNOWN"),
            "session_id": candidate.get("session_id", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "block": "V3_BLOCK_3C",
            "replay_type": "error_replay",
            "error": error,
            "replay_steps": [],
            "forbidden_transitions": _FORBIDDEN_TRANSITIONS,
            "replay_usefulness_score": 0.0,
            "replay_risk_flags": [],
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


def build_replay_packet(
    *,
    memory_candidate: dict,
    trace_packet: dict | None = None,
    replay_scope: str = "general",
) -> dict:
    """Module-level convenience wrapper. Never raises."""
    return BrodyMemoryReplayPacketBuilder().build(
        memory_candidate=memory_candidate,
        trace_packet=trace_packet,
        replay_scope=replay_scope,
    )
