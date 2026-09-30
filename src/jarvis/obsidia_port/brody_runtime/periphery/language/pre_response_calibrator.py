"""
C275 — pre-response calibration.

Checks whether a candidate response respects the epistemic calibration
established before reasoning.

This module:
- does not generate a response,
- does not rewrite a response,
- does not retrieve memory,
- does not call external engines,
- does not decide or act.

C275 only emits a readonly calibration snapshot.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def _normalize(value: Any) -> str:
    text = str(value or "").strip().lower()

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    return "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )


def _uniq_strings(values: Any) -> list[str]:
    out: list[str] = []

    if not isinstance(values, list):
        return out

    for value in values:
        token = str(value or "").strip()

        if token and token not in out:
            out.append(token)

    return out


def _contains_token(
    text: str,
    token: str,
) -> bool:
    normalized_text = _normalize(text)
    normalized_token = _normalize(token)

    if not normalized_token:
        return False

    return bool(
        re.search(
            rf"(?<![\w])"
            rf"{re.escape(normalized_token)}"
            rf"(?![\w])",
            normalized_text,
        )
    )


def _has_uncertainty_framing(
    candidate_response: str,
    token: str,
) -> bool:
    """
    Detect explicit epistemic uncertainty around an unresolved symbol.

    This is intentionally narrow:
    C275 does not judge truth.
    It only checks whether the response presents the unresolved symbol
    as unresolved / unknown instead of silently asserting it as known.
    """

    text = _normalize(candidate_response)

    if not _contains_token(
        candidate_response,
        token,
    ):
        return False

    uncertainty_markers = (
        "non resolu",
        "reste non resolu",
        "reste unresolved",
        "unresolved",
        "inconnu",
        "unknown",
        "ne peux pas traiter",
        "cannot treat",
        "pas comme un concept connu",
        "not as a known concept",
        "je ne sais pas",
        "i do not know",
        "incertain",
        "uncertain",
    )

    return any(
        marker in text
        for marker in uncertainty_markers
    )


def calibrate_pre_response(
    *,
    candidate_response: str,
    reasoning_directive: dict[str, Any] | None = None,
    pre_reasoning_calibration: dict[str, Any] | None = None,
    language: str = "unknown",
) -> dict[str, Any]:
    """
    C275 continuity check:

        C274 calibration
            ->
        reasoning directive
            ->
        candidate response
            ->
        C275 response calibration

    Only checks continuity with prior uncertainty constraints.
    """

    response_candidate = str(
        candidate_response or ""
    )

    directive = (
        reasoning_directive
        if isinstance(
            reasoning_directive,
            dict,
        )
        else {}
    )

    calibration = (
        pre_reasoning_calibration
        if isinstance(
            pre_reasoning_calibration,
            dict,
        )
        else {}
    )

    unresolved = _uniq_strings(
        directive.get(
            "resolution_targets",
            [],
        )
    )

    if not unresolved:
        unresolved = _uniq_strings(
            calibration.get(
                "unknowns",
                [],
            )
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

    assertion_policy = str(
        directive.get(
            "assertion_policy",
            "",
        )
    )

    calibration_flags: list[str] = []

    unresolved_mentions: list[str] = []
    uncertainty_preserved: list[str] = []

    for token in unresolved:
        if not _contains_token(
            response_candidate,
            token,
        ):
            continue

        unresolved_mentions.append(
            token
        )

        if _has_uncertainty_framing(
            response_candidate,
            token,
        ):
            uncertainty_preserved.append(
                token
            )
        elif (
            assertion_policy
            == "DO_NOT_ASSERT_UNRESOLVED_SYMBOL_AS_KNOWN"
        ):
            if (
                "UNRESOLVED_SYMBOL_ASSERTED_AS_KNOWN"
                not in calibration_flags
            ):
                calibration_flags.append(
                    "UNRESOLVED_SYMBOL_ASSERTED_AS_KNOWN"
                )

    if contradictions:
        calibration_flags.append(
            "PRE_REASONING_CONTRADICTIONS_PRESENT"
        )

    if calibration_flags:
        response_readiness = (
            "REQUIRES_CALIBRATION"
        )
        calibration_required = True

    elif (
        unresolved
        and (
            uncertainty_preserved
            or directive.get(
                "resolution_required"
            )
        )
    ):
        response_readiness = (
            "READY_WITH_UNCERTAINTY"
        )
        calibration_required = False

    else:
        response_readiness = "READY"
        calibration_required = False

    return {
        "status": "C275_PRE_RESPONSE_CALIBRATION_PASS",
        "schema": "BRODY_PRE_RESPONSE_CALIBRATION_V1",
        "stage": "C275",

        "language": str(
            language or "unknown"
        ),

        # Candidate is preserved exactly.
        "response_candidate": (
            response_candidate
        ),

        "response_readiness": (
            response_readiness
        ),

        "calibration_required": (
            calibration_required
        ),

        "calibration_flags": (
            calibration_flags
        ),

        "unresolved_symbols": (
            unresolved
        ),

        "unresolved_mentions": (
            unresolved_mentions
        ),

        "uncertainty_preserved_for": (
            uncertainty_preserved
        ),

        "contradictions": (
            contradictions
        ),

        "risk_flags": (
            risk_flags
        ),

        "assertion_policy": (
            assertion_policy
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
    }


__all__ = [
    "calibrate_pre_response",
]
