"""
brody_memory_readonly_packet — V3 Block 3E
Helper: builds a complete v3_memory_readonly_packet in a single call.
Chains Block 3 modules: 3A trace -> 3B candidate -> 3C EP+RP -> 3D gate.
No IO. No network. No canonical write. No ACT. No decision.
DECISION_AUTHORITY=KX108_ONLY. api_debug_only=True.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

# ── Secret scan (defense-in-depth) ────────────────────────────────────────────
_SECRET_RE: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"API_KEY\s*=\s*\S+", r"GOOGLE_API_KEY\s*=\s*\S+",
        r"SECRET\s*=\s*\S+", r"PASSWORD\s*=\s*\S+", r"PRIVATE\s+KEY",
        r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", r"sk-[A-Za-z0-9]{20,}",
        r"ghp_[A-Za-z0-9]{36}", r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
    ]
]

_DEFERRED_BASE: dict = {
    "status": "DEFERRED",
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
    "api_debug_only": True,
    "block": "V3_BLOCK_3E",
}


def _scrub(text: str) -> str:
    for pat in _SECRET_RE:
        text = pat.sub("[REDACTED]", text)
    return text


class BrodyMemoryReadonlyPacketBuilder:
    """
    Builds a complete v3_memory_readonly_packet from a single entry point.
    Chains: trace_extractor (3A) -> candidate_builder (3B) ->
            education_packet + replay_packet (3C) -> validation_gate (3D).
    Never writes. Never decides. Never emits ACT.
    canonical_write=False always. DECISION_AUTHORITY=KX108_ONLY.
    api_debug_only=True — must only appear in debug/compact API responses.
    """

    READONLY: bool = True
    CANONICAL_WRITE: bool = False
    GRAPHITI_WRITE: bool = False
    NEO4J_WRITE: bool = False
    KERNEL_MUTATION: bool = False
    EMITS_ACT: bool = False
    ALLOWED_TO_DECIDE: bool = False
    ALLOWED_TO_ACT: bool = False
    DECISION_AUTHORITY: str = "KX108_ONLY"
    HUMAN_VALIDATION_REQUIRED: bool = True
    API_DEBUG_ONLY: bool = True
    BLOCK: str = "V3_BLOCK_3E"

    def build(
        self,
        *,
        message: str,
        response_text: str,
        v3_dryrun_packet: dict,
        session_id: str = "",
        timestamp: str = "",
        source_type: str = "pipeline",
    ) -> dict:
        """Build full readonly memory chain. Never raises — falls back to DEFERRED."""
        try:
            return self._build_inner(
                message=message,
                response_text=response_text,
                v3_dryrun_packet=v3_dryrun_packet,
                session_id=session_id,
                timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
                source_type=source_type,
            )
        except Exception as exc:
            pkt = dict(_DEFERRED_BASE)
            pkt["error"] = _scrub(str(exc))[:256]
            return pkt

    def _build_inner(
        self,
        *,
        message: str,
        response_text: str,
        v3_dryrun_packet: dict,
        session_id: str,
        timestamp: str,
        source_type: str,
    ) -> dict:
        # Lazy imports — avoid circular imports and keep module lightweight
        from apps.obsidia_api.brody_memory_trace_extractor import extract_memory_trace
        from apps.obsidia_api.brody_memory_candidate_builder import build_memory_candidate
        from apps.obsidia_api.brody_memory_education_packet import build_education_packet
        from apps.obsidia_api.brody_memory_replay_packet import build_replay_packet
        from apps.obsidia_api.brody_memory_human_validation_gate import prepare_validation_decision

        # 3A — trace extraction
        trace = extract_memory_trace(
            message=message,
            response_text=response_text,
            v3_dryrun_packet=v3_dryrun_packet,
            session_id=session_id,
            timestamp=timestamp,
            source_type=source_type,
        )

        # 3B — candidate builder
        candidate = build_memory_candidate(memory_trace_packet=trace)

        # 3C — education + replay packets
        ep = build_education_packet(memory_candidate=candidate)
        rp = build_replay_packet(memory_candidate=candidate)

        # 3D — validation gate (readonly decision packet)
        vd = prepare_validation_decision(
            memory_candidate=candidate,
            education_packet=ep,
            replay_packet=rp,
        )

        return {
            # Full Block 3 chain
            "memory_trace_packet": trace,
            "memory_candidate": candidate,
            "education_packet": ep,
            "replay_packet": rp,
            "validation_decision_packet": vd,

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
            "human_validation_required": True,
            "api_debug_only": True,
            "block": "V3_BLOCK_3E",
        }


def build_memory_readonly_packet(
    *,
    message: str,
    response_text: str,
    v3_dryrun_packet: dict,
    session_id: str = "",
    timestamp: str = "",
    source_type: str = "pipeline",
) -> dict:
    """Module-level convenience wrapper. Never raises."""
    return BrodyMemoryReadonlyPacketBuilder().build(
        message=message,
        response_text=response_text,
        v3_dryrun_packet=v3_dryrun_packet,
        session_id=session_id,
        timestamp=timestamp,
        source_type=source_type,
    )
