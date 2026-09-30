"""
brody_memory_human_validation_gate — V3 Block 3D
Readonly human validation gate dry-run. Takes a memory_candidate,
education_packet, and replay_packet, and produces a readonly
validation_decision_packet. No IO. No network. No canonical write.
No auto-accept. No ACT. DECISION_AUTHORITY=KX108_ONLY.
"""
from __future__ import annotations

import hashlib
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

# ── Validation statuses ───────────────────────────────────────────────────────
VSTATUS_PENDING_REVIEW = "pending_review"
VSTATUS_REJECT_ADVERSARIAL = "reject_adversarial"
VSTATUS_EDIT_REQUIRED = "edit_required"
VSTATUS_HOLD_REVIEW = "hold_review"
VSTATUS_ELIGIBLE_FUTURE = "eligible_for_future_human_acceptance"

# ── Validation actions (parallel to statuses) ─────────────────────────────────
_VALIDATION_ACTIONS: dict[str, str] = {
    VSTATUS_REJECT_ADVERSARIAL: "EXCLUDE_FROM_CANDIDATE_POOL",
    VSTATUS_EDIT_REQUIRED: "EDIT_AND_RESUBMIT",
    VSTATUS_HOLD_REVIEW: "HOLD_PENDING_HUMAN_REVIEW",
    VSTATUS_ELIGIBLE_FUTURE: "PRESENT_TO_HUMAN_VALIDATOR",
    VSTATUS_PENDING_REVIEW: "AWAIT_TRIAGE",
}

_REQUIRED_HUMAN_ACTIONS: dict[str, str] = {
    VSTATUS_REJECT_ADVERSARIAL: "Human must confirm exclusion and audit adversarial intent.",
    VSTATUS_EDIT_REQUIRED: "Human must review contradiction_tags and correct before resubmission.",
    VSTATUS_HOLD_REVIEW: "Human must inspect missing_data or weak_signal before any promotion.",
    VSTATUS_ELIGIBLE_FUTURE: (
        "Human must explicitly accept before any memory promotion. "
        "canonical_write remains False until explicit human write decision."
    ),
    VSTATUS_PENDING_REVIEW: "Human must triage and classify before any action.",
}


def _scrub(text: str) -> str:
    for pat in _SECRET_RE:
        text = pat.sub("[REDACTED]", text)
    return text


def _has_secret(text: str) -> bool:
    return any(pat.search(text) for pat in _SECRET_RE)


def _vd_id(candidate_id: str, timestamp: str) -> str:
    src = f"VD:{candidate_id}:{timestamp}"
    return "VD_" + hashlib.sha256(src.encode()).hexdigest()[:16].upper()


def _trunc(text: str, max_chars: int) -> str:
    return text[:max_chars] if len(text) > max_chars else text


def _detect_secret_in_candidate(candidate: dict) -> bool:
    """Check security_flags or raw fields for secret traces."""
    sf = candidate.get("security_flags", {})
    # Check all known key variants — candidate builder uses secret_in_msg/secret_in_resp,
    # trace extractor uses secret_in_message/secret_in_response.
    if (sf.get("secret_in_msg") or sf.get("secret_in_resp")
            or sf.get("secret_in_message") or sf.get("secret_in_response")):
        return True
    # Also check if SECRET_INJECTION_ATTEMPT is in risk_flags (set by candidate builder 3B)
    if "SECRET_INJECTION_ATTEMPT" in candidate.get("risk_flags", []):
        return True
    payload = candidate.get("candidate_payload", {})
    for field in ("message_excerpt", "response_excerpt"):
        if _has_secret(str(payload.get(field, ""))):
            return True
    if _has_secret(str(candidate.get("candidate_summary", ""))):
        return True
    return False


