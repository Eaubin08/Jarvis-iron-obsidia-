"""
Brody MEMZUM Activation Adapter ? C2B-M2A
==========================================

Canonical provider-neutral memory activation envelope.

MEMZUM does NOT retrieve memory.
MEMZUM does NOT know Graphiti, Neo4j, or any retrieval provider.
MEMZUM does NOT ACT, decide for KX108, or mutate memory.

It consolidates already-existing cognitive memory signals into one
canonical assessment consumed later by the memory routing layer.

Current canonical activation source:
    point_cloud.memory_packet_required

Supporting evidence:
    - micro_core.bio_animal_signal.memory_relevance_signal
    - balance_engine.balance_memoire.tension
    - point_cloud axis_13_memory
    - domain_detected
    - intent_type
    - adversarial state

DECISION_AUTHORITY = KX108_ONLY.
"""

from __future__ import annotations

from typing import Any


MEMZUM_BOUNDARY: dict[str, Any] = {
    "readonly": True,
    "advisory_only": True,
    "provider_neutral": True,
    "retrieval_performed": False,
    "memory_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "emits_act": False,
    "emits_verdict": False,
    "decision_authority": "KX108_ONLY",
}


def _axis13_memory(point_cloud: dict[str, Any]) -> float:
    """
    Read the existing memory axis without creating a new heuristic.

    Runtime variants historically expose the 21D payload either as:
      - vector_21d
      - axes / axis_13_memory

    Missing evidence degrades to 0.0.
    """
    vector = point_cloud.get("vector_21d")

    if isinstance(vector, dict):
        for key in (13, "13", "axis_13_memory"):
            if key in vector:
                try:
                    return float(vector[key])
                except (TypeError, ValueError):
                    return 0.0

    axes = point_cloud.get("axes", {})
    if isinstance(axes, dict):
        try:
            return float(axes.get("axis_13_memory", 0.0))
        except (TypeError, ValueError):
            return 0.0

    return 0.0


def _memory_relevance_signal(micro_core: dict[str, Any]) -> float:
    bio = micro_core.get("bio_animal_signal", {})
    if not isinstance(bio, dict):
        return 0.0

    try:
        return float(bio.get("memory_relevance_signal", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _memory_balance_tension(balance_output: dict[str, Any]) -> float:
    balances = balance_output.get("balances", {})
    if not isinstance(balances, dict):
        return 0.0

    memory_balance = balances.get("balance_memoire", {})
    if not isinstance(memory_balance, dict):
        return 0.0

    try:
        return float(memory_balance.get("tension", 0.0))
    except (TypeError, ValueError):
        return 0.0


def evaluate_memzum_activation(
    *,
    micro_core: dict[str, Any] | None = None,
    balance_output: dict[str, Any] | None = None,
    point_cloud: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Produce the canonical MEMZUM memory-activation assessment.

    This function intentionally DOES NOT invent a second activation rule.

    The currently established cognitive runtime already emits:
        memory_packet_required

    MEMZUM freezes that signal as the canonical activation result while
    exposing its cognitive evidence in a provider-neutral envelope.
    """
    mc = micro_core or {}
    bal = balance_output or {}
    pc = point_cloud or {}

    is_adversarial = bool(mc.get("is_adversarial", False))

    # Existing canonical signal.
    packet_required = bool(pc.get("memory_packet_required", False))

    # Redundant safety bound:
    # an adversarial interaction cannot activate memory retrieval.
    memory_required = bool(packet_required and not is_adversarial)

    if is_adversarial:
        reason = "MEMORY_BLOCKED_ADVERSARIAL"
    elif memory_required:
        reason = "MEMORY_REQUIRED_COGNITIVE_SIGNAL"
    else:
        reason = "MEMORY_NOT_REQUIRED"

    domain_detected = (
        mc.get("domain_detected")
        or pc.get("domain_detected")
    )

    intent_type = mc.get("intent_type", "unknown")

    return {
        "module": "MEMZUM",
        "version": "C2B_M2A_V0",
        "status": "MEMZUM_ACTIVATION_PASS",
        "memory_required": memory_required,
        "reason": reason,

        # Existing cognitive evidence only.
        "activation_basis": {
            "memory_packet_required": packet_required,
            "axis_13_memory": _axis13_memory(pc),
            "memory_relevance_signal": _memory_relevance_signal(mc),
            "balance_memoire_tension": _memory_balance_tension(bal),
            "domain_detected": domain_detected,
            "intent_type": intent_type,
            "is_adversarial": is_adversarial,
        },

        "domain_detected": domain_detected,
        "intent_type": intent_type,

        **MEMZUM_BOUNDARY,
    }
