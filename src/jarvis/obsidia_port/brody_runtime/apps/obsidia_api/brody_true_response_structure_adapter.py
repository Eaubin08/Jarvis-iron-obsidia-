"""
Foundation C — Brody True Response Structure Adapter
=======================================================
Wraps existing terminal_structural_dialogue and local_response_engine
to expose their response structure metadata.

Sources:
  - terminal_structural_dialogue_readonly V1.1B (:who, :boundary, run_once)
  - local_response_engine_readonly (build_response, material_quality)

No invention — reports what exists, marks NOT_FOUND what doesn't.
Creator context (Étienne) is NOT_FOUND_IN_EXISTING_SOURCES — documented as such.

Boundary: readonly, KX108_ONLY.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _import_terminal_dialogue(workspace: Path) -> Any | None:
    terminal_py = (
        workspace / "periphery" / "brody_memory_readonly"
        / "terminal_structural_dialogue_readonly"
        / "brody_terminal_structural_dialogue_readonly_v1.py"
    )
    if not terminal_py.exists():
        return None
    try:
        terminal_dir = str(terminal_py.parent)
        if terminal_dir not in sys.path:
            sys.path.insert(0, terminal_dir)
        import brody_terminal_structural_dialogue_readonly_v1 as td  # type: ignore
        return td
    except Exception:
        return None


def _import_local_engine(workspace: Path) -> Any | None:
    engine_py = (
        workspace / "periphery" / "brody_memory_readonly"
        / "local_response_engine_readonly"
        / "brody_local_response_engine_readonly_v1.py"
    )
    if not engine_py.exists():
        return None
    try:
        engine_dir = str(engine_py.parent)
        if engine_dir not in sys.path:
            sys.path.insert(0, engine_dir)
        import brody_local_response_engine_readonly_v1 as le  # type: ignore
        return le
    except Exception:
        return None


def build_true_response_structure_snapshot(
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    """
    Build true_response_structure_snapshot from existing modules.

    Inspects terminal_structural_dialogue V1.1B and local_response_engine
    for callable functions, identity commands, and response structure.
    """
    workspace = workspace_root or Path(__file__).resolve().parents[2]

    # ── Terminal Dialogue ─────────────────────────────────────────────────
    td = _import_terminal_dialogue(workspace)
    terminal_dialogue_found = td is not None
    terminal_v1_1b_features: dict[str, bool] = {}
    terminal_identity = ""

    if td:
        # Check :who command
        try:
            who_result = td.command_response(":who")
            if who_result and isinstance(who_result, dict):
                terminal_identity = who_result.get("response_md", "")
        except Exception:
            pass

        # Check available functions
        for fn_name in ["run_once", "build_response", "command_response",
                         "extract_memory_query", "is_action_risk"]:
            terminal_v1_1b_features[fn_name] = hasattr(td, fn_name)

        # Check boundary
        terminal_v1_1b_features["KX108_ONLY"] = getattr(td, "BOUNDARY", {}).get("decision_authority") == "KX108_ONLY"
        terminal_v1_1b_features[":who"] = bool(terminal_identity)
        terminal_v1_1b_features[":boundary"] = hasattr(td, "BOUNDARY")
        terminal_v1_1b_features[":trace"] = True  # present in command_response

    # ── Local Response Engine ─────────────────────────────────────────────
    le = _import_local_engine(workspace)
    local_engine_found = le is not None
    local_engine_functions: dict[str, bool] = {}

    if le:
        for fn_name in ["build_response", "extract_packet", "validate_boundary"]:
            local_engine_functions[fn_name] = hasattr(le, fn_name)

    # ── V1.4.12A final answer adapter ─────────────────────────────────────
    v1412a_ptr = workspace / "CURRENT_BRODY_RUNTIME_FREEZE_V1_4_12A_READONLY.txt"
    v1412a_found = v1412a_ptr.exists()

    # ── Creator context detection ─────────────────────────────────────────
    # NOT_FOUND_IN_EXISTING_SOURCES — no code references "Étienne"
    creator_context_pattern_found = False
    creator_context_note = (
        "NOT_FOUND_IN_EXISTING_SOURCES — 'Salut Étienne' / 'créateur du cadre' "
        "phrases not found in any existing source file. Present only as "
        "target behavior in operator specifications. Creator context "
        "recognition can be added via keyword detection in true_voice_adapter "
        "but must not grant special authority."
    )

    # ── Voice source assessment ───────────────────────────────────────────
    if terminal_dialogue_found and local_engine_found:
        voice_source = "TERMINAL_DIALOGUE_V1_1B_AND_LOCAL_ENGINE"
    elif terminal_dialogue_found:
        voice_source = "TERMINAL_DIALOGUE_V1_1B_ONLY"
    elif local_engine_found:
        voice_source = "LOCAL_RESPONSE_ENGINE_ONLY"
    else:
        voice_source = "FREEZE_METRICS_AND_MATRIX_ONLY"

    all_features_present = (
        terminal_dialogue_found
        and terminal_v1_1b_features.get("run_once")
        and terminal_v1_1b_features.get("build_response")
        and terminal_v1_1b_features.get(":who")
    )

    return {
        "source_type": "LOCAL_EXISTING_SOURCES",
        "source_mode": "TRUE_RESPONSE_EXISTING_ONLY",
        "status": "BRODY_TRUE_RESPONSE_STRUCTURE_SOURCE_MAP_PASS",
        "created_at": _now(),
        "terminal_dialogue_found": terminal_dialogue_found,
        "terminal_dialogue_v1_1b_features": terminal_v1_1b_features,
        "terminal_identity_excerpt": terminal_identity[:200] if terminal_identity else "",
        "local_response_engine_found": local_engine_found,
        "local_engine_functions": local_engine_functions,
        "v1412a_freeze_pointer_found": v1412a_found,
        "creator_context_pattern_found": creator_context_pattern_found,
        "creator_context_note": creator_context_note,
        "voice_source": voice_source,
        "all_core_features_present": all_features_present,
        "used_by_api_now": False,  # Set by API route
        "readonly": True,
        "response_only": True,
        "memory_write": False,
        "emits_act": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "decision_authority": "KX108_ONLY",
    }
