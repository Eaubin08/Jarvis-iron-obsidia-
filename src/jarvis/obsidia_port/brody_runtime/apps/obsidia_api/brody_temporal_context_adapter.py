"""
Brody Temporal Context Adapter
================================
Synthesizes temporal_context_snapshot from existing sources:
  - Session memory (past)
  - Memory response chain + authority (present)
  - Candidate memory + AVDR phase (future)
  - Temporal*.lean proofs + freeze metrics (proof/control)

No invention — past/present/future derived from existing snapshots.
Boundary: readonly, KX108_ONLY.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_temporal_context_snapshot(
    session_memory: dict[str, Any] | None = None,
    memory_chain: dict[str, Any] | None = None,
    candidate_memory: dict[str, Any] | None = None,
    freeze_metrics: dict[str, Any] | None = None,
    semantic_query: dict[str, Any] | None = None,
    authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build temporal_context from existing snapshots."""
    sm = session_memory or {}
    mc = memory_chain or {}
    cm = candidate_memory or {}
    fm = freeze_metrics or {}
    sq = semantic_query or {}
    au = authority or {}

    # ── Past context (history, traces, session) ──────────────────────────
    past = {
        "session_history_available": sm.get("session_ledger_v2_found", False),
        "previous_topic": sm.get("conversation_topic", ""),
        "previous_user_message": sm.get("previous_user_message", ""),
        "record_count": sm.get("record_count", 0),
        "freeze_refs_count": fm.get("pointer_file_count", 0),
        "trace_refs": [sm.get("session_dir", "")] if sm.get("session_dir") else [],
    }

    # ── Present context (live, active, current) ──────────────────────────
    present = {
        "current_topic": sq.get("topic", "GENERAL"),
        "primary_query": sq.get("primary_query", ""),
        "memory_chain_status": mc.get("status", "UNAVAILABLE"),
        "query_results_count": mc.get("query_results_count", 0),
        "authority_status": au.get("request_type", "PURE_RESPONSE"),
        "material_quality": mc.get("material_quality", ""),
    }

    # ── Future context (projection, candidates, advisory only) ────────────
    future = {
        "candidate_pipeline_available": cm.get("status", "").startswith("CANDIDATE_MEMORY"),
        "candidate_ledger_count": cm.get("candidate_ledger_count", 0),
        "gates_required": cm.get("gates_required", 6),
        "projection_advisory_only": True,
        "avdr_phase_available": False,  # AVDR phase mapper requires gencoin sandbox
        "next_steps_advisory": [
            "final_answer_advisory",
            "context_packet_readonly",
            "authority_snapshot_readonly",
        ],
    }

    # ── Control / proof context ──────────────────────────────────────────
    control = {
        "readonly": True,
        "decision_authority": "KX108_ONLY",
        "emits_act": False,
        "emits_verdict": False,
        "memory_write": False,
        "graphiti_write": False,
        "neo4j_write": False,
        "kernel_mutation": False,
        "x108_mutation": False,
        "audit_refs": [],
        "receipt_refs": [],
        "proof_refs": [
            "proofs/lean/Obsidia/TemporalX108_3Layers.lean",
        ],
        # ── Proof surface audit refs (attestation-only, runtime_bound=false) ──
        "proof_surface_manifest":  "proofs/LEAN_PROOF_SURFACE_MANIFEST.json",
        "math_memory_closure_map": "periphery/obsidure_math_memory_readonly/MATH_MEMORY_LEAN_CLOSURE_MAP.json",
        "domain_proof_packs": [
            "proofs/domain_packs/bank_proof_pack.json",
            "proofs/domain_packs/trading_proof_pack.json",
            "proofs/domain_packs/gps_aviation_proof_pack.json",
        ],
        "proof_surface_version": "1.0.0",
        "proof_refs_attached":   True,
        "runtime_bound":         False,
        "lean_decides":          False,
        "attestation_only":      True,
    }

    # Determine overall status
    has_past = bool(past["session_history_available"] or past["freeze_refs_count"] > 0)
    has_present = bool(mc.get("status") and mc.get("status") != "ERROR")
    has_future = bool(future["candidate_pipeline_available"])
    has_proof = True  # Always: KX108_ONLY boundary is proof layer

    all_layers = sum([has_past, has_present, has_future, has_proof])
    if all_layers >= 4:
        status = "TEMPORAL_CONTEXT_FULL"
    elif all_layers >= 2:
        status = "TEMPORAL_CONTEXT_PARTIAL"
    else:
        status = "TEMPORAL_CONTEXT_MINIMAL"

    return {
        "status": status,
        "layers_available": all_layers,
        "layers_total": 4,
        "source_mode": "EXISTING_SNAPSHOT_SYNTHESIS",
        "created_at": _now(),
        "past_context": past,
        "present_context": present,
        "future_context": future,
        "control_proof_context": control,
        "readonly": True,
        "memory_write": False,
        "graphiti_write": False,
        "neo4j_write": False,
        "emits_act": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "x108_mutation": False,
        "decision_authority": "KX108_ONLY",
    }
