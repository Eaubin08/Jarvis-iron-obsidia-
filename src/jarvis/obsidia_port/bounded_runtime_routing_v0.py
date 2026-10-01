from __future__ import annotations

import os
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


_ALLOWED_CAPABILITIES = frozenset(
    {
        "BRODY_CHAT_ENTRYPOINT",
        "MEMORY_REINTEGRATION_CONTEXT",
        "PROOF_AUDIT_CONTEXT",
        "IR_ALPHABET_MAPPING",
    }
)

_ENV_FLAG = "JARJAR_BOUNDED_STRUCTURED_ROUTING_V0"


def resolve_bounded_runtime_override(
    *,
    capability_selection_snapshot: Any,
    available_families: Any = None,
) -> dict[str, Any]:
    """Resolve an opt-in, bounded P36 source-routing override.

    This is context routing only. It cannot authorize actions and it never
    changes KX108 authority. The caller must explicitly opt in through the
    environment flag; otherwise legacy P36 remains authoritative.
    """

    enabled = os.environ.get(_ENV_FLAG, "0") == "1"
    selection = (
        capability_selection_snapshot
        if isinstance(capability_selection_snapshot, dict)
        else {}
    )
    selected = str(selection.get("selected_capability") or "").strip()
    selection_status = str(selection.get("status") or "").strip()

    base = {
        "status": "DISABLED",
        "enabled": enabled,
        "applied": False,
        "selected_capability": selected or None,
        "allowed_capabilities": sorted(_ALLOWED_CAPABILITIES),
        "runtime_path": {},
        "hydration_plan": {},
        "fallback_to_legacy_p36": True,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "emits_act": False,
        "memory_write": False,
        "kernel_mutation": False,
        "x108_mutation": False,
        "authorizes_action": False,
        "authorizes_capability": False,
        "scope": "SOURCE_CONTEXT_ROUTING_ONLY",
    }

    if not enabled:
        return base

    if selection_status != "SELECTED_SHADOW" or not selected:
        return {**base, "status": "NO_ADMISSIBLE_SELECTION"}

    if selected not in _ALLOWED_CAPABILITIES:
        return {**base, "status": "CAPABILITY_OUTSIDE_BOUNDED_ALLOWLIST"}

    try:
        path = _build_path_for_capability(
            selected,
            query="BOUNDED_RUNTIME_V0",
            path_idx=0,
            available_families=(
                [str(v) for v in available_families if str(v).strip()]
                if isinstance(available_families, list)
                else None
            ),
        )
    except Exception as exc:
        return {
            **base,
            "status": f"P36_TEMPLATE_ERROR:{type(exc).__name__}",
        }

    if path.get("capability_chain") != [selected]:
        return {**base, "status": "P36_TEMPLATE_MISMATCH"}

    if path.get("decision_authority") != "KX108_ONLY":
        return {**base, "status": "AUTHORITY_GUARD_FAIL"}

    if path.get("emits_act") is not False:
        return {**base, "status": "ACT_GUARD_FAIL"}

    if path.get("x108_decision") != "ALLOW_CONTEXT_ONLY":
        return {**base, "status": "CONTEXT_ONLY_GUARD_FAIL"}

    hydration = build_hydration_plan_from_path(
        path,
        max_files=8,
        max_bytes=50_000,
    )

    return {
        **base,
        "status": "BOUNDED_RUNTIME_OVERRIDE_READY",
        "applied": True,
        "runtime_path": path,
        "hydration_plan": hydration,
        "fallback_to_legacy_p36": False,
    }


__all__ = ["resolve_bounded_runtime_override"]
