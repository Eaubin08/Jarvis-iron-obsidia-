from __future__ import annotations

from typing import Any


_PRECEDENCE = (
    "ACTION_REQUEST_BLOCKED",
    "BRODY_CHAT_ENTRYPOINT",
    "MEMORY_REINTEGRATION_CONTEXT",
    "PROOF_AUDIT_CONTEXT",
    "IR_ALPHABET_MAPPING",
    "REVERSE_OS_INTERLANGUAGE",
    "OS_TRAD_TRANSLATION",
    "AGENT_TREE_LOOKUP",
    "SOURCE_CONTEXT",
)

_GOVERNANCE = {
    "readonly": True,
    "shadow_only": True,
    "advisory_only": True,
    "emits_act": False,
    "memory_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "decision_authority": "KX108_ONLY",
    "selects_runtime_path": False,
    "modifies_p36_selection": False,
    "authorizes_capability": False,
    "authorizes_action": False,
    "selection_is_diagnostic_only": True,
}


def build_capability_selection_shadow(
    *,
    capability_admissibility_snapshot: Any,
    comparator_snapshot: Any | None = None,
) -> dict[str, Any]:
    """Select one admissible capability for shadow comparison only.

    The selector consumes admissibility output, not raw routing evidence. It
    never selects a runtime path, authorizes a capability, or feeds P36.
    """

    admissibility = _as_dict(capability_admissibility_snapshot)
    comparator = _as_dict(comparator_snapshot)
    candidates = admissibility.get("candidates")
    candidates = candidates if isinstance(candidates, list) else []

    eligible = []
    excluded_review = []
    excluded_insufficient = []

    for candidate in candidates:
        record = _as_dict(candidate)
        capability = _string(record.get("capability"))
        state = _string(record.get("admissibility"))
        if not capability:
            continue
        if state == "ADMISSIBLE":
            _append_unique(eligible, capability)
        elif state == "REVIEW_REQUIRED":
            _append_unique(excluded_review, capability)
        elif state == "INSUFFICIENT_PROVENANCE":
            _append_unique(excluded_insufficient, capability)

    unranked = [
        capability
        for capability in eligible
        if capability not in _PRECEDENCE
    ]
    ranked = [
        capability
        for capability in _PRECEDENCE
        if capability in eligible
    ]

    selected = ranked[0] if ranked else None

    if selected is not None:
        status = "SELECTED_SHADOW"
        reason = f"V0_PRECEDENCE:{selected}"
    elif eligible:
        status = "UNRANKED_ADMISSIBLE"
        reason = "ONLY_UNRANKED_ADMISSIBLE_CAPABILITIES"
    else:
        status = "NO_ADMISSIBLE_CAPABILITY"
        reason = "NO_ADMISSIBLE_CAPABILITY"

    alternatives = [
        capability
        for capability in eligible
        if capability != selected
    ]

    return {
        "status": status,
        "selection_version": "V0",
        "precedence": list(_PRECEDENCE),
        "eligible_capabilities": eligible,
        "excluded_review_required": excluded_review,
        "excluded_insufficient_provenance": excluded_insufficient,
        "unranked_admissible_capabilities": unranked,
        "selected_capability": selected,
        "selection_reason": reason,
        "alternative_admissible_capabilities": alternatives,
        "legacy_p36_selected_path": comparator.get("legacy_selected_path"),
        "legacy_p36_selected_source_families": _normalize_strings(
            comparator.get("legacy_selected_source_families")
        ),
        "contract": {
            "detection_not_admissibility": True,
            "admissibility_not_selection": True,
            "selection_not_authorization": True,
        },
        "governance": dict(_GOVERNANCE),
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string(value: Any) -> str:
    return str(value or "").strip()


def _normalize_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = _string(item)
        if text and text not in out:
            out.append(text)
    return out


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


__all__ = ["build_capability_selection_shadow"]
