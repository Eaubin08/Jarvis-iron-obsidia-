from __future__ import annotations

from copy import deepcopy
from typing import Any


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
    "authorizes_capability": False,
}

_P36_SPECIALIST_CAPABILITIES = frozenset(
    {
        "AGENT_TREE_LOOKUP",
        "OS_TRAD_TRANSLATION",
    }
)


def build_structured_p36_shadow_comparison(
    *,
    structured_capability_snapshot: Any,
    p36_snapshot: Any,
    unified_ir_snapshot: Any | None = None,
    semantic_snapshot: Any | None = None,
    memzum_snapshot: Any | None = None,
) -> dict[str, Any]:
    """Compare already-computed structured hints beside the legacy P36 result.

    This is a Jarjar-owned diagnostic. It intentionally does not accept raw
    user text, does not call P36, does not rank candidates and never emits a
    runtime selected path. The union is only an observation set.
    """

    structured = _as_dict(structured_capability_snapshot)
    p36 = _as_dict(p36_snapshot)

    legacy_capabilities = _normalize_capabilities(
        p36.get("required_capabilities")
    )
    structured_capabilities = _normalize_capabilities(
        structured.get("structured_capability_hints")
    )

    legacy_set = set(legacy_capabilities)
    structured_set = set(structured_capabilities)
    shared = [
        capability
        for capability in legacy_capabilities
        if capability in structured_set
    ]
    legacy_only = [
        capability
        for capability in legacy_capabilities
        if capability not in structured_set
    ]
    structured_only = [
        capability
        for capability in structured_capabilities
        if capability not in legacy_set
    ]

    union_capabilities = _append_observation_set(
        legacy_capabilities,
        structured_capabilities,
    )

    status = _augmentation_status(
        structured_capabilities=structured_capabilities,
        legacy_only=legacy_only,
        structured_only=structured_only,
    )

    return {
        "status": "STRUCTURED_P36_SHADOW_COMPARATOR_READY",
        "comparator_version": "V0",
        "legacy_capabilities": legacy_capabilities,
        "structured_capabilities": structured_capabilities,
        "union_capabilities": union_capabilities,
        "union_semantics": "OBSERVATION_SET_ONLY",
        "legacy_only": legacy_only,
        "structured_only": structured_only,
        "shared": shared,
        "legacy_detected_intents": _normalize_strings(
            p36.get("detected_intents")
        ),
        "legacy_selected_path": deepcopy(
            p36.get("selected_runtime_path")
        ),
        "legacy_selected_source_families": _normalize_strings(
            p36.get("selected_source_families")
        ),
        "legacy_hydration_plan": deepcopy(p36.get("hydration_plan")),
        "structured_primary_capability": _string_or_none(
            structured.get("primary_capability_hint")
            or structured.get("structured_primary_capability")
        ),
        "capability_hint_confidence": _string_or_none(
            structured.get("confidence_class")
            or structured.get("capability_hint_confidence")
        ),
        "augmentation_status": status,
        "augmentation_reason": _augmentation_reason(
            status=status,
            legacy_only=legacy_only,
            structured_only=structured_only,
            shared=shared,
        ),
        "optional_provenance": _optional_provenance(
            unified_ir_snapshot=unified_ir_snapshot,
            semantic_snapshot=semantic_snapshot,
            memzum_snapshot=memzum_snapshot,
        ),
        "governance": dict(_GOVERNANCE),
    }


def _augmentation_status(
    *,
    structured_capabilities: list[str],
    legacy_only: list[str],
    structured_only: list[str],
) -> str:
    legacy_specialist = bool(
        set(legacy_only) & _P36_SPECIALIST_CAPABILITIES
    )

    if structured_only and legacy_only:
        return "COMPLEMENTARY_SIGNALS"
    if structured_only:
        return "STRUCTURED_ADDS_SIGNAL"
    if legacy_specialist:
        return "P36_ADDS_SPECIALIST_SIGNAL"
    if not structured_capabilities:
        return "NO_STRUCTURED_SIGNAL"
    if legacy_only:
        return "P36_ADDS_SPECIALIST_SIGNAL"
    return "NO_CHANGE"


def _augmentation_reason(
    *,
    status: str,
    legacy_only: list[str],
    structured_only: list[str],
    shared: list[str],
) -> str:
    if status == "STRUCTURED_ADDS_SIGNAL":
        return "Structured hints add diagnostic capability observations absent from P36."
    if status == "P36_ADDS_SPECIALIST_SIGNAL":
        return "P36 exposes legacy specialist capability observations absent from structured hints."
    if status == "COMPLEMENTARY_SIGNALS":
        return "Structured hints and P36 each expose distinct diagnostic capability observations."
    if status == "NO_STRUCTURED_SIGNAL":
        return "No structured capability signal is available beside the legacy P36 result."
    if shared:
        return "Structured hints and P36 observe the same capability candidates."
    if legacy_only or structured_only:
        return "Capability observations differ without a structured augmentation."
    return "No additional capability observation is present."


def _optional_provenance(
    *,
    unified_ir_snapshot: Any | None,
    semantic_snapshot: Any | None,
    memzum_snapshot: Any | None,
) -> dict[str, Any]:
    ir = _as_dict(unified_ir_snapshot)
    semantic = _as_dict(semantic_snapshot)
    memzum = _as_dict(memzum_snapshot)
    memory_required = memzum.get("memory_required")
    if memory_required is None:
        memory_required = _as_dict(ir.get("needs")).get("memory")

    return {
        "ir_intent_type": _string_or_none(ir.get("intent_type")),
        "ir_target_layer": _string_or_none(ir.get("target_layer")),
        "semantic_topic": _string_or_none(semantic.get("topic")),
        "memzum_memory_required": bool(memory_required is True),
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_capabilities(value: Any) -> list[str]:
    return _normalize_strings(value)


def _normalize_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _append_observation_set(*groups: list[str]) -> list[str]:
    out: list[str] = []
    for group in groups:
        for item in group:
            if item not in out:
                out.append(item)
    return out


def _string_or_none(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


__all__ = ["build_structured_p36_shadow_comparison"]
