"""
Foundation A — Brody Project Memory Adapter
=============================================
Synthesizes project_memory_snapshot from existing local sources:
  - Obsidia native memory index (runtime-bound readonly)
  - Memory candidate ledger (JSONL)
  - Freeze metrics snapshot (for context_packet_chain status)
  - CURRENT_BRODY_*.txt pointers (for module availability)

No invention — everything sourced from freeze files, indexes, and ledgers.
Boundary: readonly, KX108_ONLY, no write.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_project_memory_snapshot(
    workspace_root: Path | None = None,
    freeze_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build project_memory_snapshot from existing local sources.

    Sources checked:
      1. Obsidia native memory index V1
      2. Memory candidate ledger (JSONL)
      3. Freeze metrics (context_packet_chain availability)
      4. CURRENT_BRODY pointer files for module discovery

    Returns provider-neutral project memory inventory plus candidate ledger,
    module_availability, brody_memory_doc_status, project_context_summary.
    """
    workspace = workspace_root or Path(__file__).resolve().parents[2]

    # ?? 1. Obsidia Native Memory Index ????????????????????????????????????
    native_root = (
        workspace
        / "_obsidia_native_memory"
        / "OBSIDIA_NATIVE_MEMORY_INDEX_V1"
    )

    native_index_path = (
        native_root
        / "obsidia_native_memory_records_v1.jsonl"
    )

    native_manifest_path = (
        native_root
        / "OBSIDIA_NATIVE_MEMORY_INDEX_V1_MANIFEST.json"
    )

    native_index_found = False
    native_runtime_bound = False
    native_index_item_count = 0
    text_excerpt_count = 0
    native_tags_sample: list[str] = []
    source_file_used = "NOT_FOUND"

    try:
        from apps.obsidia_api.brody_obsidia_native_memory import (
            load_native_memory_index,
        )

        if (
            native_index_path.exists()
            and native_manifest_path.exists()
        ):
            manifest = json.loads(
                native_manifest_path.read_text(
                    encoding="utf-8-sig"
                )
            )

            native_runtime_bound = (
                manifest.get(
                    "runtime_bound"
                )
                is True
            )

            if native_runtime_bound:
                records = (
                    load_native_memory_index(
                        index_path=(
                            native_index_path
                        )
                    )
                )

                native_index_item_count = (
                    len(records)
                )

                text_excerpt_count = sum(
                    1
                    for record in records
                    if isinstance(
                        record,
                        dict,
                    )
                    and str(
                        record.get(
                            "text_excerpt"
                        )
                        or ""
                    ).strip()
                )

                for record in records[:5]:
                    if not isinstance(
                        record,
                        dict,
                    ):
                        continue

                    tags = record.get(
                        "tags",
                        [],
                    )

                    if isinstance(
                        tags,
                        list,
                    ):
                        native_tags_sample.extend(
                            str(tag)
                            for tag
                            in tags[:3]
                        )

                native_index_found = (
                    native_index_item_count
                    > 0
                )

                source_file_used = str(
                    native_index_path
                )

    except Exception:
        native_index_found = False
        native_runtime_bound = False
        native_index_item_count = 0
        text_excerpt_count = 0
        native_tags_sample = []
        source_file_used = "NOT_FOUND"
    # ── 2. Memory Candidate Ledger ────────────────────────────────────────
    candidate_ledger_path = workspace / "_local_audits" / "memory_candidate_ledger.jsonl"
    candidate_ledger_found = candidate_ledger_path.exists()
    candidate_count = 0

    if candidate_ledger_found:
        try:
            lines = candidate_ledger_path.read_text(encoding="utf-8").strip().splitlines()
            candidate_count = len([l for l in lines if l.strip()])
        except Exception:
            candidate_ledger_found = False

    # ── 3. Module availability from freeze pointers ───────────────────────
    module_status: dict[str, bool] = {}
    for pattern, name in [
        ("CONTEXT_PACKET_QUERY", "context_packet_query"),
        ("CONTENT_HYDRATION", "content_hydration"),
        ("LOCAL_RESPONSE_ENGINE", "local_response_engine"),
        ("CONTEXT_PACKET_CONSUMER", "context_packet_consumer"),
        ("AUTO_TRIAGE", "auto_triage"),
        ("PROJECT_INTAKE_CAPTURE", "project_intake_capture"),
    ]:
        ptr_files = list(workspace.glob(f"CURRENT_BRODY_{pattern}*.txt"))
        module_status[name] = len(ptr_files) > 0

    # ── 4. BrodyMemoryDoc status from freeze metrics ──────────────────────
    chain = (freeze_metrics or {}).get("context_packet_chain", {})
    brody_memory_doc_available = chain.get("status") == "CHAIN_PASS"

    # ?? 5. Native memory readiness ???????????????????????????????????????
    native_memory_ready = bool(
        native_index_found
        and native_runtime_bound
        and native_index_item_count > 0
    )
    # ?? 6. Project context summary ???????????????????????????????????????
    if native_memory_ready:
        contextual_material_status = (
            "HAS_PROJECT_MEMORY"
        )
    elif candidate_count > 0:
        contextual_material_status = (
            "PARTIAL_PROJECT_MEMORY"
        )
    else:
        contextual_material_status = (
            "NO_PROJECT_MEMORY"
        )

    # Local freeze pointer count
    freeze_pointers_count = len(list(workspace.glob("CURRENT_BRODY_*.txt")))

    missing_links: list[str] = []
    if not module_status.get("project_intake_capture"):
        missing_links.append("project_intake_capture_not_found")
    if native_index_item_count == 0:
        missing_links.append("obsidia_native_memory_empty_or_unavailable")

    return {
        "source_type": "OBSIDIA_NATIVE_MEMORY_PROJECT_SNAPSHOT",
        "source_mode": "OBSIDIA_NATIVE_MEMORY",
        "status": "BRODY_PROJECT_MEMORY_NATIVE_SOURCE_MAP_PASS",
        "created_at": _now(),
        "context_packet_query_found": module_status.get("context_packet_query", False),
        "content_hydration_found": module_status.get("content_hydration", False),
        "local_response_engine_found": module_status.get("local_response_engine", False),
        "brody_memory_doc_available": brody_memory_doc_available,
        "native_index_found": native_index_found,
        "native_runtime_bound": native_runtime_bound,
        "native_memory_ready": native_memory_ready,
        "native_index_item_count": native_index_item_count,
        "native_index_item_count": native_index_item_count,
        "local_records_count": native_index_item_count,
        "text_excerpt_records_count": text_excerpt_count,
        "usable_material": text_excerpt_count > 0,
        "cache_enabled": True,
        "source_file_used": source_file_used,
        "candidate_ledger_found": candidate_ledger_found,
        "candidate_ledger_count": candidate_count,
        "auto_triage_found": module_status.get("auto_triage", False),
        "contextual_material_status": contextual_material_status,
        "local_freeze_available": native_index_item_count > 0,
        "local_index_item_count": native_index_item_count,
        "freeze_pointers_count": freeze_pointers_count,
        "top_context_tags": native_tags_sample[:10],
        "project_memory_used_by_api": False,  # Set by API route
        "missing_links": missing_links,
        "source_files": [
            source_file_used,
            str(candidate_ledger_path) if candidate_ledger_found else "NOT_FOUND",
        ],
        "readonly": True,
        "memory_write": False,
        "emits_act": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "decision_authority": "KX108_ONLY",
    }
