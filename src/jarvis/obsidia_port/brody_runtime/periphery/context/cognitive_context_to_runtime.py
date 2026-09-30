"""
Cognitive Context -> runtime_wiring.ContextPacket adapter (W1 canonical join).

No AgentResult. No AgentLayer.COGNITIVE. No new admission gate.
Projection reuses context_packet_validation_projection (generic on ContextPacket).
evaluate_dry_run belongs to W2.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from periphery.context.context_packet_builder_v2 import ContextPacketV2
from periphery.context.agent_result_context_adapter import (
    context_packet_validation_projection,
)
from runtime_wiring.packet_types import ContextPacket

BOUNDARY = "COGNITIVE_CONTEXT_ADVISORY_ONLY"
SOURCE_STATUS = "CANDIDATE_ONLY"
CLAIM_SCOPE = "CONTEXT_SIGNAL_ONLY"
_SOURCE = "COGNITIVE_TREE_SIGNAL"
_NOTES = (
    "ContextPacketV2 -> runtime ContextPacket (W1 cognitive join). "
    "Context-only. KX108_ONLY. No agent. No act. No decision."
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_context_id(signal_id: str, packet_id: str) -> str:
    raw = json.dumps(
        {"signal_id": signal_id, "packet_id": packet_id},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    digest = hashlib.sha256(raw).hexdigest()[:20]
    return f"cp-cognitive-{digest}"


def _build_payload(v2: ContextPacketV2, signal_id: str) -> dict[str, Any]:
    d = v2.to_dict()
    d["action_id"] = signal_id
    d["_cognitive_context_join"] = True
    d["_context_signal_only"] = True
    d["_allowed_to_decide"] = False
    d["_allowed_to_act"] = False
    d["_memory_write"] = False
    d["_kernel_mutation"] = False
    d["_boundary"] = BOUNDARY
    d["_dry_run"] = True
    return d


def build_cognitive_runtime_packet(
    v2: ContextPacketV2,
    signal_id: str,
) -> ContextPacket:
    """
    Canonical W1 adapter: ContextPacketV2 -> runtime_wiring.ContextPacket.

    Raises TypeError/ValueError/AssertionError (fail-closed) on any
    sovereignty violation in the source V2 or on a missing signal_id.
    """
    if not isinstance(v2, ContextPacketV2):
        raise TypeError("COGNITIVE_RUNTIME_ADAPTER:CONTEXT_PACKET_V2_REQUIRED")
    if not signal_id or not signal_id.strip():
        raise ValueError("COGNITIVE_RUNTIME_ADAPTER:SIGNAL_ID_REQUIRED")
    if not v2.readonly:
        raise AssertionError("COGNITIVE_RUNTIME_ADAPTER:READONLY_VIOLATED")
    if not v2.context_signal_only:
        raise AssertionError("COGNITIVE_RUNTIME_ADAPTER:CONTEXT_SIGNAL_ONLY_VIOLATED")
    if v2.decision_authority != "KX108_ONLY":
        raise AssertionError("COGNITIVE_RUNTIME_ADAPTER:DECISION_AUTHORITY_VIOLATED")
    if v2.allowed_to_decide:
        raise AssertionError("COGNITIVE_RUNTIME_ADAPTER:ALLOWED_TO_DECIDE_VIOLATED")
    if v2.allowed_to_act:
        raise AssertionError("COGNITIVE_RUNTIME_ADAPTER:ALLOWED_TO_ACT_VIOLATED")
    if v2.kernel_mutation:
        raise AssertionError("COGNITIVE_RUNTIME_ADAPTER:KERNEL_MUTATION_VIOLATED")
    if v2.memory_write:
        raise AssertionError("COGNITIVE_RUNTIME_ADAPTER:MEMORY_WRITE_VIOLATED")
    labels = ["COGNITIVE_TREE_SIGNAL", "NON_SOVEREIGN", "READONLY_CONTEXT"]
    for flag in v2.risk_flags:
        labels.append(f"RISK:{flag}")
    context = ContextPacket(
        context_id=_make_context_id(signal_id, v2.packet_id),
        source=_SOURCE,
        source_status=SOURCE_STATUS,
        claim_scope=CLAIM_SCOPE,
        boundary=BOUNDARY,
        timestamp_or_tick=_utcnow(),
        advisory_only=True,
        readonly=True,
        runtime_allowed_now=False,
        emits_act=False,
        emits_decision=False,
        decision_authority="KX108_ONLY",
        labels=labels,
        payload=_build_payload(v2, signal_id),
        notes=_NOTES,
    )
    context.validate_invariants()
    return context


__all__ = [
    "build_cognitive_runtime_packet",
    "context_packet_validation_projection",
    "BOUNDARY",
    "SOURCE_STATUS",
    "CLAIM_SCOPE",
]
