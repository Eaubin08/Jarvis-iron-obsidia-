"""
Bounded pre-reasoning cognitive calibration.

Historical cognitive roles formalized as one readonly pipeline:

C265 - sense -> symbolic integration
C266 - symbolic alignment
C273 - divergence detection
C274 - calibration before reasoning

This component:
- consumes already-produced lexical / IR signals,
- performs no retrieval,
- performs no action,
- emits no sovereign verdict,
- never mutates kernel/X108,
- remains KX108_ONLY.
"""

from __future__ import annotations

from typing import Any


_STAGE_ORDER = [
    "C265",
    "C266",
    "C273",
    "C274",
]


def _uniq_strings(values: Any) -> list[str]:
    out: list[str] = []

    if not isinstance(values, list):
        return out

    for value in values:
        text = str(value or "").strip()

        if text and text not in out:
            out.append(text)

    return out


def calibrate_pre_reasoning(
    *,
    user_message: str,
    language: str = "unknown",
    lexical_calibration: dict[str, Any] | None = None,
    ir_candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Produce a bounded cognitive state before reasoning.

    No sovereign decision is made here.
    """

    lexical = (
        lexical_calibration
        if isinstance(lexical_calibration, dict)
        else {}
    )

    ir = (
        ir_candidate
        if isinstance(ir_candidate, dict)
        else {}
    )

    # ------------------------------------------------------------
    # C265
    # Sense -> symbolic integration
    # ------------------------------------------------------------

    lexical_unknowns = _uniq_strings(
        lexical.get("unknowns", [])
    )

    ir_unknowns = _uniq_strings(
        ir.get("unknowns", [])
    )

    unknowns = _uniq_strings(
        lexical_unknowns + ir_unknowns
    )

    known_concept_ids = _uniq_strings(
        lexical.get(
            "known_concept_ids",
            [],
        )
    )

    symbolic_state = {
        "stage": "C265",
        "role": "sense_symbolic_integration",
        "input_present": bool(
            str(user_message or "").strip()
        ),
        "known_concept_ids": known_concept_ids,
        "unknowns": unknowns,
        "readonly": True,
    }

    # ------------------------------------------------------------
    # C266
    # Symbolic alignment
    # ------------------------------------------------------------

    if unknowns:
        symbolic_alignment = "PARTIAL"
    else:
        symbolic_alignment = "ALIGNED"

    alignment_state = {
        "stage": "C266",
        "role": "symbolic_alignment",
        "alignment": symbolic_alignment,
        "unknown_count": len(unknowns),
        "readonly": True,
    }

    # ------------------------------------------------------------
    # C273
    # Divergence detection
    # ------------------------------------------------------------

    contradictions = _uniq_strings(
        ir.get(
            "contradictions",
            [],
        )
    )

    risk_flags = _uniq_strings(
        ir.get(
            "risk_flags",
            [],
        )
    )

    divergence_tokens = list(unknowns)

    divergences: list[dict[str, Any]] = []

    for token in divergence_tokens:
        divergences.append(
            {
                "kind": "UNRESOLVED_SYMBOL",
                "token": token,
                "source": "LEXICAL_OR_IR_UNKNOWN",
            }
        )

    for contradiction in contradictions:
        divergences.append(
            {
                "kind": "CONTRADICTION",
                "signal": contradiction,
                "source": "IR_CANDIDATE",
            }
        )

    divergence_state = {
        "stage": "C273",
        "role": "divergence_detection",
        "divergence_tokens": divergence_tokens,
        "contradictions": contradictions,
        "risk_flags": risk_flags,
        "divergence_count": len(divergences),
        "readonly": True,
    }

    # ------------------------------------------------------------
    # C274
    # Calibration before reasoning
    # ------------------------------------------------------------

    has_uncertainty = bool(
        unknowns
        or contradictions
    )

    reasoning_readiness = (
        "CALIBRATED_WITH_UNCERTAINTY"
        if has_uncertainty
        else "CALIBRATED"
    )

    calibration_state = {
        "stage": "C274",
        "role": "calibration_before_reasoning",
        "reasoning_readiness": reasoning_readiness,
        "uncertainty_present": has_uncertainty,
        "readonly": True,
    }

    return {
        "status": "PRE_REASONING_CALIBRATION_PASS",
        "schema": "BRODY_PRE_REASONING_CALIBRATION_V1",

        "stage_order": list(_STAGE_ORDER),

        "user_message": str(user_message or ""),
        "language": str(language or "unknown"),

        "known_concept_ids": known_concept_ids,
        "unknowns": unknowns,

        "symbolic_alignment": symbolic_alignment,

        "divergence_tokens": divergence_tokens,
        "divergences": divergences,

        "contradictions": contradictions,
        "risk_flags": risk_flags,

        "reasoning_readiness": reasoning_readiness,

        "stages": {
            "C265": symbolic_state,
            "C266": alignment_state,
            "C273": divergence_state,
            "C274": calibration_state,
        },

        "lexical_source_status": lexical.get(
            "status",
            "NOT_PROVIDED",
        ),
        "lexical_source_ref": lexical.get(
            "source_ref",
        ),

        # Hard authority boundary.
        "readonly": True,
        "advisory_only": True,
        "context_signal_only": True,

        "decision_authority": "KX108_ONLY",

        "allowed_to_decide": False,
        "allowed_to_act": False,

        "emits_act": False,
        "emits_verdict": False,

        "memory_write": False,
        "canonical_write": False,

        "kernel_mutation": False,
        "x108_mutation": False,
    }


__all__ = [
    "calibrate_pre_reasoning",
]
