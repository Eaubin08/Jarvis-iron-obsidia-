"""
brody_runtime_cost_map — Mesure de la dissipation runtime Brody V3.

No IO. No network. No ACT. DECISION_AUTHORITY=KX108_ONLY.

Formules :
  dissipation_ratio = orchestration_ms / max(useful_compute_ms, 1)
  "Obsidia ne doit pas seulement décider juste ; il doit calculer sobrement."
  "Ce n'est pas un problème de cerveau, c'est un problème de circulation
   énergétique dans le runtime."
"""
from __future__ import annotations

from typing import Any


# ── Étapes connues par catégorie ──────────────────────────────────────────────

_USEFUL_STEPS: frozenset[str] = frozenset({
    "real_pipeline",
    "terminal_fallback",
    "graphiti_query",
    "neo4j_query",
})

_ORCHESTRATION_STEPS: frozenset[str] = frozenset({
    "automation_snapshot",
    "v1412a_final_answer",
    "true_voice_snapshot",
    "brody_full_context",
    "memory_response_chain",
    "runtime_context",
    "sigma_packet",
    "sigma_packet_initial",
    "anti_mismatch_signal",
    "reverse_os_bridge",
    "machination_packet",
})

_DIAGNOSTICS_STEPS: frozenset[str] = frozenset({
    "candidate_memory",
    "operator_loop",
    "tree_policy",
    "temporal_context",
    "cognitive_modules",
    "project_memory",
    "structured_response_snapshot",
    "freeze_metrics_snapshot",
    "authority_snapshot",
    "brody_readonly_activation",
    "graphiti_memory_readonly_activation",
    "world_action_bus_dry_run_activation",
    "action_gateway_hold_block_sandbox",
    "source_pack_context",
})

_MEMORY_STEPS: frozenset[str] = frozenset({
    "memory_readonly_packet",
    "memory_trace",
    "memory_candidate",
    "human_validation_gate",
})

_SCRUB_STEPS: frozenset[str] = frozenset({
    "scrub_secret_like_deep",
    "scrub_response",
    "scrub_final_answer",
})


def compute_runtime_cost_map(
    useful_compute_ms: float = 0.0,
    orchestration_ms: float = 0.0,
    diagnostics_ms: float = 0.0,
    memory_readonly_ms: float = 0.0,
    scrub_ms: float = 0.0,
    expensive_steps: list[str] | None = None,
    skipped_steps: list[str] | None = None,
    lazy_steps: list[str] | None = None,
    fastpath_type: str | None = None,
) -> dict[str, Any]:
    """
    Calcule la carte de coût runtime.

    Invariants :
    - decision_authority = KX108_ONLY (toujours)
    - emits_act = False (toujours)
    - canonical_write = False (toujours)

    Formule principale :
    dissipation_ratio = orchestration_ms / max(useful_compute_ms, 1)

    Un dissipation_ratio élevé signale une mauvaise circulation énergétique runtime.
    Cible : dissipation_ratio < 2.0 (idéalement < 0.5 en mode fastpath).
    """
    total_ms = (
        useful_compute_ms
        + orchestration_ms
        + diagnostics_ms
        + memory_readonly_ms
        + scrub_ms
    )
    dissipation_ratio = orchestration_ms / max(useful_compute_ms, 1.0)

    return {
        "useful_compute_ms": round(useful_compute_ms, 2),
        "orchestration_ms": round(orchestration_ms, 2),
        "diagnostics_ms": round(diagnostics_ms, 2),
        "memory_readonly_ms": round(memory_readonly_ms, 2),
        "scrub_ms": round(scrub_ms, 2),
        "total_ms": round(total_ms, 2),
        "dissipation_ratio": round(dissipation_ratio, 4),
        "fastpath_type": fastpath_type,
        "expensive_steps": list(expensive_steps or []),
        "skipped_steps": list(skipped_steps or []),
        "lazy_steps": list(lazy_steps or []),
        "decision_authority": "KX108_ONLY",
        "emits_act": False,
        "canonical_write": False,
        "graphiti_write": False,
        "neo4j_write": False,
    }


def fastpath_cost_map(fastpath_type: str | None = None) -> dict[str, Any]:
    """Carte de coût pour une réponse fastpath (dissipation minimale)."""
    return compute_runtime_cost_map(
        useful_compute_ms=0.0,
        orchestration_ms=2.0,
        diagnostics_ms=0.0,
        memory_readonly_ms=0.0,
        scrub_ms=0.0,
        fastpath_type=fastpath_type,
        expensive_steps=[],
        skipped_steps=[
            "real_pipeline",
            "automation_snapshot",
            "v1412a_final_answer",
            "true_voice_snapshot",
            "brody_full_context",
            "memory_response_chain",
            "runtime_context",
            "machination_packet",
            "sigma_packet",
        ],
        lazy_steps=[],
    )


def lazy_cost_map(pipeline_ms: float = 1100.0) -> dict[str, Any]:
    """Carte de coût pour un fallback lazy (compact sans fastpath)."""
    return compute_runtime_cost_map(
        useful_compute_ms=pipeline_ms,
        orchestration_ms=10.0,
        diagnostics_ms=0.0,
        memory_readonly_ms=0.0,
        scrub_ms=0.0,
        fastpath_type="compact_lazy_fallback",
        expensive_steps=[],
        skipped_steps=[
            "automation_snapshot",
            "v1412a_final_answer",
            "true_voice_snapshot",
            "brody_full_context",
            "memory_response_chain",
            "runtime_context",
        ],
        lazy_steps=[
            "automation_snapshot",
            "true_voice_snapshot",
            "brody_full_context",
        ],
    )


def full_pipeline_cost_map(
    pipeline_ms: float = 1100.0,
    handler_ms: float = 21000.0,
) -> dict[str, Any]:
    """Carte de coût pour le pipeline complet (mode normal sans fastpath)."""
    orchestration_ms = max(handler_ms - pipeline_ms, 0.0)
    return compute_runtime_cost_map(
        useful_compute_ms=pipeline_ms,
        orchestration_ms=orchestration_ms,
        diagnostics_ms=orchestration_ms * 0.6,
        memory_readonly_ms=0.0,
        scrub_ms=1.0,
        fastpath_type=None,
        expensive_steps=[
            "automation_snapshot",
            "true_voice_snapshot",
            "brody_full_context",
            "runtime_context",
            "machination_packet",
        ],
        skipped_steps=[],
        lazy_steps=[],
    )
