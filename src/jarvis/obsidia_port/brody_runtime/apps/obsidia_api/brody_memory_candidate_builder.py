"""
brody_memory_candidate_builder — V3 Block 3B
Readonly candidate builder. Transforms a memory_trace_packet (Block 3A)
into a structured memory_candidate. No IO. No network. Provider-neutral.
No memory write. No canonical write. No ACT. DECISION_AUTHORITY=KX108_ONLY.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

# ── Secret scan patterns (re-used from trace extractor for independence) ──────
_SECRET_PATTERNS: list[str] = [
    r"API_KEY\s*=\s*\S+",
    r"GOOGLE_API_KEY\s*=\s*\S+",
    r"SECRET\s*=\s*\S+",
    r"PASSWORD\s*=\s*\S+",
    r"PRIVATE\s+KEY",
    r"Bearer\s+[A-Za-z0-9\-._~+/]+=*",
    r"sk-[A-Za-z0-9]{20,}",
    r"ghp_[A-Za-z0-9]{36}",
    r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
]

_SECRET_RE: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in _SECRET_PATTERNS
]

# ── Candidate types ───────────────────────────────────────────────────────────
CANDIDATE_TYPE_EDUCATION = "education_candidate"
CANDIDATE_TYPE_REPLAY = "replay_candidate"
CANDIDATE_TYPE_WEAK_SIGNAL = "weak_signal_candidate"
CANDIDATE_TYPE_DEAD_PATH = "dead_path_candidate"
CANDIDATE_TYPE_USEFUL_PATH = "useful_path_candidate"
CANDIDATE_TYPE_BOUNDARY = "boundary_candidate"
CANDIDATE_TYPE_ADVERSARIAL_REJECTION = "adversarial_rejection_candidate"

# ── Scoring weights ───────────────────────────────────────────────────────────
_W_MEM_RELEVANCE = 0.40
_W_PATH_COHERENCE = 0.30
_W_WEAK_SIGNAL = 0.15
_W_USEFUL_PATH = 0.15

# ── Summary budget (max bytes per candidate) ──────────────────────────────────
_MAX_SUMMARY_BYTES = 256


def _scrub_secrets(text: str) -> str:
    result = text
    for pat in _SECRET_RE:
        result = pat.sub("[REDACTED]", result)
    return result


def _contains_secret(text: str) -> bool:
    return any(pat.search(text) for pat in _SECRET_RE)


def _make_candidate_id(trace_id: str, candidate_type: str, timestamp: str) -> str:
    src = f"{trace_id}:{candidate_type}:{timestamp}"
    return "MC_" + hashlib.sha256(src.encode()).hexdigest()[:16].upper()


def _truncate_to_budget(text: str, max_bytes: int = _MAX_SUMMARY_BYTES) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore").rstrip() + "…"


def _compute_priority_score(trace: dict) -> float:
    """
    Priority score [0.0–1.0].
    Higher = more valuable as candidate.
    Adversarial traces always get 0.0 (rejected).
    """
    if trace.get("security_flags", {}).get("is_adversarial", False):
        return 0.0

    mem_score = float(trace.get("memory_relevance_score", 0.0))
    path_score = float(trace.get("path_coherence_score", 0.5))

    weak_signal_count = len(trace.get("weak_signal_tags", []))
    weak_bonus = min(1.0, weak_signal_count * 0.2)

    useful_path_count = len(trace.get("useful_path_tags", []))
    useful_bonus = min(1.0, useful_path_count * 0.2)

    # Penalty for risk and dead paths
    risk_flag_count = len(trace.get("risk_flags", []))
    dead_path_count = len(trace.get("dead_path_tags", []))
    penalty = min(0.5, risk_flag_count * 0.1 + dead_path_count * 0.1)

    raw = (
        _W_MEM_RELEVANCE * mem_score
        + _W_PATH_COHERENCE * path_score
        + _W_WEAK_SIGNAL * weak_bonus
        + _W_USEFUL_PATH * useful_bonus
        - penalty
    )
    return round(min(1.0, max(0.0, raw)), 4)


def _determine_candidate_type(trace: dict) -> str:
    """
    Determine candidate type from trace signals.
    Priority: adversarial → secret_detected → dead_path → boundary → weak_signal → replay → useful_path → education
    """
    sf = trace.get("security_flags", {})
    is_adversarial = sf.get("is_adversarial", False)
    if is_adversarial:
        return CANDIDATE_TYPE_ADVERSARIAL_REJECTION

    # Secret detected in original message/response (flag propagated from trace extractor 3A)
    if sf.get("secret_in_message") or sf.get("secret_in_response"):
        return CANDIDATE_TYPE_ADVERSARIAL_REJECTION

    has_dead_paths = bool(trace.get("dead_path_tags"))
    has_missing_proof = bool(trace.get("missing_data_flags"))
    has_contradiction = bool(trace.get("contradiction_flags"))
    has_weak_signal = bool(trace.get("weak_signal_tags"))
    has_useful_path = bool(trace.get("useful_path_tags"))
    fastpath_type = trace.get("fastpath_type")
    fastpath_triggered = bool(trace.get("fastpath_triggered", False))

    if has_missing_proof or has_contradiction:
        return CANDIDATE_TYPE_BOUNDARY

    if has_dead_paths and not has_useful_path:
        return CANDIDATE_TYPE_DEAD_PATH

    if has_weak_signal:
        return CANDIDATE_TYPE_WEAK_SIGNAL

    if fastpath_triggered and fastpath_type:
        fastpath_lower = (fastpath_type or "").lower()
        if "replay" in fastpath_lower or "gps" in fastpath_lower:
            return CANDIDATE_TYPE_REPLAY
        return CANDIDATE_TYPE_EDUCATION

    if has_useful_path:
        return CANDIDATE_TYPE_USEFUL_PATH

    return CANDIDATE_TYPE_EDUCATION


def _build_candidate_summary(trace: dict, candidate_type: str) -> str:
    """Build a compact summary within budget."""
    parts: list[str] = []

    domain = trace.get("domain_detected") or "general"
    intent = trace.get("intent_type") or "unknown"
    parts.append(f"[{candidate_type}] domain={domain} intent={intent}")

    msg = (trace.get("message_summary") or "")[:80]
    if msg:
        parts.append(f"msg={msg}")

    score = trace.get("memory_relevance_score", 0.0)
    path = trace.get("path_coherence_score", 0.0)
    parts.append(f"mem_score={score:.3f} path={path:.3f}")

    if trace.get("fastpath_type"):
        parts.append(f"fp={trace['fastpath_type']}")

    return _truncate_to_budget(" | ".join(parts))


class BrodyMemoryCandidateBuilder:
    """
    Readonly candidate builder for Block 3B.
    Transforms a memory_trace_packet into a memory_candidate.
    Never writes. Never decides. Never emits ACT.
    canonical_write=False always. DECISION_AUTHORITY=KX108_ONLY.
    """

    # Structural invariants — never mutable
    READONLY: bool = True
    CANONICAL_WRITE: bool = False
    MEMORY_WRITE: bool = False
    KERNEL_MUTATION: bool = False
    EMITS_ACT: bool = False
    DECISION_AUTHORITY: str = "KX108_ONLY"
    HUMAN_VALIDATION_REQUIRED: bool = True
    ALLOWED_TO_DECIDE: bool = False
    ALLOWED_TO_ACT: bool = False
    BLOCK: str = "V3_BLOCK_3B"

    def build(
        self,
        *,
        memory_trace_packet: dict,
        session_context: dict | None = None,
        source_confidence: float = 0.5,
        human_validation_state: str = "pending",
    ) -> dict:
        """
        Build a memory_candidate from a memory_trace_packet.
        Never raises — returns an error candidate on unexpected failure.
        """
        try:
            return self._build_inner(
                trace=memory_trace_packet,
                session_context=session_context or {},
                source_confidence=source_confidence,
                human_validation_state=human_validation_state,
            )
        except Exception as exc:
            return self._error_candidate(memory_trace_packet, str(exc))

    def _build_inner(
        self,
        *,
        trace: dict,
        session_context: dict,
        source_confidence: float,
        human_validation_state: str,
    ) -> dict:
        # ── 0. Propagate trace invariants — always override to safe values ────
        trace_id = trace.get("trace_id", "TR_UNKNOWN")
        session_id = trace.get("session_id", "")
        timestamp = trace.get("timestamp", datetime.now(timezone.utc).isoformat())

        # ── 1. Determine candidate type ───────────────────────────────────────
        candidate_type = _determine_candidate_type(trace)
        is_adversarial = trace.get("security_flags", {}).get("is_adversarial", False)

        # ── 2. Priority + relevance scores ────────────────────────────────────
        priority_score = _compute_priority_score(trace)
        memory_relevance_score = float(trace.get("memory_relevance_score", 0.0))
        source_confidence_clamped = round(min(1.0, max(0.0, float(source_confidence))), 4)

        # ── 3. Security scan on summary fields + propagate from trace flags ─────
        raw_msg_summary = trace.get("message_summary", "")
        raw_resp_summary = trace.get("response_summary", "")
        _trace_sf = trace.get("security_flags", {})
        # Propagate flags from trace extractor (detected on raw message before scrub).
        # The trace extractor sets secret_in_message=True before scrubbing message_summary,
        # so re-scanning the already-scrubbed summary alone would miss the original secret.
        _trace_secret_msg = bool(_trace_sf.get("secret_in_message", False))
        _trace_secret_resp = bool(_trace_sf.get("secret_in_response", False))
        msg_has_secret = _contains_secret(raw_msg_summary) or _trace_secret_msg
        resp_has_secret = _contains_secret(raw_resp_summary) or _trace_secret_resp
        safe_msg = _scrub_secrets(raw_msg_summary) if _contains_secret(raw_msg_summary) else raw_msg_summary
        safe_resp = _scrub_secrets(raw_resp_summary) if _contains_secret(raw_resp_summary) else raw_resp_summary

        # ── 4. Build candidate summary (budget-capped) ────────────────────────
        candidate_summary = _build_candidate_summary(
            {**trace, "message_summary": safe_msg, "response_summary": safe_resp},
            candidate_type,
        )

        # ── 5. Candidate payload (scrubbed, within budget) ────────────────────
        candidate_payload: dict[str, Any] = {
            "message_excerpt": _truncate_to_budget(safe_msg, 100),
            "response_excerpt": _truncate_to_budget(safe_resp, 150),
            "domain_detected": trace.get("domain_detected"),
            "intent_type": trace.get("intent_type"),
            "path_coherence_score": round(float(trace.get("path_coherence_score", 0.0)), 4),
            "fastpath_type": trace.get("fastpath_type"),
            "fastpath_triggered": bool(trace.get("fastpath_triggered", False)),
            "memory_required": bool(trace.get("memory_required", False)),
        }

        # ── 6. Tags (propagated from trace) ───────────────────────────────────
        domain_tags = list(trace.get("domain_detected", None) and [trace["domain_detected"]] or [])
        balance_tags = dict(trace.get("balance_tags_snapshot", {}))
        point_cloud_21d = dict(trace.get("point_cloud_21d_snapshot", {}))
        weak_signal_tags = list(trace.get("weak_signal_tags", []))
        dead_path_tags = list(trace.get("dead_path_tags", []))
        useful_path_tags = list(trace.get("useful_path_tags", []))
        missing_proof_tags = list(trace.get("missing_data_flags", []))
        contradiction_tags = list(trace.get("contradiction_flags", []))
        risk_flags = list(trace.get("risk_flags", []))

        # Adversarial rejection: explicitly mark
        if is_adversarial and "adversarial_excluded" not in dead_path_tags:
            dead_path_tags.append("adversarial_excluded")
        if is_adversarial and "adversarial_prompt" not in risk_flags:
            risk_flags.append("adversarial_prompt")
        # Secret injection attempt: mark even if not strictly adversarial intent
        if (msg_has_secret or resp_has_secret) and "SECRET_INJECTION_ATTEMPT" not in risk_flags:
            risk_flags.append("SECRET_INJECTION_ATTEMPT")

        # ── 7. Candidate ID ───────────────────────────────────────────────────
        candidate_id = _make_candidate_id(trace_id, candidate_type, timestamp)

        # ── 8. Assemble — invariants always last (cannot be overridden) ───────
        candidate: dict[str, Any] = {
            # Identity
            "candidate_id": candidate_id,
            "trace_id": trace_id,
            "session_id": session_id,
            "timestamp": timestamp,
            "block": "V3_BLOCK_3B",

            # Type + classification
            "candidate_type": candidate_type,
            "candidate_summary": candidate_summary,
            "candidate_payload": candidate_payload,

            # Tags
            "domain_tags": domain_tags,
            "balance_tags": balance_tags,
            "point_cloud_21d": point_cloud_21d,
            "weak_signal_tags": weak_signal_tags,
            "dead_path_tags": dead_path_tags,
            "useful_path_tags": useful_path_tags,
            "missing_proof_tags": missing_proof_tags,
            "contradiction_tags": contradiction_tags,
            "risk_flags": risk_flags,

            # Scores
            "memory_relevance_score": round(min(1.0, max(0.0, memory_relevance_score)), 4),
            "priority_score": round(min(1.0, max(0.0, priority_score)), 4),
            "source_confidence": source_confidence_clamped,

            # Validation
            "human_validation_required": True,
            "human_validation_state": human_validation_state,
            "validation_result": {
                "status": human_validation_state,
                "validated_by": None,
                "validation_timestamp": None,
            },

            # Security audit
            "security_flags": {
                "is_adversarial": is_adversarial,
                "secret_in_msg": msg_has_secret,
                "secret_in_resp": resp_has_secret,
                "scrubbed": msg_has_secret or resp_has_secret,
            },

            # ── Structural invariants — ALWAYS these values ───────────────────
            "readonly": True,
            "canonical_write": False,
            "memory_write": False,
            "kernel_mutation": False,
            "emits_act": False,
            "decision_authority": "KX108_ONLY",
            "allowed_to_decide": False,
            "allowed_to_act": False,
            "advisory_only": True,
        }

        return candidate

    def _error_candidate(self, trace: dict, error: str) -> dict:
        trace_id = trace.get("trace_id", "TR_UNKNOWN")
        ts = trace.get("timestamp", datetime.now(timezone.utc).isoformat())
        return {
            "candidate_id": _make_candidate_id(trace_id, "error", ts),
            "trace_id": trace_id,
            "session_id": trace.get("session_id", ""),
            "timestamp": ts,
            "block": "V3_BLOCK_3B",
            "candidate_type": "error_candidate",
            "error": error,
            "readonly": True,
            "canonical_write": False,
            "memory_write": False,
            "kernel_mutation": False,
            "emits_act": False,
            "decision_authority": "KX108_ONLY",
            "human_validation_required": True,
            "human_validation_state": "pending",
            "allowed_to_decide": False,
            "allowed_to_act": False,
            "advisory_only": True,
            "memory_relevance_score": 0.0,
            "priority_score": 0.0,
        }


def build_memory_candidate(
    *,
    memory_trace_packet: dict,
    session_context: dict | None = None,
    source_confidence: float = 0.5,
    human_validation_state: str = "pending",
) -> dict:
    """Module-level convenience wrapper. Never raises."""
    return BrodyMemoryCandidateBuilder().build(
        memory_trace_packet=memory_trace_packet,
        session_context=session_context,
        source_confidence=source_confidence,
        human_validation_state=human_validation_state,
    )
