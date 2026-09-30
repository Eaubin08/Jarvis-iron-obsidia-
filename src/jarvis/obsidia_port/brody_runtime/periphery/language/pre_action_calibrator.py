"""
C276 pre-action calibration.

Checks cognitive readiness before construction of a governed
action candidate.

C276 does not execute, decide, validate the final candidate,
or replace downstream governance.
"""

from __future__ import annotations

from typing import Any


_BOUNDARY_CONTRADICTIONS = {
    "REQUEST_REQUIRES_ACTION_BUT_ROUTE_IS_READONLY",
}


_ACTION_INTENTS = {
    "action_request",
    "write_request",
    "create_patch",
    "code_debug",
    "mutation_request",
}


def _uniq_strings(values: Any) -> list[str]:
    out: list[str] = []

    if not isinstance(values, (list, tuple, set)):
        return out

    for value in values:
        item = str(value or "").strip()

        if item and item not in out:
            out.append(item)

    return out


def calibrate_pre_action(
    *,
    ir_candidate: dict[str, Any] | None = None,
    reasoning_directive: dict[str, Any] | None = None,
    pre_reasoning_calibration: dict[str, Any] | None = None,
    pre_response_calibration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    C276 continuity check:

        IR intent
            +
        C274 reasoning calibration
            +
        C275 response calibration
            ->
        readiness to construct a governed candidate

    The result is only a readonly cognitive signal.
    """

    ir = (
        ir_candidate
        if isinstance(ir_candidate, dict)
        else {}
    )

    directive = (
        reasoning_directive
        if isinstance(reasoning_directive, dict)
        else {}
    )

    c274 = (
        pre_reasoning_calibration
        if isinstance(pre_reasoning_calibration, dict)
        else {}
    )

    c275 = (
        pre_response_calibration
        if isinstance(pre_response_calibration, dict)
        else {}
    )

    intent = str(
        ir.get("intent") or ""
    ).strip().lower()

    risk_flags = _uniq_strings(
        ir.get("risk_flags", [])
    )

    contradictions = _uniq_strings(
        ir.get("contradictions", [])
    )

    constraints = _uniq_strings(
        ir.get("constraints", [])
    )

    boundary_contradictions = [
        item
        for item in contradictions
        if item in _BOUNDARY_CONTRADICTIONS
    ]

    semantic_contradictions = [
        item
        for item in contradictions
        if item not in _BOUNDARY_CONTRADICTIONS
    ]

    unresolved_symbols = _uniq_strings(
        directive.get(
            "resolution_targets",
            [],
        )
    )

    if not unresolved_symbols:
        unresolved_symbols = _uniq_strings(
            c274.get(
                "unknowns",
                [],
            )
        )

    resolution_required = bool(
        directive.get(
            "resolution_required",
            False,
        )
    )

    c275_readiness = str(
        c275.get(
            "response_readiness",
            "",
        )
    ).strip()

    c275_calibration_required = bool(
        c275.get(
            "calibration_required",
            False,
        )
    )

    action_requested = (
        intent in _ACTION_INTENTS
        or "action_request" in risk_flags
        or "mutation_request" in risk_flags
    )

    calibration_flags: list[str] = []

    if not action_requested:
        readiness = (
            "NO_ACTION_CANDIDATE_REQUESTED"
        )
        candidate_projection_ready = False

    elif (
        c275_calibration_required
        or c275_readiness
        == "REQUIRES_CALIBRATION"
    ):
        readiness = (
            "REQUIRES_RESPONSE_CALIBRATION"
        )
        candidate_projection_ready = False

        calibration_flags.append(
            "C275_NOT_READY"
        )

    elif (
        resolution_required
        and unresolved_symbols
    ):
        readiness = (
            "REQUIRES_SEMANTIC_RESOLUTION"
        )
        candidate_projection_ready = False

        calibration_flags.append(
            "UNRESOLVED_SYMBOL_BEFORE_ACTION_CANDIDATE"
        )

    elif semantic_contradictions:
        readiness = (
            "REQUIRES_SEMANTIC_RESOLUTION"
        )
        candidate_projection_ready = False

        calibration_flags.append(
            "SEMANTIC_CONTRADICTION_BEFORE_ACTION_CANDIDATE"
        )

    else:
        readiness = (
            "READY_FOR_GOVERNANCE_CANDIDATE"
        )
        candidate_projection_ready = True

    return {
        "status": (
            "C276_PRE_ACTION_CALIBRATION_PASS"
        ),
        "schema": (
            "BRODY_PRE_ACTION_CALIBRATION_V1"
        ),
        "stage": "C276",

        "intent": intent,

        "action_requested": (
            action_requested
        ),

        "action_candidate_readiness": (
            readiness
        ),

        "candidate_projection_ready": (
            candidate_projection_ready
        ),

        # Candidate readiness is not execution permission.
        "execution_authorized": False,

        "requires_downstream_governance": (
            bool(action_requested)
        ),

        "risk_flags": risk_flags,
        "contradictions": contradictions,
        "boundary_contradictions": (
            boundary_contradictions
        ),
        "semantic_contradictions": (
            semantic_contradictions
        ),
        "constraints": constraints,

        "unresolved_symbols": (
            unresolved_symbols
        ),

        "calibration_flags": (
            calibration_flags
        ),

        # Hard boundaries.
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
    "calibrate_pre_action",
]
