"""
sigma/sigma_guidance.py — F72 Sigma Guidance V0

Sigma guides. Sigma does not decide.

Architecture :
- SigmaAction    : actions que Sigma peut *recommander* (jamais ACT/ALLOW/BLOCK)
- SigmaFeedbackMode : modes de boucle feedback (NO_LOOP par défaut)
- SigmaGuidanceReport         : rapport de guidance produit par Sigma
- SigmaIntrospectiveSearchResult : résultat d'introspection des couches
- SigmaFeedbackDecision       : décision de feedback (quelle boucle, quelles couches)
- compute_sigma_guidance()    : règles de décision V0

Boundary invariants (TOUS les objets) :
  decision_authority = KX108_ONLY
  readonly           = True
  emits_act          = False
  kernel_mutation    = False

HOLD_RECOMMENDED est une recommandation Sigma.
HOLD            est une décision X108 (sigma/contracts.py X108Gate).
Ces deux concepts ne doivent JAMAIS être confondus.

Palier : F72
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


PALIER = "F72"
COMPONENT = "SIGMA_GUIDANCE_READONLY"
DECISION_AUTHORITY = "KX108_ONLY"

# ── Actions autorisées ─────────────────────────────────────────────────────────

class SigmaAction(str, Enum):
    CONTINUE          = "CONTINUE"
    SLOW_DOWN         = "SLOW_DOWN"
    RELAUNCH_LAYER    = "RELAUNCH_LAYER"
    REQUEST_CONTEXT   = "REQUEST_CONTEXT"
    REQUEST_TRACE     = "REQUEST_TRACE"
    REQUEST_REPLAY    = "REQUEST_REPLAY"
    REQUEST_TEST      = "REQUEST_TEST"
    REQUEST_PROOF     = "REQUEST_PROOF"
    CHECK_INVARIANT   = "CHECK_INVARIANT"
    STOP_UNKNOWN      = "STOP_UNKNOWN"
    HOLD_RECOMMENDED  = "HOLD_RECOMMENDED"


# Actions explicitement interdites — Sigma ne les produit JAMAIS
FORBIDDEN_ACTIONS: frozenset[str] = frozenset({
    "ACT",
    "ALLOW",
    "BLOCK",
    "WRITE_MEMORY",
    "MUTATE_KERNEL",
    "AUTO_APPLY",
})


# ── Modes de feedback loop ─────────────────────────────────────────────────────

class SigmaFeedbackMode(str, Enum):
    NO_LOOP      = "NO_LOOP"       # Sigma observe, ne relance pas
    LIGHT_SIGMA  = "LIGHT_SIGMA"   # Sigma suggère un relaunch, attend X108
    FULL_LOOP    = "FULL_LOOP"     # Sigma retrace toutes les couches manquantes
    STOP_UNKNOWN = "STOP_UNKNOWN"  # Impossible de relancer utilement


# ── Objet 1 : SigmaGuidanceReport ─────────────────────────────────────────────

@dataclass
class SigmaGuidanceReport:
    """
    Rapport de guidance Sigma. Lecture seule. Ne décide pas.

    recommended_action est une RECOMMANDATION à destination de X108 ou de
    l'orchestrateur. Sigma ne produit jamais ACT / ALLOW / BLOCK.
    """
    report_id: str = "guidance-unknown"
    problem_id: str = "unknown"
    input_type: str = "unknown"                       # transaction / proof / context / trace
    affected_layers: List[str] = field(default_factory=list)
    missing_context: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    unstable_metrics: List[str] = field(default_factory=list)
    proof_status: str = "UNKNOWN"                     # OK / MISSING / PARTIAL / FAILED / UNKNOWN
    recommended_action: SigmaAction = SigmaAction.HOLD_RECOMMENDED
    recommended_layer_relaunch: Optional[str] = None
    stop_reason: Optional[str] = None
    brody_hint: Optional[str] = None                  # hint pour la couche réponse Brody
    obsidure_hint: Optional[str] = None               # hint pour la couche preuve Obsidure
    x108_required: bool = False
    confidence: float = 0.0
    # Boundary invariants — ne jamais modifier
    readonly: bool = True
    emits_act: bool = False
    kernel_mutation: bool = False
    decision_authority: str = DECISION_AUTHORITY


# ── Objet 2 : SigmaIntrospectiveSearchResult ──────────────────────────────────

@dataclass
class SigmaIntrospectiveSearchResult:
    """
    Résultat d'une introspection des couches disponibles.
    Lecture seule. Ne produit aucune décision.
    """
    search_id: str = "search-unknown"
    query: str = ""
    layers_consulted: List[str] = field(default_factory=list)
    layers_missing: List[str] = field(default_factory=list)
    proof_refs_found: List[str] = field(default_factory=list)
    context_fragments: List[str] = field(default_factory=list)
    contradiction_traces: List[str] = field(default_factory=list)
    coverage_score: float = 0.0      # 0.0 = aucune couverture, 1.0 = complète
    sufficient_for_decision: bool = False
    # Boundary
    readonly: bool = True
    emits_act: bool = False
    decision_authority: str = DECISION_AUTHORITY


# ── Objet 3 : SigmaFeedbackDecision ───────────────────────────────────────────

@dataclass
class SigmaFeedbackDecision:
    """
    Décision de feedback Sigma : quelle boucle activer, quelles couches relancer.
    Sigma ne décide pas — il recommande le mode et les couches.
    max_relaunch_count=1 par défaut pour éviter les boucles infinies.
    """
    feedback_id: str = "feedback-unknown"
    problem_id: str = "unknown"
    mode: SigmaFeedbackMode = SigmaFeedbackMode.NO_LOOP
    recommended_action: SigmaAction = SigmaAction.HOLD_RECOMMENDED
    layers_to_relaunch: List[str] = field(default_factory=list)
    max_relaunch_count: int = 1
    relaunch_condition: Optional[str] = None
    stop_reason: Optional[str] = None
    x108_required: bool = False
    # Boundary invariants — ne jamais modifier
    readonly: bool = True
    emits_act: bool = False
    emits_verdict: bool = False
    kernel_mutation: bool = False
    decision_authority: str = DECISION_AUTHORITY


# ── Règles de décision Sigma V0 ───────────────────────────────────────────────

def compute_sigma_guidance(
    contradictions: List[str],
    proof_status: str,
    missing_context: List[str],
    layers_consulted: List[str],
    all_required_layers: List[str],
    report_field_count: int,
    is_critical_output: bool,
    report_id: str = "guidance-unknown",
    problem_id: str = "unknown",
) -> SigmaGuidanceReport:
    """
    Calcule un SigmaGuidanceReport selon les règles V0.

    Sigma recommande — X108 tranche.

    Priorité des règles :
      R1 contradiction non résolue       → HOLD_RECOMMENDED (>1) ou REQUEST_TRACE (1)
      R2 preuve manquante critique        → REQUEST_PROOF
      R3 couche utile non consultée       → RELAUNCH_LAYER
      R4 contexte insuffisant             → REQUEST_CONTEXT
      R5 rapport trop pauvre              → SLOW_DOWN
      R6 rien de relançable utilement     → STOP_UNKNOWN
      R7 (transverse) sortie critique     → x108_required=True
      R8 cas nominal                      → CONTINUE
    """
    action = SigmaAction.CONTINUE
    stop_reason: Optional[str] = None
    x108_required: bool = False
    relaunch_layer: Optional[str] = None
    obsidure_hint: Optional[str] = None
    brody_hint: Optional[str] = None

    # R1 — contradiction non résolue
    if contradictions:
        action = (
            SigmaAction.HOLD_RECOMMENDED
            if len(contradictions) > 1
            else SigmaAction.REQUEST_TRACE
        )

    # R2 — preuve manquante sur action critique
    elif proof_status in ("MISSING", "FAILED") and is_critical_output:
        action = SigmaAction.REQUEST_PROOF
        obsidure_hint = "proof_surface_incomplete"

    # R3 — couche utile non consultée
    else:
        missing_layers = [
            layer for layer in all_required_layers
            if layer not in layers_consulted
        ]
        if missing_layers:
            action = SigmaAction.RELAUNCH_LAYER
            relaunch_layer = missing_layers[0]

        # R4 — contexte insuffisant
        elif missing_context:
            action = SigmaAction.REQUEST_CONTEXT

        # R5 — rapport trop pauvre
        elif report_field_count < 3:
            action = SigmaAction.SLOW_DOWN
            brody_hint = "response_too_sparse"

        # R6 — impossible de relancer utilement
        elif not layers_consulted and proof_status == "UNKNOWN":
            action = SigmaAction.STOP_UNKNOWN
            stop_reason = "no_layer_no_proof"

    # R7 — sortie critique requiert autorité X108
    if is_critical_output and action not in (
        SigmaAction.CONTINUE,
        SigmaAction.SLOW_DOWN,
    ):
        x108_required = True

    # Garde-fou absolu — Sigma ne produit JAMAIS une action interdite
    assert action.value not in FORBIDDEN_ACTIONS, (
        f"SIGMA_BOUNDARY_VIOLATION: action interdite '{action.value}'"
    )

    return SigmaGuidanceReport(
        report_id=report_id,
        problem_id=problem_id,
        recommended_action=action,
        recommended_layer_relaunch=relaunch_layer,
        stop_reason=stop_reason,
        brody_hint=brody_hint,
        obsidure_hint=obsidure_hint,
        x108_required=x108_required,
        contradictions=list(contradictions),
        missing_context=list(missing_context),
        proof_status=proof_status,
        confidence=0.0,
    )


__all__ = [
    "PALIER",
    "COMPONENT",
    "DECISION_AUTHORITY",
    "FORBIDDEN_ACTIONS",
    "SigmaAction",
    "SigmaFeedbackMode",
    "SigmaGuidanceReport",
    "SigmaIntrospectiveSearchResult",
    "SigmaFeedbackDecision",
    "compute_sigma_guidance",
]
