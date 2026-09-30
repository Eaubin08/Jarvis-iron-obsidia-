"""
C8 -- AgentResult cognitive enrichment bridge.

Composable: AgentResult -> ContextPacketV2 (additive, never overwrites).
Not a standalone pipeline.
SIGNAL COGNITIF = CONTEXTE (W1 forensic verdict preserved).

Fields transferred:
  result.agent_id         -> source_refs + source_hashes (sha16)
  packet.action_id        -> source_refs + source_hashes (sha16)
  packet.evidence_refs    -> source_refs + source_hashes (sha16)
  packet.unknowns         -> unknowns
  packet.risk_flags       -> risk_flags
  packet.contradictions   -> contradictions
  packet.recommended_gate -> risk_flags as GATE_HINT:<value> if != "NONE"

Fields NOT transferred:
  result.layer
  packet.domain
  packet.extra_metrics
  result.notes

Governance flags are validated/preserved, never copied as authority.
"""

from __future__ import annotations

import dataclasses
import hashlib

from periphery.agent_contracts import AgentResult
from periphery.common import PeripheralSignalPacket
from periphery.context.context_packet_builder_v2 import ContextPacketV2


_PFX = "AGENT_RESULT_COGNITIVE_BRIDGE"
_TYPE_ERR_CONTEXT = f"{_PFX}:CONTEXT_PACKET_V2_TYPE_REQUIRED"
_TYPE_ERR_RESULT = f"{_PFX}:AGENT_RESULT_TYPE_REQUIRED"
_TYPE_ERR_PACKET = f"{_PFX}:PERIPHERAL_SIGNAL_PACKET_TYPE_REQUIRED"
_CAN_EMIT_ACT_ERR = f"{_PFX}:CAN_EMIT_ACT_VIOLATED"
_AGENT_ID_EMPTY_ERR = f"{_PFX}:AGENT_ID_EMPTY"
_ACTION_ID_EMPTY_ERR = f"{_PFX}:ACTION_ID_EMPTY"


def _sha16(ref: str) -> str:
    return hashlib.sha256(ref.encode()).hexdigest()[:16]


def _merge_unique(existing: list[str], incoming: list[str]) -> list[str]:
    """Additive, deterministic, order-stable deduplication."""
    result = list(existing)
    seen = set(result)

    for item in incoming:
        if item not in seen:
            result.append(item)
            seen.add(item)

    return result


def enrich_context_packet_v2_with_agent_result(
    context: ContextPacketV2,
    result: AgentResult,
) -> ContextPacketV2:
    """
    Add AgentResult information to ContextPacketV2 without mutating either input.

    NO_MAPPING:
      result.layer
      packet.domain
      packet.extra_metrics
      result.notes
    """

    if not isinstance(context, ContextPacketV2):
        raise TypeError(_TYPE_ERR_CONTEXT)

    if not isinstance(result, AgentResult):
        raise TypeError(_TYPE_ERR_RESULT)

    packet = result.packet

    if not isinstance(packet, PeripheralSignalPacket):
        raise TypeError(_TYPE_ERR_PACKET)

    # Fail closed on peripheral sovereignty before enrichment.
    result.assert_non_sovereign()

    if packet.can_emit_act:
        raise AssertionError(_CAN_EMIT_ACT_ERR)

    if not result.agent_id or not result.agent_id.strip():
        raise ValueError(_AGENT_ID_EMPTY_ERR)

    if not packet.action_id or not packet.action_id.strip():
        raise ValueError(_ACTION_ID_EMPTY_ERR)

    # Provenance: preserve alignment source_refs[i] <-> source_hashes[i].
    incoming_refs = [
        f"agent:{result.agent_id}",
        f"action:{packet.action_id}",
        *packet.evidence_refs,
    ]

    new_source_refs = list(context.source_refs)
    new_source_hashes = list(context.source_hashes)
    seen_refs = set(new_source_refs)

    for ref in incoming_refs:
        if ref not in seen_refs:
            new_source_refs.append(ref)
            new_source_hashes.append(_sha16(ref))
            seen_refs.add(ref)

    new_unknowns = _merge_unique(
        context.unknowns,
        packet.unknowns,
    )

    new_risk_flags = _merge_unique(
        context.risk_flags,
        packet.risk_flags,
    )

    new_contradictions = _merge_unique(
        context.contradictions,
        packet.contradictions,
    )

    # GateHint contract:
    # Literal["NONE", "HOLD", "BLOCK_CANDIDATE"]
    if packet.recommended_gate != "NONE":
        new_risk_flags = _merge_unique(
            new_risk_flags,
            [f"GATE_HINT:{packet.recommended_gate}"],
        )

    return dataclasses.replace(
        context,
        source_refs=new_source_refs,
        source_hashes=new_source_hashes,
        unknowns=new_unknowns,
        risk_flags=new_risk_flags,
        contradictions=new_contradictions,
    )


__all__ = [
    "enrich_context_packet_v2_with_agent_result",
]
