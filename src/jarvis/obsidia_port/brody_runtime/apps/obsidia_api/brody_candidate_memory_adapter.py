"""
Brody Candidate Memory Snapshot Adapter
=========================================
Wraps existing freeze-sourced modules into a candidate_memory_snapshot.

Sources:
  - session_presave_buffer_readonly V1
  - auto_triage_memory_intake_readonly V1
  - graphiti_candidate_review_gate_readonly V1
  - memory_candidate_ledger (JSONL)

No invention — reports what exists in freeze files and ledgers.
All writes disabled: CANDIDATE_ONLY, memory_write=false.
Boundary: readonly, KX108_ONLY.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_candidate_memory_snapshot(
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    """Build candidate_memory_snapshot from existing freeze sources."""
    workspace = workspace_root or Path(__file__).resolve().parents[2]

    # Check presave buffer
    presave_ptr = workspace / "CURRENT_BRODY_SESSION_PRESAVE_BUFFER_READONLY.txt"
    presave_found = presave_ptr.exists()
    presave_status = "NOT_FOUND"
    if presave_found:
        presave_status = "READY"

    # Check auto-triage
    triage_ptr = workspace / "CURRENT_BRODY_AUTO_TRIAGE_MEMORY_INTAKE_READONLY.txt"
    triage_found = triage_ptr.exists()
    triage_status = "NOT_FOUND"
    if triage_found:
        triage_status = "READY"

    # Check review gate
    review_ptr = workspace / "CURRENT_BRODY_GRAPHITI_CANDIDATE_REVIEW_GATE_READONLY.txt"
    review_found = review_ptr.exists()
    review_status = "NOT_FOUND"
    if review_found:
        review_status = "READY"

    # Check import apply
    apply_ptr = workspace / "CURRENT_BRODY_GRAPHITI_IMPORT_APPLY_GUARDED_MANUAL_ONLY.txt"
    apply_found = apply_ptr.exists()
    apply_status = "NOT_FOUND"
    if apply_found:
        apply_status = "GUARDED_MANUAL_ONLY"

    # Check candidate ledger
    ledger_path = workspace / "_local_audits" / "memory_candidate_ledger.jsonl"
    ledger_found = ledger_path.exists()
    candidate_count = 0
    latest_candidates: list[dict] = []

    if ledger_found:
        try:
            lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
            records = [json.loads(l) for l in lines if l.strip()]
            candidate_count = len(records)
            latest_candidates = records[-3:] if records else []
        except Exception:
            ledger_found = False

    all_ready = presave_found and triage_found and review_found

    return {
        "status": "CANDIDATE_MEMORY_READY" if all_ready else "CANDIDATE_MEMORY_PARTIAL",
        "source_mode": "EXISTING_FREEZE_SOURCES",
        "created_at": _now(),
        "presave_buffer_found": presave_found,
        "presave_buffer_status": presave_status,
        "auto_triage_found": triage_found,
        "auto_triage_status": triage_status,
        "graphiti_review_gate_found": review_found,
        "graphiti_review_gate_status": review_status,
        "graphiti_import_apply_found": apply_found,
        "graphiti_import_apply_status": apply_status,
        "candidate_ledger_found": ledger_found,
        "candidate_ledger_count": candidate_count,
        "latest_candidates": latest_candidates,
        "pipeline": "CANDIDATE_ONLY",
        "gates_required": 6,
        "auto_promotion": False,
        "memory_write": False,
        "graphiti_write": False,
        "neo4j_write": False,
        "emits_act": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "decision_authority": "KX108_ONLY",
    }
