"""
Brody Operator Loop Snapshot Adapter
======================================
Wraps freeze-sourced operator loop modules into an operator_loop_snapshot.

Sources: CURRENT_BRODY_OPERATOR_*.txt freeze pointers.
All 7 components freeze-sourced, V1_PASS, KX108_ONLY.

Boundary: readonly, Brody cannot execute, human operates, X108 decides.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_ptr(workspace: Path, name: str) -> str:
    ptr = workspace / f"CURRENT_BRODY_{name}.txt"
    if ptr.exists():
        try:
            for line in ptr.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
                if "=" in line and "STATUS" in line.split("=", 1)[0].strip():
                    return line.split("=", 1)[1].strip()
        except Exception:
            pass
    return "NOT_FOUND"


def build_operator_loop_snapshot(
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    """Build operator_loop_snapshot from freeze pointers."""
    workspace = workspace_root or Path(__file__).resolve().parents[2]

    components = {
        "command_gate": _check_ptr(workspace, "LOCAL_COMMAND_GATE_READONLY"),
        "human_command_packet": _check_ptr(workspace, "HUMAN_COMMAND_PACKET_READONLY"),
        "control_loop": _check_ptr(workspace, "OPERATOR_CONTROL_LOOP_BASELINE_FREEZE_READONLY"),
        "execution_line": _check_ptr(workspace, "OPERATOR_EXECUTION_LINE_BASELINE_FREEZE_READONLY"),
        "execution_receipt": _check_ptr(workspace, "OPERATOR_EXECUTION_RECEIPT_READONLY"),
        "handoff_line": _check_ptr(workspace, "OPERATOR_HANDOFF_LINE_BASELINE_FREEZE_READONLY"),
        "final_baseline": _check_ptr(workspace, "OPERATOR_FINAL_BASELINE_FREEZE_READONLY"),
    }

    pass_count = sum(1 for v in components.values() if "PASS" in v)
    total = len(components)

    return {
        "status": f"{pass_count}/{total} PASS",
        "source_mode": "EXISTING_FREEZE_POINTERS",
        "created_at": _now(),
        "command_gate": components["command_gate"],
        "human_command_packet": components["human_command_packet"],
        "control_loop": components["control_loop"],
        "execution_line": components["execution_line"],
        "execution_receipt": components["execution_receipt"],
        "handoff_line": components["handoff_line"],
        "final_baseline": components["final_baseline"],
        "brody_execute_allowed": False,
        "human_operator_required": True,
        "receipt_schema_only": True,
        "execution_allowed": False,
        "decision_authority_role": "KX108_ONLY",
        "brody_role": "PREPARE_AND_STRUCTURE_ONLY",
        "human_role": "VALIDATE_AND_OPERATE",
        "x108_role": "DECIDE_AND_AUTHORIZE",
        "readonly": True,
        "memory_write": False,
        "graphiti_write": False,
        "neo4j_write": False,
        "emits_act": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "decision_authority": "KX108_ONLY",
    }
