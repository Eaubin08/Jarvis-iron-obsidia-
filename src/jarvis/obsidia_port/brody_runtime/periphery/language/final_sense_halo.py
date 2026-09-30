"""
C277 final sense halo.

Consolidates the final cognitive sense state produced by the
preceding calibration stages into a readonly, auditable signal.

No execution, no sovereign decision, no retrieval, no mutation.
"""

from __future__ import annotations

from typing import Any


def _uniq_strings(values: Any) -> list[str]:
    out: list[str] = []

    if not isinstance(values, (list, tuple, set)):
        return out

    for value in values:
        item = str(value or "").strip()

        if item and item not in out:
            out.append(item)

    return out


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def build_final_sense_halo(
    *,
    calibration_context: dict[str, Any] | None = None,
    memory_refs: list[Any] | None = None,
    symbolic_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build C277 final-sense consolidation.

    C277 preserves the calibrated cognitive state and exposes a
    bounded integration trace for downstream semantic comparison.

    It does not resolve uncertainty and does not authorize action.
    """

    context = _dict(
        calibration_context
    )

    pre_reasoning = _dict(
        context.get(
            "pre_reasoning"
        )
    )

    pre_response = _dict(
        context.get(
            "pre_response"
        )
    )

    pre_action = _dict(
        context.get(
            "pre_action"
        )
    )

    symbolic = dict(
        symbolic_context
        if isinstance(
            symbolic_context,
            dict,
        )
        else {}
    )

    refs = list(
        memory_refs
        if isinstance(
            memory_refs,
            (list, tuple),
        )
        else []
    )

    unresolved_symbols = _uniq_strings(
        list(
            pre_reasoning.get(
                "unknowns",
                [],
            )
            or []
        )
        + list(
            pre_action.get(
                "unresolved_symbols",
                [],
            )
            or []
        )
    )

    contradictions = _uniq_strings(
        pre_reasoning.get(
            "contradictions",
            [],
        )
    )

    risk_flags = _uniq_strings(
        list(
            pre_reasoning.get(
                "risk_flags",
                [],
            )
            or []
        )
        + list(
            pre_action.get(
                "risk_flags",
                [],
            )
            or []
        )
    )

    calibration_flags = _uniq_strings(
        pre_response.get(
            "calibration_flags",
            [],
        )
    )

    reasoning_readiness = str(
        pre_reasoning.get(
            "readiness",
            "",
        )
        or ""
    )

    response_readiness = str(
        pre_response.get(
            "response_readiness",
            "",
        )
        or ""
    )

    action_readiness = str(
        pre_action.get(
            "action_candidate_readiness",
            "",
        )
        or ""
    )

    uncertainty_present = bool(
        unresolved_symbols
        or contradictions
        or calibration_flags
        or "UNCERTAINTY"
        in reasoning_readiness.upper()
        or "UNCERTAINTY"
        in response_readiness.upper()
        or "REQUIRES_"
        in action_readiness.upper()
    )

    if uncertainty_present:
        node_signal = (
            "FINAL_SENSE_WITH_UNCERTAINTY"
        )
    else:
        node_signal = (
            "FINAL_SENSE_CONSOLIDATED"
        )

    source_stages: list[str] = []

    for stage_data in (
        pre_reasoning,
        pre_response,
        pre_action,
    ):
        stage = str(
            stage_data.get(
                "stage",
                "",
            )
            or ""
        ).strip()

        if stage:
            source_stages.append(
                stage
            )

    calibration_result = {
        "status": (
            "CONSOLIDATED_WITH_UNCERTAINTY"
            if uncertainty_present
            else "CONSOLIDATED"
        ),
        "uncertainty_present": (
            uncertainty_present
        ),
        "unresolved_symbols": (
            unresolved_symbols
        ),
        "contradictions": (
            contradictions
        ),
        "risk_flags": (
            risk_flags
        ),
        "calibration_flags": (
            calibration_flags
        ),
        "reasoning_readiness": (
            reasoning_readiness
        ),
        "response_readiness": (
            response_readiness
        ),
        "action_readiness": (
            action_readiness
        ),
    }

    integration_trace = {
        "source_stages": (
            source_stages
        ),
        "memory_refs": refs,
        "symbolic_context": (
            symbolic
        ),
        "trace_mode": (
            "READONLY_CONSOLIDATION"
        ),
    }

    return {
        "status": (
            "C277_FINAL_SENSE_HALO_PASS"
        ),
        "schema": (
            "BRODY_FINAL_SENSE_HALO_V1"
        ),
        "stage": "C277",
        "name": "final_sense_halo",

        # Declared C277 outputs.
        "node_signal": (
            node_signal
        ),
        "calibration_result": (
            calibration_result
        ),
        "integration_trace": (
            integration_trace
        ),

        # Non-sovereign boundary.
        "readonly": True,
        "advisory_only": True,
        "context_signal_only": True,

        "decision_authority": (
            "KX108_ONLY"
        ),

        "allowed_to_decide": False,
        "allowed_to_act": False,

        "emits_act": False,
        "emits_verdict": False,

        "memory_write": False,
        "canonical_write": False,

        "kernel_mutation": False,
        "x108_mutation": False,

        "auto_apply": False,
        "auto_commit": False,
        "auto_push": False,
    }


__all__ = [
    "build_final_sense_halo",
]
