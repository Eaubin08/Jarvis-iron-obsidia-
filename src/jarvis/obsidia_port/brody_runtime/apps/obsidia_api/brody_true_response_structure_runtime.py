"""
Foundation C — Brody True Response Structure Runtime
=======================================================
Canonical runtime entry point for Foundation C: True Response Structure.

Delegates to brody_true_response_structure_adapter for module inspection,
then overlays runtime fields required by brody_full_runtime_reconnect:
  foundation, status (FOUNDATION_C_READY/PARTIAL), source_mode,
  local_response_engine, terminal_structural_dialogue, model_position,
  creator_context_pattern, voice_source.

Boundary: readonly, KX108_ONLY.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from apps.obsidia_api.brody_true_response_structure_adapter import (
    build_true_response_structure_snapshot as _build_from_adapter,
)


def build_true_response_structure_snapshot(
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    """
    Runtime-layer true response structure snapshot (Foundation C).
    Delegates to adapter, overlays foundation/status fields.
    """
    snap = _build_from_adapter(workspace_root=workspace_root)

    terminal_found = snap.get("terminal_dialogue_found", False)
    engine_found = snap.get("local_response_engine_found", False)
    all_features = snap.get("all_core_features_present", False)

    if all_features:
        runtime_status = "FOUNDATION_C_READY"
    elif terminal_found or engine_found:
        runtime_status = "FOUNDATION_C_PARTIAL"
    else:
        runtime_status = "FOUNDATION_C_PARTIAL"

    snap["foundation"] = "TRUE_RESPONSE_STRUCTURE"
    snap["status"] = runtime_status
    snap["source_mode"] = "EXISTING_BRODY_RESPONSE_STRUCTURE_ONLY"
    snap["local_response_engine"] = engine_found
    snap["terminal_structural_dialogue"] = terminal_found
    snap["response_md"] = snap.get("voice_source", "")
    snap["model_position"] = "LLM_OBSIDIEN_READONLY_ADVISORY"
    snap["creator_context_pattern"] = snap.get("creator_context_pattern_found", False)
    snap["used_by_api_now"] = False
    snap["voice_source"] = snap.get("voice_source", "FREEZE_METRICS_AND_MATRIX_ONLY")
    snap["memory_write"] = False
    snap["emits_act"] = False
    snap["decision_authority"] = "KX108_ONLY"
    return snap
