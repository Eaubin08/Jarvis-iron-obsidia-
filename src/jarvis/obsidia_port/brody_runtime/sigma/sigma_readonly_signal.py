"""sigma/_w6a_signal_tmp.py -- Contrat SigmaReadonlySignal W6a.
Signal Sigma readonly non-souverain. Observations uniquement.
Aucun recommended_action. Aucune execution. Aucune decision.
SIGNAL COGNITIF = CONTEXTE.
palier: W6A
"""
from __future__ import annotations

from dataclasses import dataclass, field

_DECISION_AUTHORITY = "KX108_ONLY"
PALIER = "W6A"
COMPONENT = "SIGMA_READONLY_SIGNAL"


@dataclass
class SigmaReadonlySignal:
    signal_id: str
    contradictions: list[str] = field(default_factory=list)
    missing_context: list[str] = field(default_factory=list)
    proof_status: str = "UNKNOWN"

    readonly: bool = True
    advisory_only: bool = True
    context_signal_only: bool = True
    can_decide: bool = False
    can_emit_act: bool = False
    emits_act: bool = False
    emits_verdict: bool = False
    memory_write: bool = False
    graphiti_write: bool = False
    neo4j_write: bool = False
    kernel_mutation: bool = False
    x108_mutation: bool = False
    decision_authority: str = _DECISION_AUTHORITY


def build_sigma_readonly_signal(
    signal_id: str,
    contradictions: list[str],
    proof_status: str,
    missing_context: list[str],
) -> SigmaReadonlySignal:
    return SigmaReadonlySignal(
        signal_id=signal_id,
        contradictions=list(contradictions),
        missing_context=list(missing_context),
        proof_status=proof_status,
    )


__all__ = [
    "SigmaReadonlySignal",
    "build_sigma_readonly_signal",
]
