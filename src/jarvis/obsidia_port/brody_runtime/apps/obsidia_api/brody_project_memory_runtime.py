"""
Foundation A — Brody Project Memory Runtime
=============================================
Canonical runtime entry point for Foundation A: Project Memory.

Delegates to brody_project_memory_adapter for source resolution,
then overlays runtime fields required by brody_full_runtime_reconnect:
  foundation, status (FOUNDATION_A_READY/PARTIAL), source_mode,
  available_sources, missing_links.

Boundary: readonly, KX108_ONLY, no write.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from apps.obsidia_api.brody_project_memory_adapter import (
    build_project_memory_snapshot as _build_from_adapter,
)


def build_project_memory_snapshot(
    workspace_root: Path | None = None,
    freeze_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Runtime-layer project memory snapshot (Foundation A).
    Delegates to adapter, overlays foundation/status fields.
    """
    snap = _build_from_adapter(workspace_root=workspace_root, freeze_metrics=freeze_metrics)

    material = snap.get("contextual_material_status", "NO_PROJECT_MEMORY")
    if material == "HAS_PROJECT_MEMORY":
        runtime_status = "FOUNDATION_A_READY"
    else:
        runtime_status = "FOUNDATION_A_PARTIAL"

    snap["foundation"] = "PROJECT_MEMORY"
    snap["status"] = runtime_status
    snap["source_mode"] = "OBSIDIA_NATIVE_MEMORY"
    snap["available_sources"] = {
        "obsidia_native_memory": snap.get("native_memory_ready", False),
        "brody_memory_doc": snap.get("brody_memory_doc_available", False),
        "context_packets": snap.get("context_packet_query_found", False),
        "project_ledgers": snap.get("candidate_ledger_found", False),
        "tree_policy": snap.get("auto_triage_found", False),
        "mmonde_or_34trees": False,
    }
    snap["obsidia_native_memory"] = snap.get("native_memory_ready", False)
    snap["brody_memory_doc"] = snap.get("brody_memory_doc_available", False)
    snap["context_packets"] = snap.get("context_packet_query_found", False)
    snap["project_ledgers"] = snap.get("candidate_ledger_found", False)
    snap["tree_policy"] = snap.get("auto_triage_found", False)
    snap["mmonde_or_34trees"] = False
    snap["used_by_api_now"] = False
    snap["missing_links"] = snap.get("missing_links", [])
    snap["memory_write"] = False
    snap["decision_authority"] = "KX108_ONLY"
    return snap
