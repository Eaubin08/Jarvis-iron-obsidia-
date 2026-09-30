"""
W5 -- Tree Signal cognitive enrichment bridge.

Composable: TreeSignalPacket -> ContextPacketV2 (additive, never overwrites).
Maps dominant_ids (0-based dims) to canonical TREE_IDs (1-based, +1).
No patterns_detected, no active_domains, no memory_relevance, no world_relevance mapping.
SIGNAL COGNITIF = CONTEXTE (W1 forensic verdict preserved).
"""
from __future__ import annotations

import dataclasses
import hashlib

from periphery.cognitive_trees.tree_signal_packet import TreeSignalPacket
from periphery.context.context_packet_builder_v2 import ContextPacketV2

_PFX = "TREE_SIGNAL_COGNITIVE_BRIDGE"
_TYPE_ERR = f"{_PFX}:TREE_SIGNAL_PACKET_TYPE_REQUIRED"
_MAX_TREE_ID = 34

_FLAG_CHECKS: list[tuple[str, object, str]] = [
    ("readonly",            True,  f"{_PFX}:READONLY_VIOLATED"),
    ("advisory_only",       True,  f"{_PFX}:ADVISORY_ONLY_VIOLATED"),
    ("context_signal_only", True,  f"{_PFX}:CONTEXT_SIGNAL_ONLY_VIOLATED"),
    ("can_decide",          False, f"{_PFX}:CAN_DECIDE_VIOLATED"),
    ("can_emit_act",        False, f"{_PFX}:CAN_EMIT_ACT_VIOLATED"),
    ("emits_act",           False, f"{_PFX}:EMITS_ACT_VIOLATED"),
    ("emits_verdict",       False, f"{_PFX}:EMITS_VERDICT_VIOLATED"),
    ("memory_write",        False, f"{_PFX}:MEMORY_WRITE_VIOLATED"),
    ("graphiti_write",      False, f"{_PFX}:GRAPHITI_WRITE_VIOLATED"),
    ("neo4j_write",         False, f"{_PFX}:NEO4J_WRITE_VIOLATED"),
    ("kernel_mutation",     False, f"{_PFX}:KERNEL_MUTATION_VIOLATED"),
    ("x108_mutation",       False, f"{_PFX}:X108_MUTATION_VIOLATED"),
]


def _validate_tree_signal_packet(packet: TreeSignalPacket) -> None:
    if not isinstance(packet, TreeSignalPacket):
        raise TypeError(_TYPE_ERR)
    for attr, expected, err in _FLAG_CHECKS:
        if getattr(packet, attr) != expected:
            raise AssertionError(err)
    if packet.decision_authority != "KX108_ONLY":
        raise AssertionError(f"{_PFX}:DECISION_AUTHORITY_VIOLATED")
    for dim in packet.dominant_ids:
        if not isinstance(dim, int):
            raise TypeError(f"{_PFX}:DOMINANT_IDS_MUST_BE_INT")
        if dim < 0:
            raise ValueError(f"{_PFX}:DOMINANT_IDS_NEGATIVE:{dim}")
        tree_id = dim + 1
        if tree_id > _MAX_TREE_ID:
            raise ValueError(f"{_PFX}:DOMINANT_IDS_OUT_OF_RANGE:{dim}")


def _sha16(ref: str) -> str:
    return hashlib.sha256(ref.encode()).hexdigest()[:16]


def enrich_context_packet_v2_with_tree_signal(
    context: ContextPacketV2,
    packet: TreeSignalPacket,
) -> ContextPacketV2:
    _validate_tree_signal_packet(packet)

    canonical_tree_ids = [dim + 1 for dim in packet.dominant_ids]
    new_dominant_trees = list(dict.fromkeys([
        *context.dominant_trees,
        *canonical_tree_ids,
    ]))

    source_ref = packet.signal_id
    existing_refs = set(context.source_refs)
    new_refs = [source_ref] if source_ref not in existing_refs else []
    new_source_refs = list(context.source_refs) + new_refs
    new_source_hashes = list(context.source_hashes) + [_sha16(r) for r in new_refs]

    return dataclasses.replace(
        context,
        dominant_trees=new_dominant_trees,
        source_refs=new_source_refs,
        source_hashes=new_source_hashes,
    )