def _determine_validation_status(candidate: dict) -> str:
    """Determine validation status per Block 3D rules. Never auto-accepts."""
    ctype = candidate.get("candidate_type", "")
    sf = candidate.get("security_flags", {})
    is_adv = sf.get("is_adversarial", False)

    # Rule 1 — adversarial candidate
    if ctype == "adversarial_rejection_candidate" or is_adv:
        return VSTATUS_REJECT_ADVERSARIAL

    # Rule 2 — secret / token detected in candidate
    if _detect_secret_in_candidate(candidate):
        return VSTATUS_REJECT_ADVERSARIAL

    # Rule 4 — contradiction present → edit_required before hold
    if candidate.get("contradiction_tags"):
        return VSTATUS_EDIT_REQUIRED

    # Rule 3 — missing_data or boundary → hold_review
    if ctype == "boundary_candidate" or candidate.get("missing_proof_tags"):
        return VSTATUS_HOLD_REVIEW

    # Rule 7 — weak_signal → hold_review
    if ctype == "weak_signal_candidate":
        return VSTATUS_HOLD_REVIEW

    # dead_path → hold_review (safe; not ready for promotion)
    if ctype == "dead_path_candidate":
        return VSTATUS_HOLD_REVIEW

    # Rule 5+6 — clean education or replay candidate
    if ctype in (
        "education_candidate",
        "replay_candidate",
        "useful_path_candidate",
    ):
        return VSTATUS_ELIGIBLE_FUTURE

    # Fallback — unclassified
    return VSTATUS_PENDING_REVIEW


def _build_rejection_flags(candidate: dict, vstatus: str) -> list[str]:
    flags: list[str] = []
    if vstatus == VSTATUS_REJECT_ADVERSARIAL:
        if candidate.get("security_flags", {}).get("is_adversarial"):
            flags.append("adversarial_intent_detected")
        if _detect_secret_in_candidate(candidate):
            flags.append("secret_or_token_in_payload")
        if not flags:
            flags.append("adversarial_candidate_type")
    return flags


def _build_edit_required_fields(candidate: dict, vstatus: str) -> list[str]:
    if vstatus != VSTATUS_EDIT_REQUIRED:
        return []
    fields: list[str] = []
    if candidate.get("contradiction_tags"):
        fields.append("contradiction_tags")
    if candidate.get("missing_proof_tags"):
        fields.append("missing_proof_tags")
    return fields or ["candidate_payload"]


def _build_validation_reason(candidate: dict, vstatus: str) -> str:
    ctype = candidate.get("candidate_type", "unknown")
    prio = candidate.get("priority_score", 0.0)
    sf = candidate.get("security_flags", {})
    is_adv = sf.get("is_adversarial", False)

    if vstatus == VSTATUS_REJECT_ADVERSARIAL:
        if is_adv:
            return _scrub(
                f"Candidate type={ctype} flagged adversarial (is_adversarial=True). "
                "Excluded from candidate pool per invariant."
            )
        return _scrub(
            f"Candidate type={ctype} contains secret or token in payload. "
            "Excluded per security policy."
        )
    if vstatus == VSTATUS_EDIT_REQUIRED:
        ctags = candidate.get("contradiction_tags", [])
        return _scrub(
            f"Candidate type={ctype} has contradiction_tags={ctags[:2]}. "
            "Requires human review and correction before resubmission."
        )
    if vstatus == VSTATUS_HOLD_REVIEW:
        missing = candidate.get("missing_proof_tags", [])
        weak = candidate.get("weak_signal_tags", [])
        return _scrub(
            f"Candidate type={ctype} held: missing_proof={missing[:2]}, "
            f"weak_signal={weak[:2]}. Human inspection required."
        )
    if vstatus == VSTATUS_ELIGIBLE_FUTURE:
        return _scrub(
            f"Candidate type={ctype} priority={prio:.3f} is clean and "
            "eligible for future human acceptance. canonical_write=False until explicit "
            "human decision. No auto-promotion."
        )
    return _scrub(
        f"Candidate type={ctype} requires triage. status=pending_review."
    )


