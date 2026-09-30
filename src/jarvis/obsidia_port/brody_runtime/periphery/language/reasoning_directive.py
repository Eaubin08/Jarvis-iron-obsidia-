"""
Readonly reasoning directive derived from pre-reasoning calibration.

Consumes C265 -> C274 output and converts uncertainty into a bounded
reasoning instruction.

It does NOT:
- resolve unknown concepts,
- retrieve memory,
- decide HOLD/BLOCK/ALLOW,
- emit ACT,
- mutate kernel/X108.
"""

from __future__ import annotations

from typing import Any


def _uniq_strings(values: Any) -> list[str]:
    out: list[str] = []

    if not isinstance(values, list):
        return out

    for value in values:
        text = str(value or "").strip()

        if text and text not in out:
            out.append(text)

    return out


def build_reasoning_directive(
    pre_reasoning_calibration: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Convert a bounded C274 calibration state into a reasoning directive.

    This is guidance for cognition only.
    It is never a sovereign gate.
    """

    calibration = (
        pre_reasoning_calibration
        if isinstance(pre_reasoning_calibration, dict)
        else {}
    )

    unknowns = _uniq_strings(
        calibration.get("unknowns", [])
    )

    contradictions = _uniq_strings(
        calibration.get(
            "contradictions",
            [],
        )
    )

    risk_flags = _uniq_strings(
        calibration.get(
            "risk_flags",
            [],
        )
    )

    known_concept_ids = _uniq_strings(
        calibration.get(
            "known_concept_ids",
            [],
        )
    )

    readiness = str(
        calibration.get(
            "reasoning_readiness",
            "",
        )
        or ""
    )

    uncertainty_present = bool(
        unknowns
        or contradictions
        or readiness == "CALIBRATED_WITH_UNCERTAINTY"
    )

    if uncertainty_present:
        reasoning_mode = "RESOLVE_BEFORE_ASSERT"
        resolution_required = True
        assertion_policy = (
            "DO_NOT_ASSERT_UNRESOLVED_SYMBOL_AS_KNOWN"
        )
    else:
        reasoning_mode = "NORMAL_REASONING"
        resolution_required = False
        assertion_policy = (
            "NORMAL_ASSERTION_WITH_EVIDENCE"
        )

    return {
        "status": "PRE_REASONING_DIRECTIVE_PASS",
        "schema": "BRODY_REASONING_DIRECTIVE_V1",

        "source_status": calibration.get(
            "status",
            "UNKNOWN",
        ),

        "source_stage_order": list(
            calibration.get(
                "stage_order",
                [],
            )
        ),

        "reasoning_mode": reasoning_mode,
        "resolution_required": resolution_required,

        # At this stage only unresolved lexical/symbolic objects
        # are concrete resolution targets.
        "resolution_targets": unknowns,

        "assertion_policy": assertion_policy,

        "reasoning_readiness": readiness,

        "known_concept_ids": known_concept_ids,
        "unknowns": unknowns,
        "contradictions": contradictions,
        "risk_flags": risk_flags,

        "symbolic_alignment": calibration.get(
            "symbolic_alignment",
            "UNKNOWN",
        ),

        "divergences": list(
            calibration.get(
                "divergences",
                [],
            )
        )
        if isinstance(
            calibration.get("divergences"),
            list,
        )
        else [],

        # Cognitive guidance only.
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
    "build_reasoning_directive",
]
