"""
Brody Tree Policy Adapter
===========================
Reads tree policy from authority_snapshot and freeze pointers.
Synthesizes safe/blocked tree classification.

Sources:
  - brody_rights_authority_matrix.py (tree_policy field)
  - CURRENT_BRODY_GRAPHITI_CANDIDATE_REVIEW_GATE_READONLY.txt
  - 34 arbres contextual data from project memory

Boundary: readonly, KX108_ONLY.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_tree_policy_snapshot(
    workspace_root: Path | None = None,
    authority_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build tree_policy_snapshot from existing sources."""
    workspace = workspace_root or Path(__file__).resolve().parents[2]
    au = authority_snapshot or {}

    # Get tree policy from authority if present
    tree_policy = au.get("tree_policy", "BLOCK")
    safe_trees = au.get("safe_trees", [])
    blocked_action = au.get("blocked_action", [])
    blocked_memory = au.get("blocked_memory", [])
    blocked_agi = au.get("blocked_agi", [])

    # Check if 34 arbres references exist in project memory
    trees_refs: list[str] = []
    audit_34_path = workspace / "docs" / "cognitive_trees"
    if audit_34_path.exists():
        try:
            trees_refs = [f.stem for f in list(audit_34_path.glob("*.md"))[:5]]
        except Exception:
            pass

    return {
        "status": "BRODY_TREE_POLICY_READY",
        "source_mode": "EXISTING_SOURCES",
        "created_at": _now(),
        "tree_policy": tree_policy,
        "safe_trees": safe_trees if safe_trees else ["TREE_X108_BOUNDARY"],
        "blocked_action": blocked_action if blocked_action else [],
        "blocked_memory": blocked_memory if blocked_memory else [],
        "blocked_agi": blocked_agi if blocked_agi else [],
        "total_known_trees": 34,
        "trees_docs_found": len(trees_refs),
        "trees_docs_sample": trees_refs[:5],
        "readonly": True,
        "memory_write": False,
        "graphiti_write": False,
        "neo4j_write": False,
        "emits_act": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "decision_authority": "KX108_ONLY",
    }