class BrodyMemoryHumanValidationGate:
    """
    Readonly human validation gate for Block 3D.
    Prepares a validation_decision_packet from memory_candidate +
    education_packet + replay_packet. Never writes. Never auto-accepts.
    canonical_write=False always. DECISION_AUTHORITY=KX108_ONLY.
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
    CANON_CANDIDATE_ALLOWED: bool = False
    BLOCK: str = "V3_BLOCK_3D"

    def prepare(
        self,
        *,
        memory_candidate: dict,
        education_packet: dict | None = None,
        replay_packet: dict | None = None,
        reviewer_state: dict | None = None,
        validation_request: dict | None = None,
    ) -> dict:
        """Produce a readonly validation_decision_packet. Never raises."""
        try:
            return self._prepare_inner(
                candidate=memory_candidate,
                ep=education_packet or {},
                rp=replay_packet or {},
                reviewer_state=reviewer_state or {},
                validation_request=validation_request or {},
            )
        except Exception as exc:
            return self._error_packet(memory_candidate, str(exc))

    def _prepare_inner(
        self,
        *,
        candidate: dict,
        ep: dict,
        rp: dict,
        reviewer_state: dict,
        validation_request: dict,
    ) -> dict:
        candidate_id = candidate.get("candidate_id", "MC_UNKNOWN")
        trace_id = candidate.get("trace_id", "TR_UNKNOWN")
        session_id = candidate.get("session_id", "")
        timestamp = candidate.get("timestamp", datetime.now(timezone.utc).isoformat())
        education_packet_id = ep.get("education_packet_id", "EP_NONE")
        replay_packet_id = rp.get("replay_packet_id", "RP_NONE")

        vstatus = _determine_validation_status(candidate)
        vaction = _VALIDATION_ACTIONS[vstatus]
        vreason = _build_validation_reason(candidate, vstatus)
        required_human_action = _REQUIRED_HUMAN_ACTIONS[vstatus]
        rejection_flags = _build_rejection_flags(candidate, vstatus)
        edit_required_fields = _build_edit_required_fields(candidate, vstatus)

        risk_flags = list(candidate.get("risk_flags", []))
        sf = candidate.get("security_flags", {})

        validation_packet_id = _vd_id(candidate_id, timestamp)

        return {
            # Identity
            "validation_packet_id": validation_packet_id,
            "candidate_id": candidate_id,
            "education_packet_id": education_packet_id,
            "replay_packet_id": replay_packet_id,
            "trace_id": trace_id,
            "session_id": session_id,
            "timestamp": timestamp,
            "block": "V3_BLOCK_3D",

            # Validation result
            "validation_status": vstatus,
            "validation_action": vaction,
            "validation_reason": vreason,
            "required_human_action": required_human_action,
            "risk_flags": risk_flags,
            "rejection_flags": rejection_flags,
            "edit_required_fields": edit_required_fields,

            # Canon gate — always False
            "canon_candidate_allowed": False,

            # Validation gate state
            "human_validation_required": True,
            "human_validation_state": "pending",

            # Security
            "security_flags": {
                "is_adversarial": sf.get("is_adversarial", False),
                "secret_in_msg": sf.get("secret_in_msg", False),
                "secret_in_resp": sf.get("secret_in_resp", False),
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

    def _error_packet(self, candidate: dict, error: str) -> dict:
        return {
            "validation_packet_id": "VD_ERROR_" + hashlib.sha256(
                error.encode()
            ).hexdigest()[:8].upper(),
            "candidate_id": candidate.get("candidate_id", "MC_UNKNOWN"),
            "education_packet_id": "EP_NONE",
            "replay_packet_id": "RP_NONE",
            "trace_id": candidate.get("trace_id", "TR_UNKNOWN"),
            "session_id": candidate.get("session_id", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "block": "V3_BLOCK_3D",
            "validation_status": "pending_review",
            "validation_action": "AWAIT_TRIAGE",
            "validation_reason": f"[ERROR] {_scrub(error)}",
            "required_human_action": "Human must inspect error before any action.",
            "risk_flags": ["gate_error"],
            "rejection_flags": [],
            "edit_required_fields": [],
            "canon_candidate_allowed": False,
            "human_validation_required": True,
            "human_validation_state": "pending",
            "security_flags": {"is_adversarial": False, "secret_in_msg": False, "secret_in_resp": False},
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


def prepare_validation_decision(
    *,
    memory_candidate: dict,
    education_packet: dict | None = None,
    replay_packet: dict | None = None,
    reviewer_state: dict | None = None,
    validation_request: dict | None = None,
) -> dict:
    """Module-level convenience wrapper. Never raises."""
    return BrodyMemoryHumanValidationGate().prepare(
        memory_candidate=memory_candidate,
        education_packet=education_packet,
        replay_packet=replay_packet,
        reviewer_state=reviewer_state,
        validation_request=validation_request,
    )
