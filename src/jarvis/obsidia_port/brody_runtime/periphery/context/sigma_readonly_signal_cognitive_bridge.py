"""
W6b -- Sigma readonly signal cognitive enrichment bridge.

Composable: SigmaReadonlySignal -> ContextPacketV2 (additive, never overwrites).
Not a standalone pipeline.
SIGNAL COGNITIF = CONTEXTE (W1 forensic verdict preserved).

Fields transferred:
  signal.signal_id      -> source_refs (append if absent), source_hashes (sha16)
  signal.contradictions -> contradictions (additive merge, order-stable, no dup)

Fields NOT transferred:
  signal.missing_context  NOT mapped -- SEMANTICALLY_DISTINCT from unknowns
  signal.proof_status     NOT mapped -- NO_DIRECT_MAPPING in ContextPacketV2
  governance flags        validated as preconditions only, never copied
"""
from __future__ import annotations

import dataclasses
import hashlib

from sigma.sigma_readonly_signal import SigmaReadonlySignal
from periphery.context.context_packet_builder_v2 import ContextPacketV2

_PFX = "SIGMA_READONLY_SIGNAL_COGNITIVE_BRIDGE"
_TYPE_ERR_SIGNAL = f"{_PFX}:SIGMA_READONLY_SIGNAL_TYPE_REQUIRED"
_TYPE_ERR_CONTEXT = f"{_PFX}:CONTEXT_PACKET_V2_TYPE_REQUIRED"
_SIGNAL_ID_EMPTY_ERR = f"{_PFX}:SIGNAL_ID_EMPTY"

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


def _validate_sigma_readonly_signal(signal: SigmaReadonlySignal) -> None:
    if not isinstance(signal, SigmaReadonlySignal):
        raise TypeError(_TYPE_ERR_SIGNAL)
    for attr, expected, err in _FLAG_CHECKS:
        if getattr(signal, attr) != expected:
            raise AssertionError(err)
    if signal.decision_authority != "KX108_ONLY":
        raise AssertionError(f"{_PFX}:DECISION_AUTHORITY_VIOLATED")
    if not signal.signal_id or not signal.signal_id.strip():
        raise ValueError(_SIGNAL_ID_EMPTY_ERR)


def _sha16(ref: str) -> str:
    return hashlib.sha256(ref.encode()).hexdigest()[:16]


def enrich_context_packet_v2_with_sigma_signal(
    context: ContextPacketV2,
    signal: SigmaReadonlySignal,
) -> ContextPacketV2:
    """
    W6b additive enrichment: merges SigmaReadonlySignal into an existing ContextPacketV2.

    Transferred:
      signal.signal_id      -> source_refs (append if absent), source_hashes (sha16)
      signal.contradictions -> contradictions (additive merge, order-stable, no dup)

    Not transferred:
      signal.missing_context (SEMANTICALLY_DISTINCT from unknowns)
      signal.proof_status    (NO_DIRECT_MAPPING in ContextPacketV2)
      governance flags       (validated as preconditions only)

    Preserved unchanged: query, language, context_items, dominant_trees,
    memory_status, retrieval_status, risk_flags, unknowns,
    forbidden_tokens_detected, and all governance invariants.
    """
    if not isinstance(context, ContextPacketV2):
        raise TypeError(_TYPE_ERR_CONTEXT)
    _validate_sigma_readonly_signal(signal)

    source_ref = signal.signal_id
    existing_refs = set(context.source_refs)
    new_refs = [source_ref] if source_ref not in existing_refs else []
    new_source_refs = list(context.source_refs) + new_refs
    new_source_hashes = list(context.source_hashes) + [_sha16(r) for r in new_refs]

    existing_contradictions = list(context.contradictions)
    existing_set = set(existing_contradictions)
    new_contradictions = existing_contradictions + [
        c for c in signal.contradictions if c not in existing_set
    ]

    return dataclasses.replace(
        context,
        source_refs=new_source_refs,
        source_hashes=new_source_hashes,
        contradictions=new_contradictions,
    )


__all__ = [
    "enrich_context_packet_v2_with_sigma_signal",
]
