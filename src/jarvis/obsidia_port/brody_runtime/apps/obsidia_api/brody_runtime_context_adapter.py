"""
Brody Runtime Context Adapter
================================
Assembles runtime_context top-level snapshot from all peripheral snapshots.

runtime_context is the single top-level envelope that the true_voice adapter
and the workbench use to access all Brody context at once.

No invention — purely assembles what the other adapters already produced.
Boundary: readonly, KX108_ONLY.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


RUNTIME_CONTEXT_BOUNDARY: dict[str, Any] = {
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


def build_runtime_context(
    semantic_query_snapshot: dict[str, Any] | None = None,
    authority_snapshot: dict[str, Any] | None = None,
    session_memory_snapshot: dict[str, Any] | None = None,
    project_memory_snapshot: dict[str, Any] | None = None,
    memory_response_chain_snapshot: dict[str, Any] | None = None,
    freeze_metrics_snapshot: dict[str, Any] | None = None,
    automation_snapshot: dict[str, Any] | None = None,
    candidate_memory_snapshot: dict[str, Any] | None = None,
    operator_loop_snapshot: dict[str, Any] | None = None,
    tree_policy_snapshot: dict[str, Any] | None = None,
    temporal_context_snapshot: dict[str, Any] | None = None,
    cognitive_modules_snapshot: dict[str, Any] | None = None,
    domain_sigma_envelope_snapshot: dict[str, Any] | None = None,
    tree_signal_packet_snapshot: dict[str, Any] | None = None,
    brody_full_context: dict[str, Any] | None = None,
    true_voice_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Assemble the top-level runtime_context from all existing snapshots.
    Every key must already exist — no invention, no defaults with invented values.
    """
    chain = memory_response_chain_snapshot or {}
    chain_pass = chain.get("status") == "BRODY_MEMORY_RESPONSE_CHAIN_PASS"
    chain_material = chain.get("material_quality", "UNKNOWN")

    proj = project_memory_snapshot or {}
    cand = candidate_memory_snapshot or {}
    oploop = operator_loop_snapshot or {}
    trees = tree_policy_snapshot or {}
    temporal = temporal_context_snapshot or {}
    cog = cognitive_modules_snapshot or {}
    tv = true_voice_snapshot or {}
    dse = domain_sigma_envelope_snapshot or {}
    tsp = tree_signal_packet_snapshot or {}
    auth = authority_snapshot or {}
    sem = semantic_query_snapshot or {}

    return {
        "status": "BRODY_RUNTIME_CONTEXT_READY",
        "created_at": _now(),
        # — Core snapshots ——————————————————————————————————————————————
        "semantic_query_snapshot": sem,
        "authority_snapshot": auth,
        "session_memory_snapshot": session_memory_snapshot or {},
        "project_memory_snapshot": proj,
        "memory_response_chain_snapshot": chain,
        "freeze_metrics_snapshot": freeze_metrics_snapshot or {},
        "automation_snapshot": automation_snapshot or {},
        "candidate_memory_snapshot": cand,
        "operator_loop_snapshot": oploop,
        "tree_policy_snapshot": trees,
        "temporal_context_snapshot": temporal,
        "cognitive_modules_snapshot": cog,
        "domain_sigma_envelope_snapshot": dse,
        "tree_signal_packet_snapshot": tsp,
        "brody_full_context": brody_full_context or {},
        "true_voice_snapshot": tv,
        # — Derived summaries ———————————————————————————————————————————
        "memory_chain_pass": chain_pass,
        "memory_material_quality": chain_material,
        "local_records_count": proj.get("local_records_count", 0),
        "text_excerpt_records_count": proj.get("text_excerpt_records_count", 0),
        "project_memory_usable": proj.get("usable_material", False),
        "candidate_ready": cand.get("status") == "CANDIDATE_MEMORY_READY",
        "operator_loop_ready": "7/7" in str(oploop.get("status", "")),
        "tree_policy_ready": trees.get("status") == "BRODY_TREE_POLICY_READY",
        "cognitive_modules_count": cog.get("total_known", 0),
        "domain_sigma_ready": bool(dse),
        "domain_sigma_domain": dse.get("domain", "UNKNOWN"),
        "domain_sigma_gate": dse.get("x108_gate", "UNKNOWN"),
        "domain_sigma_authority": dse.get("decision_authority", "UNKNOWN"),
        "tree_signal_ready": bool(tsp),
        "tree_signal_version": tsp.get("version", "UNKNOWN"),
        "tree_signal_dominant_count": tsp.get("dominant_count", 0),
        "tree_signal_patterns": tsp.get("patterns_detected", []),
        "voice_source": tv.get("voice_source", "UNKNOWN"),
        "topic": sem.get("topic", "GENERAL"),
        "request_type": auth.get("request_type", "INFORMATION_REQUEST"),
        # — Boundary ——————————————————————————————————————————————————
        **RUNTIME_CONTEXT_BOUNDARY,
    }
