"""Brody Tree Signal Packet — F5B.

Readonly bridge from existing periphery.cognitive_trees formal computation
into Brody transverse runtime.

Does not decide.
Does not ACT.
Does not write memory.
Does not mutate kernel.
"""

from __future__ import annotations

from typing import Any

from periphery.cognitive_trees.tree_activation_vector import (
    N_TREES,
    DEFAULT_THETA,
    build_activation_vector,
)
from periphery.cognitive_trees.dominant_trees import find_dominant_trees
from periphery.cognitive_trees.shazam_cognitif import shazam_cognitif
from periphery.cognitive_trees.memory_world_mapper import map_memory_world


_BOUNDARY = {
    "decision_authority": "KX108_ONLY",
    "advisory_only": True,
    "readonly": True,
    "context_signal_only": True,
    "emits_act": False,
    "emits_verdict": False,
    "memory_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "can_decide": False,
    "can_emit_act": False,
}


def _clamp01(x: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(x))), 3)
    except Exception:
        return 0.0


def _word_features(text: str) -> dict[str, bool]:
    low = (text or "").lower()
    return {
        "mentions_tree": any(k in low for k in ("34 arbres", "arbres", "tree policy", "cognitive trees")),
        "mentions_memory": any(k in low for k in ("memoire", "mémoire", "memory", "graphiti", "neo4j", "contexte")),
        "mentions_governance": any(k in low for k in ("x108", "kx108", "gouvernance", "souverain", "authority", "kernel")),
        "mentions_ir": any(k in low for k in ("os trad", "ir", "reverse", "intermediate representation")),
        "mentions_value": any(k in low for k in ("valeur", "value", "gencoin", "proof", "preuve")),
        "mentions_action": any(k in low for k in ("act", "action", "execute", "exécute", "ecriture", "écriture")),
    }


def _derive_activation_from_text(text: str) -> list[float]:
    """Small deterministic text-derived activation.

    This is not semantic truth. It only produces a formal R^34 signal
    so Brody can expose the existing tree machinery in readonly mode.
    """
    f = _word_features(text)
    a = [0.0] * N_TREES

    if f["mentions_tree"]:
        for idx in (29, 30, 31, 32, 33):
            a[idx] = max(a[idx], 0.35)

    if f["mentions_memory"]:
        for idx in (23, 24, 25):
            a[idx] = max(a[idx], 0.45)

    if f["mentions_governance"]:
        for idx in (25, 26, 27, 28, 33):
            a[idx] = max(a[idx], 0.60)

    if f["mentions_ir"]:
        for idx in (9, 10, 11, 30, 31):
            a[idx] = max(a[idx], 0.50)

    if f["mentions_value"]:
        for idx in (26, 27, 28):
            a[idx] = max(a[idx], 0.55)

    if f["mentions_action"]:
        for idx in (19, 20, 21):
            a[idx] = max(a[idx], 0.50)

    return [_clamp01(x) for x in a]


def build_tree_signal_packet(
    *,
    text: str = "",
    vector_id: str = "brody_tree_signal_v1",
    activations: list[float] | None = None,
    theta: float = DEFAULT_THETA,
) -> dict[str, Any]:
    """Build TREE_SIGNAL_PACKET_V1 from existing formal cognitive tree modules."""
    raw_activations = activations if isinstance(activations, list) else _derive_activation_from_text(text)
    vector = build_activation_vector(vector_id, raw_activations)
    dominant = find_dominant_trees(vector, theta=theta)
    shazam = shazam_cognitif(vector, theta=theta)
    memory_world = map_memory_world(shazam)

    activation_sum = round(sum(vector.activations), 3)
    activation_density = round(sum(1 for x in vector.activations if x >= theta) / N_TREES, 3)

    packet = {
        "version": "TREE_SIGNAL_PACKET_V1",
        "mode": "SHADOW_READONLY",
        "tree_count": N_TREES,
        "theta": theta,
        "trees_textual_signal": bool(text),
        "trees_formal_computation": True,
        "activation_vector_present": True,
        "activation_vector": vector.to_dict(),
        "dominant_trees": dominant.to_dict(),
        "shazam": shazam.to_dict(),
        "memory_world": memory_world.to_dict(),
        "metrics": {
            "activation_sum": activation_sum,
            "activation_density": activation_density,
            "dominant_count": dominant.dominant_count,
            "pattern_count": len(shazam.patterns_detected),
            "memory_relevance": memory_world.memory_relevance,
            "world_relevance": memory_world.world_relevance,
        },
        "usable_for_gencoin_shadow": True,
        "usable_for_sigma": True,
        "usable_for_thermodynamics": True,
        "reason": "TREE_SIGNAL_PACKET_V1_FORMAL_READONLY",
        "notes": [
            "Tree signal remains advisory-only.",
            "Dominant trees are not authority.",
            "Tree activation is not truth.",
            "Tree signal cannot emit ACT or verdict.",
        ],
        **_BOUNDARY,
    }
    return {"tree_signal_packet": packet}
