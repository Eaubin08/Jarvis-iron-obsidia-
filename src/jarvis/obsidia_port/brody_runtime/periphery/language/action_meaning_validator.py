"""
C278 action meaning validator.

Checks semantic continuity between the final cognitive sense
snapshot and a projected action request.

Readonly, advisory, non-sovereign.
"""

from __future__ import annotations

from typing import Any


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _normalize_text(value: Any) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .split()
    )


def _list(value: Any) -> list[Any]:
    if isinstance(
        value,
        (list, tuple),
    ):
        return list(value)

    return []


def validate_action_meaning(
    *,
    calibration_context: dict[str, Any] | None = None,
    memory_refs: list[Any] | None = None,
    symbolic_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the C278 semantic continuity signal.

    This stage compares meaning only. It does not perform
    downstream structural governance or execution.
    """

    context = _dict(
        calibration_context
    )

    halo = _dict(
        context.get(
            "final_sense_halo"
        )
    )

    projection_raw = context.get(
        "action_projection"
    )

    projection = (
        projection_raw
        if isinstance(
            projection_raw,
            dict,
        )
        else None
    )

    symbolic = _dict(
        symbolic_context
    )

    refs = _list(
        memory_refs
    )

    halo_calibration = _dict(
        halo.get(
            "calibration_result"
        )
    )

    halo_trace = _dict(
        halo.get(
            "integration_trace"
        )
    )

    halo_symbolic = _dict(
        halo_trace.get(
            "symbolic_context"
        )
    )

    uncertainty_present = bool(
        halo_calibration.get(
            "uncertainty_present",
            False,
        )
    )

    unresolved_symbols = [
        str(value).strip()
        for value in _list(
            halo_calibration.get(
                "unresolved_symbols"
            )
        )
        if str(value).strip()
    ]

    source_objective = str(
        symbolic.get(
            "source_objective",
            "",
        )
        or ""
    )

    source_intent = str(
        symbolic.get(
            "intent",
            "",
        )
        or ""
    ).strip()

    halo_intent = str(
        halo_symbolic.get(
            "intent",
            "",
        )
        or ""
    ).strip()

    projected_objective = ""

    if projection is not None:
        projected_objective = str(
            projection.get(
                "objective",
                "",
            )
            or ""
        )

    source_norm = _normalize_text(
        source_objective
    )

    projected_norm = _normalize_text(
        projected_objective
    )

    objective_continuity = bool(
        projection is not None
        and source_norm
        and projected_norm
        and source_norm
        == projected_norm
    )

    normalized_source_intent = (
        _normalize_text(
            source_intent
        )
    )

    normalized_halo_intent = (
        _normalize_text(
            halo_intent
        )
    )

    intent_alignment = bool(
        normalized_source_intent
        and normalized_halo_intent
        and normalized_source_intent
        == normalized_halo_intent
    )

    if projection is None:
        action_meaning_status = (
            "NOT_APPLICABLE"
        )

        node_signal = (
            "NO_ACTION_MEANING_TO_VALIDATE"
        )

    elif uncertainty_present:
        action_meaning_status = (
            "UNRESOLVED"
        )

        node_signal = (
            "ACTION_MEANING_WITH_UNCERTAINTY"
        )

    elif (
        objective_continuity
        and intent_alignment
    ):
        action_meaning_status = (
            "ALIGNED"
        )

        node_signal = (
            "ACTION_MEANING_ALIGNED"
        )

    else:
        action_meaning_status = (
            "DIVERGENT"
        )

        node_signal = (
            "ACTION_MEANING_DIVERGENCE"
        )

    calibration_result = {
        "action_meaning_status": (
            action_meaning_status
        ),
        "objective_continuity": (
            objective_continuity
        ),
        "intent_alignment": (
            intent_alignment
        ),
        "uncertainty_present": (
            uncertainty_present
        ),
        "unresolved_symbols": (
            unresolved_symbols
        ),
        "source_intent": (
            source_intent
        ),
        "halo_intent": (
            halo_intent
        ),
    }

    integration_trace = {
        "source_stage": (
            halo.get(
                "stage",
                "",
            )
        ),
        "projection_type": (
            "REPAIR_REQUEST"
            if projection is not None
            else "NONE"
        ),
        "projection_id": (
            str(
                projection.get(
                    "request_id",
                    "",
                )
                or ""
            )
            if projection is not None
            else ""
        ),
        "memory_refs": refs,
        "symbolic_context": (
            dict(symbolic)
        ),
        "trace_mode": (
            "READONLY_MEANING_VALIDATION"
        ),
    }

    return {
        "status": (
            "C278_ACTION_MEANING_VALIDATOR_PASS"
        ),
        "schema": (
            "BRODY_ACTION_MEANING_VALIDATOR_V1"
        ),
        "stage": "C278",
        "name": (
            "action_meaning_validator"
        ),

        # Declared C278 outputs.
        "node_signal": (
            node_signal
        ),
        "calibration_result": (
            calibration_result
        ),
        "integration_trace": (
            integration_trace
        ),

        # Absolute non-sovereign boundary.
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
    "validate_action_meaning",
]
