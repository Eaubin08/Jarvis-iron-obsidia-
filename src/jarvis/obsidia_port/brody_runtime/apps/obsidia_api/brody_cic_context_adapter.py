"""
Brody CIC Context Adapter
SCOPE: READONLY_BINDING_PREP
DECISION_AUTHORITY: KX108_ONLY

Injecte le contexte CIC readonly dans le packet runtime Brody
sous la clé `cic_readonly_context`.

Ce que Brody PEUT faire avec ce contexte :
  - afficher confirmed_metrics, partial_metrics, missing_metrics
  - expliquer central_rules, domain_relevance
  - exposer projection_not_prediction, memory_not_sovereign

Ce que Brody NE PEUT PAS faire :
  - décider, autoriser, bloquer
  - activer ACT
  - écrire en mémoire
  - modifier le kernel
  - promouvoir une métrique en décision
  - remplacer X108

Le contexte CIC est TOUJOURS injecté comme `cic_readonly_context`,
JAMAIS comme decision / gate / kernel_result / x108_result / authority_result.
"""
from __future__ import annotations

from typing import Any

from apps.obsidia_api.cic.cic_readonly_pack_provider import build_cic_readonly_context

_FORBIDDEN_INJECT_KEYS = frozenset(
    {"decision", "gate", "kernel_result", "x108_result", "authority_result"}
)

_BRODY_CIC_BOUNDARY: dict[str, Any] = {
    "can_display_confirmed_metrics": True,
    "can_display_partial_metrics": True,
    "can_display_missing_metrics": True,
    "can_display_central_rules": True,
    "can_display_domain_relevance": True,
    "can_display_projection_not_prediction": True,
    "can_display_memory_not_sovereign": True,
    "can_decide": False,
    "can_authorize": False,
    "can_block": False,
    "can_emit_act": False,
    "can_write_memory": False,
    "can_mutate_kernel": False,
    "can_promote_metric_to_decision": False,
    "can_replace_x108": False,
    "inject_key": "cic_readonly_context",
    "forbidden_inject_keys": sorted(_FORBIDDEN_INJECT_KEYS),
    "decision_authority": "KX108_ONLY",
}


def build_brody_cic_packet() -> dict[str, Any]:
    """
    Construit le packet CIC pour injection dans le runtime Brody.
    Retourne un dict avec la clé `cic_readonly_context`.
    Ne jamais injecter ce dict sous une clé interdite.
    """
    ctx = build_cic_readonly_context()

    return {
        "cic_readonly_context": {
            **ctx,
            "brody_boundary": _BRODY_CIC_BOUNDARY,
            "inject_key": "cic_readonly_context",
            "projection_not_prediction": "Projection is not prediction.",
            "memory_not_sovereign": "Memory is not sovereign.",
            "score_cannot_authorize_invariant": "A score cannot authorize what an invariant forbids.",
            "priority_chain": "Invariant > Reversibilite > Score > Projection",
        }
    }


def inject_cic_into_runtime_packet(
    runtime_packet: dict[str, Any],
) -> dict[str, Any]:
    """
    Injecte cic_readonly_context dans un packet runtime Brody existant.
    Lève ValueError si une clé interdite est déjà présente (guard).
    """
    for forbidden in _FORBIDDEN_INJECT_KEYS:
        if forbidden in runtime_packet:
            raise ValueError(
                f"CIC ne peut pas être injecté sous la clé interdite '{forbidden}'. "
                "Utiliser uniquement 'cic_readonly_context'."
            )

    packet = build_brody_cic_packet()
    runtime_packet["cic_readonly_context"] = packet["cic_readonly_context"]
    return runtime_packet
