"""
sigma/tests/test_sigma_guidance.py
Suite de tests — Sigma Guidance V0 (F72)

Vérifie :
- Boundary invariants (readonly, emits_act=False, decision_authority=KX108_ONLY)
- Les 8 règles de décision de compute_sigma_guidance()
- Absence de ACT / ALLOW / BLOCK dans tout output
- Les 4 modes de SigmaFeedbackMode
- brody_hint et obsidure_hint corrects selon le contexte

Scope : APPLY_SIGMA_GUIDANCE_V0
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sigma.sigma_guidance import (
    DECISION_AUTHORITY,
    FORBIDDEN_ACTIONS,
    SigmaAction,
    SigmaFeedbackDecision,
    SigmaFeedbackMode,
    SigmaGuidanceReport,
    SigmaIntrospectiveSearchResult,
    compute_sigma_guidance,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _guidance(
    contradictions=None,
    proof_status="OK",
    missing_context=None,
    layers_consulted=None,
    all_required_layers=None,
    report_field_count=5,
    is_critical_output=False,
) -> SigmaGuidanceReport:
    return compute_sigma_guidance(
        contradictions=contradictions or [],
        proof_status=proof_status,
        missing_context=missing_context or [],
        layers_consulted=layers_consulted if layers_consulted is not None else ["sigma"],
        all_required_layers=all_required_layers if all_required_layers is not None else ["sigma"],
        report_field_count=report_field_count,
        is_critical_output=is_critical_output,
    )


# ===========================================================================
# Test 1 — defaults non-sovereign
# ===========================================================================

def test_sigma_guidance_report_defaults_non_sovereign() -> None:
    r = SigmaGuidanceReport()
    assert r.readonly is True
    assert r.emits_act is False
    assert r.kernel_mutation is False
    assert r.decision_authority == DECISION_AUTHORITY
    assert r.recommended_action.value not in FORBIDDEN_ACTIONS


# ===========================================================================
# Test 2 — REQUEST_PROOF sur preuve manquante critique
# ===========================================================================

def test_sigma_recommends_request_proof_on_missing_proof() -> None:
    r = _guidance(
        proof_status="MISSING",
        layers_consulted=["sigma", "obsidure"],
        all_required_layers=["sigma", "obsidure"],
        is_critical_output=True,
    )
    assert r.recommended_action == SigmaAction.REQUEST_PROOF, (
        f"Attendu REQUEST_PROOF, obtenu {r.recommended_action}"
    )


# ===========================================================================
# Test 3 — REQUEST_TRACE sur contradiction unique non résolue
# ===========================================================================

def test_sigma_recommends_request_trace_on_unresolved_contradiction() -> None:
    r = _guidance(contradictions=["c1"])
    assert r.recommended_action == SigmaAction.REQUEST_TRACE, (
        f"Attendu REQUEST_TRACE pour 1 contradiction, obtenu {r.recommended_action}"
    )


def test_sigma_recommends_hold_on_multiple_contradictions() -> None:
    r = _guidance(contradictions=["c1", "c2"])
    assert r.recommended_action == SigmaAction.HOLD_RECOMMENDED, (
        f"Attendu HOLD_RECOMMENDED pour >1 contradiction, obtenu {r.recommended_action}"
    )


# ===========================================================================
# Test 4 — RELAUNCH_LAYER quand une couche manque
# ===========================================================================

def test_sigma_relaunches_layer_when_layer_missing() -> None:
    r = _guidance(
        layers_consulted=["sigma"],
        all_required_layers=["sigma", "obsidure"],
    )
    assert r.recommended_action == SigmaAction.RELAUNCH_LAYER, (
        f"Attendu RELAUNCH_LAYER, obtenu {r.recommended_action}"
    )
    assert r.recommended_layer_relaunch == "obsidure", (
        f"Attendu layer 'obsidure', obtenu {r.recommended_layer_relaunch}"
    )


# ===========================================================================
# Test 5 — STOP_UNKNOWN quand aucune couche + preuve inconnue
# ===========================================================================

def test_sigma_stop_unknown_when_no_useful_loop() -> None:
    # STOP_UNKNOWN : aucune couche consultée ET aucune couche requise disponible
    # (si all_required_layers contient des layers, R3 RELAUNCH_LAYER prendrait
    # la priorité — c'est le comportement correct).
    r = _guidance(
        proof_status="UNKNOWN",
        layers_consulted=[],
        all_required_layers=[],  # aucune couche à relancer → blocage réel
    )
    assert r.recommended_action == SigmaAction.STOP_UNKNOWN, (
        f"Attendu STOP_UNKNOWN, obtenu {r.recommended_action}"
    )
    assert r.stop_reason == "no_layer_no_proof"


# ===========================================================================
# Test 6 — Sigma ne produit JAMAIS ACT / ALLOW / BLOCK
# ===========================================================================

def test_sigma_never_emits_act_allow_block() -> None:
    scenarios = [
        dict(proof_status="OK",      layers_consulted=["sigma"], all_required_layers=["sigma"]),
        dict(proof_status="MISSING", layers_consulted=[],         all_required_layers=["sigma"], is_critical_output=True),
        dict(contradictions=["c1", "c2"], proof_status="FAILED",  layers_consulted=[], all_required_layers=["sigma"], is_critical_output=True),
        dict(missing_context=["ctx"], layers_consulted=["sigma"],  all_required_layers=["sigma"]),
        dict(proof_status="UNKNOWN", layers_consulted=[],          all_required_layers=["sigma"]),
    ]
    for kw in scenarios:
        r = _guidance(**kw)
        assert r.recommended_action.value not in FORBIDDEN_ACTIONS, (
            f"Action interdite '{r.recommended_action}' dans le scénario {kw}"
        )
        assert r.emits_act is False


# ===========================================================================
# Test 7 — x108_required=True pour sortie critique non-CONTINUE
# ===========================================================================

def test_sigma_sets_x108_required_for_critical_output() -> None:
    r = _guidance(
        contradictions=["c1", "c2"],
        proof_status="FAILED",
        is_critical_output=True,
    )
    assert r.x108_required is True


def test_sigma_x108_not_required_for_continue() -> None:
    r = _guidance(
        proof_status="OK",
        layers_consulted=["sigma"],
        all_required_layers=["sigma"],
        is_critical_output=True,  # critique mais action = CONTINUE
    )
    assert r.recommended_action == SigmaAction.CONTINUE
    assert r.x108_required is False


# ===========================================================================
# Test 8 — brody_hint présent pour rapport trop pauvre
# ===========================================================================

def test_sigma_brody_hint_present_for_response_issue() -> None:
    r = _guidance(
        proof_status="OK",
        layers_consulted=["sigma"],
        all_required_layers=["sigma"],
        report_field_count=2,  # < 3 → SLOW_DOWN
    )
    assert r.recommended_action == SigmaAction.SLOW_DOWN, (
        f"Attendu SLOW_DOWN pour report_field_count=2, obtenu {r.recommended_action}"
    )
    assert r.brody_hint == "response_too_sparse"


# ===========================================================================
# Test 9 — obsidure_hint présent pour problème de preuve
# ===========================================================================

def test_sigma_obsidure_hint_present_for_proof_issue() -> None:
    r = _guidance(
        proof_status="FAILED",
        layers_consulted=["sigma"],
        all_required_layers=["sigma"],
        is_critical_output=True,
    )
    assert r.obsidure_hint == "proof_surface_incomplete"


# ===========================================================================
# Test 10 — SigmaFeedbackMode : 4 modes, tous non-souverains
# ===========================================================================

def test_sigma_feedback_modes_no_loop_light_full_stop() -> None:
    assert len(SigmaFeedbackMode) == 4, (
        f"Attendu 4 modes, obtenu {len(SigmaFeedbackMode)}: {list(SigmaFeedbackMode)}"
    )
    expected_modes = {
        SigmaFeedbackMode.NO_LOOP,
        SigmaFeedbackMode.LIGHT_SIGMA,
        SigmaFeedbackMode.FULL_LOOP,
        SigmaFeedbackMode.STOP_UNKNOWN,
    }
    assert set(SigmaFeedbackMode) == expected_modes

    for mode in SigmaFeedbackMode:
        fd = SigmaFeedbackDecision(mode=mode)
        assert fd.emits_act is False, f"emits_act=True pour mode {mode}"
        assert fd.emits_verdict is False, f"emits_verdict=True pour mode {mode}"
        assert fd.kernel_mutation is False, f"kernel_mutation=True pour mode {mode}"
        assert fd.decision_authority == DECISION_AUTHORITY, (
            f"decision_authority incorrect pour mode {mode}"
        )


# ===========================================================================
# Tests additionnels — objets auxiliaires
# ===========================================================================

def test_sigma_introspective_search_result_defaults() -> None:
    r = SigmaIntrospectiveSearchResult()
    assert r.readonly is True
    assert r.emits_act is False
    assert r.decision_authority == DECISION_AUTHORITY
    assert r.sufficient_for_decision is False
    assert r.coverage_score == 0.0


def test_sigma_feedback_decision_defaults() -> None:
    fd = SigmaFeedbackDecision()
    assert fd.readonly is True
    assert fd.emits_act is False
    assert fd.emits_verdict is False
    assert fd.kernel_mutation is False
    assert fd.decision_authority == DECISION_AUTHORITY
    assert fd.max_relaunch_count == 1
    assert fd.mode == SigmaFeedbackMode.NO_LOOP


def test_sigma_hold_recommended_distinct_from_x108_hold() -> None:
    """HOLD_RECOMMENDED (Sigma) != HOLD (X108Gate) — namespaces séparés."""
    assert SigmaAction.HOLD_RECOMMENDED.value == "HOLD_RECOMMENDED"
    assert SigmaAction.HOLD_RECOMMENDED.value != "HOLD"


def test_forbidden_actions_complete() -> None:
    assert "ACT" in FORBIDDEN_ACTIONS
    assert "ALLOW" in FORBIDDEN_ACTIONS
    assert "BLOCK" in FORBIDDEN_ACTIONS
    assert "WRITE_MEMORY" in FORBIDDEN_ACTIONS
    assert "MUTATE_KERNEL" in FORBIDDEN_ACTIONS
    assert "AUTO_APPLY" in FORBIDDEN_ACTIONS


def test_sigma_request_context_when_missing_context() -> None:
    r = _guidance(
        missing_context=["brody_session", "domain_pack"],
        layers_consulted=["sigma"],
        all_required_layers=["sigma"],
    )
    assert r.recommended_action == SigmaAction.REQUEST_CONTEXT


def test_sigma_continue_nominal() -> None:
    r = _guidance(
        proof_status="OK",
        layers_consulted=["sigma"],
        all_required_layers=["sigma"],
        report_field_count=5,
        is_critical_output=False,
    )
    assert r.recommended_action == SigmaAction.CONTINUE
    assert r.x108_required is False
