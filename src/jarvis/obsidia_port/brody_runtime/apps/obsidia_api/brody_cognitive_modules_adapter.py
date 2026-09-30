"""
Brody Cognitive Modules Adapter
=================================
Exposes the cognitive module resolution table as a runtime snapshot.
Uses the 13-module canonical resolution already established.

Sources:
  - docs/freeze/BRODY_COGNITIVE_MODULE_RESOLUTION_TABLE.json
  - Existing adapters (project_memory, session_memory, temporal_context, etc.)

No invention — maps canonical names to existing runtime coverage.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_MODULES = [
    {"name": "AVDR", "resolution": "EXACT_FOUND", "covered_by": "avdr_phase_mapper.py", "branchable": True, "active": False},
    {"name": "GhostLogic", "resolution": "DESIGN_SPEC_NOT_IMPLEMENTED", "covered_by": None, "branchable": False, "active": False, "needs_operator_spec": True},
    {"name": "Continuum", "resolution": "COVERED_BY_EXISTING_MODULE", "covered_by": "session_memory_snapshot, temporal_context_snapshot", "branchable": True, "active": True},
    {"name": "ERA", "resolution": "DESIGN_SPEC_NOT_IMPLEMENTED", "covered_by": None, "branchable": False, "active": False, "needs_operator_spec": True},
    {"name": "LTCU+", "resolution": "TEST_ONLY", "covered_by": "hexaflux_transition tests", "branchable": False, "active": False},
    {"name": "Verbatia", "resolution": "FULLY_BRANCHED", "covered_by": "brody_true_voice_adapter.py", "branchable": True, "active": True},
    {"name": "Inference_Aubin", "resolution": "PARTIALLY_COVERED", "covered_by": "brody_rights_authority_matrix.py, semantic_query_router", "branchable": True, "active": True},
    {"name": "MEMZUM", "resolution": "FULLY_BRANCHED", "covered_by": "project_memory_snapshot, session_memory_snapshot, memory_response_chain, OBSIDIA_NATIVE_MEMORY", "branchable": True, "active": True},
    {"name": "Capsule_Evolution", "resolution": "COVERED_BY_EXISTING_MODULE", "covered_by": "temporal_context.future_context, candidate_memory_snapshot", "branchable": True, "active": True},
    {"name": "Horloge_Cognitive", "resolution": "PROOF_ONLY", "covered_by": "Temporal*.lean (5 proofs)", "branchable": False, "active": True},
    {"name": "Cristal_Sortie", "resolution": "FULLY_BRANCHED", "covered_by": "brody_true_voice_adapter.py, brody_text_encoding.py", "branchable": True, "active": True},
    {"name": "Collecteur_Epiphanies", "resolution": "COVERED_BY_EXISTING_MODULE", "covered_by": "candidate_memory_snapshot, presave_buffer, auto_triage", "branchable": True, "active": True},
    {"name": "Simulateur_Memoires", "resolution": "PARTIALLY_COVERED", "covered_by": "memory_response_chain (replay), temporal_context.future", "branchable": True, "active": True},
]

_PAST_MODULES = ["MEMZUM", "Continuum", "Collecteur_Epiphanies"]
_PRESENT_MODULES = ["Verbatia", "Inference_Aubin", "Cristal_Sortie", "MEMZUM"]
_FUTURE_MODULES = ["AVDR", "Capsule_Evolution", "Simulateur_Memoires"]
_PROOF_MODULES = ["Horloge_Cognitive", "LTCU+"]
_DESIGN_MODULES = ["GhostLogic", "ERA"]


def build_cognitive_modules_snapshot(
    user_message: str = "",
) -> dict[str, Any]:
    """Build cognitive_modules_snapshot from the canonical resolution table."""
    modules_found = [m["name"] for m in _MODULES if m["resolution"] not in ("DESIGN_SPEC_NOT_IMPLEMENTED",)]
    modules_missing = [m["name"] for m in _MODULES if m["resolution"] == "DESIGN_SPEC_NOT_IMPLEMENTED"]
    modules_active = [m["name"] for m in _MODULES if m.get("active")]

    return {
        "status": "BRODY_COGNITIVE_MODULES_SNAPSHOT_PASS",
        "source_mode": "CANONICAL_RESOLUTION_TABLE",
        "created_at": _now(),
        "total_known": len(_MODULES),
        "modules_found": len(modules_found),
        "modules_missing_after_multipass": len(modules_missing),
        "modules_missing_names": modules_missing,
        "modules_active": modules_active,
        "modules": _MODULES,
        "past_present_future_mapping": {
            "past": _PAST_MODULES,
            "present": _PRESENT_MODULES,
            "future": _FUTURE_MODULES,
            "control_proof": _PROOF_MODULES,
            "design_spec_pending": _DESIGN_MODULES,
        },
        "readonly": True,
        "memory_write": False,
        "graphiti_write": False,
        "neo4j_write": False,
        "emits_act": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "decision_authority": "KX108_ONLY",
    }
