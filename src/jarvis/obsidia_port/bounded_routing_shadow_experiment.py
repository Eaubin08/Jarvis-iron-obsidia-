from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


_RUNTIME_ROOT = Path(__file__).resolve().parent / "brody_runtime"
if str(_RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(_RUNTIME_ROOT))


from runtime_wiring.source_runtime.capability_path_router import (
    _build_path_for_capability,
)
from runtime_wiring.source_runtime.source_hydration_planner import (
    build_hydration_plan_from_path,
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
    "counterfactual_only": True,
}


def build_bounded_routing_shadow_experiment(
    *,
    capability_selection_snapshot: Any,
    legacy_p36_snapshot: Any,
    available_families: Any = None,
) -> dict[str, Any]:
    """Resolve the shadow-selected capability through the existing P36 template.

    Counterfactual only: this function never feeds the resulting path back into
    source routing, hydration, answer generation, permissions, or KX108.
    """

    selection = _as_dict(capability_selection_snapshot)
    legacy = _as_dict(legacy_p36_snapshot)
    selected_capability = _string(selection.get("selected_capability"))
    status = _string(selection.get("status"))

    legacy_path = _as_dict(
        legacy.get("selected_runtime_path") or legacy.get("selected_path")
    )
    legacy_hydration = _as_dict(legacy.get("hydration_plan"))

    if status != "SELECTED_SHADOW" or not selected_capability:
        return _result(
            status="NO_SHADOW_SELECTION",
            selected_capability=None,
            shadow_path={},
            shadow_hydration={},
            legacy_path=legacy_path,
            legacy_hydration=legacy_hydration,
            reason="NO_SELECTED_ADMISSIBLE_CAPABILITY",
        )

    if selected_capability == "ACTION_REQUEST_BLOCKED":
        return _result(
            status="AUTHORITY_BOUNDARY_EXCLUDED",
            selected_capability=selected_capability,
            shadow_path={},
            shadow_hydration={},
            legacy_path=legacy_path,
            legacy_hydration=legacy_hydration,
            reason="ACTION_CLASSIFICATION_IS_NOT_SOURCE_ROUTING",
        )

    try:
        shadow_path = _build_path_for_capability(
            selected_capability,
            query="SHADOW_COUNTERFACTUAL_ONLY",
            path_idx=0,
            available_families=_normalize_strings(available_families)
            if isinstance(available_families, list)
            else None,
        )
    except Exception as exc:
        return _result(
            status="NO_EXISTING_P36_MAPPING",
            selected_capability=selected_capability,
            shadow_path={},
            shadow_hydration={},
            legacy_path=legacy_path,
            legacy_hydration=legacy_hydration,
            reason=f"P36_TEMPLATE_UNAVAILABLE:{type(exc).__name__}",
        )

    if not shadow_path.get("capability_chain"):
        return _result(
            status="NO_EXISTING_P36_MAPPING",
            selected_capability=selected_capability,
            shadow_path={},
            shadow_hydration={},
            legacy_path=legacy_path,
            legacy_hydration=legacy_hydration,
            reason="P36_TEMPLATE_EMPTY",
        )

    shadow_hydration = build_hydration_plan_from_path(
        shadow_path,
        max_files=8,
        max_bytes=50_000,
    )

    legacy_capability = _first_string(legacy_path.get("capability_chain"))
    shadow_families = _normalize_strings(shadow_path.get("source_families"))
    legacy_families = _normalize_strings(legacy_path.get("source_families"))
    shadow_subfamilies = _normalize_strings(shadow_path.get("source_subfamilies"))
    legacy_subfamilies = _normalize_strings(legacy_path.get("source_subfamilies"))
    shadow_evidence = _normalize_strings(shadow_path.get("evidence_packs"))
    legacy_evidence = _normalize_strings(legacy_path.get("evidence_packs"))

    same_capability = selected_capability == legacy_capability
    same_families = shadow_families == legacy_families
    same_subfamilies = shadow_subfamilies == legacy_subfamilies
    same_evidence = shadow_evidence == legacy_evidence

    if same_capability and same_families and same_subfamilies and same_evidence:
        comparison = "EQUIVALENT_PATH"
        impact = "NONE"
    elif same_families and same_subfamilies and same_evidence:
        comparison = "CAPABILITY_LABEL_DIFFERENCE"
        impact = "METADATA_ONLY"
    elif same_families:
        comparison = "HYDRATION_SCOPE_DIFFERENCE"
        impact = "HYDRATION_DIFFERENCE"
    else:
        comparison = "SOURCE_FAMILY_DIFFERENCE"
        impact = "SOURCE_FAMILY_DIFFERENCE"

    result = _result(
        status="SHADOW_P36_MAPPING_READY",
        selected_capability=selected_capability,
        shadow_path=shadow_path,
        shadow_hydration=shadow_hydration,
        legacy_path=legacy_path,
        legacy_hydration=legacy_hydration,
        reason="EXISTING_P36_TEMPLATE_RESOLVED",
    )
    result.update(
        {
            "legacy_selected_capability": legacy_capability,
            "comparison": comparison,
            "runtime_impact": impact,
            "same_capability": same_capability,
            "same_source_families": same_families,
            "same_source_subfamilies": same_subfamilies,
            "same_evidence_packs": same_evidence,
        }
    )
    return result


def _result(
    *,
    status: str,
    selected_capability: str | None,
    shadow_path: dict[str, Any],
    shadow_hydration: dict[str, Any],
    legacy_path: dict[str, Any],
    legacy_hydration: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "status": status,
        "selected_capability": selected_capability,
        "shadow_p36_path": shadow_path,
        "shadow_hydration_plan": shadow_hydration,
        "legacy_p36_path": legacy_path,
        "legacy_hydration_plan": legacy_hydration,
        "reason": reason,
        "governance": dict(_GOVERNANCE),
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string(value: Any) -> str:
    return str(value or "").strip()


def _first_string(value: Any) -> str | None:
    values = _normalize_strings(value)
    return values[0] if values else None


def _normalize_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = _string(item)
        if text and text not in out:
            out.append(text)
    return out


__all__ = ["build_bounded_routing_shadow_experiment"]
