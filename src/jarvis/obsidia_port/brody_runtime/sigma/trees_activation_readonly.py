"""
sigma/trees_activation_readonly.py — F71 Sigma 34 Trees Activation (readonly)

Maps canonical Sigma domains to their cognitive tree activation vectors.
Pure in-process.  No decision.  No ACT.  No write.  KX108_ONLY.
"""
from __future__ import annotations

from typing import Any

from sigma.registry import list_sigma_domains

TREES_VERSION = "F71"
N_TREES = 34
DEFAULT_DOMINANCE_THRESHOLD = 0.15

_BOUNDARY: dict[str, Any] = {
    "decision_authority": "KX108_ONLY",
    "readonly": True,
    "advisory_only": True,
    "allowed_to_decide": False,
    "emits_act": False,
    "emits_verdict": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "neo4j_write": False,
    "graphiti_write": False,
    "memory_write": False,
    "brody_decision": False,
}

# Sigma domain → primary tree indices (0-based, informational only).
# Derived from periphery.cognitive_trees domain mapping conventions.
SIGMA_DOMAIN_TREE_MAP: dict[str, list[int]] = {
    "bank": [0, 1, 2, 3, 8, 9, 12, 15],
    "trading": [0, 1, 4, 5, 9, 13, 16, 20],
    "ecom": [0, 2, 6, 7, 10, 14, 17, 21],
    "gps_defense_aviation": [0, 3, 8, 11, 15, 18, 22, 25],
}

_CANONICAL_DOMAINS = tuple(SIGMA_DOMAIN_TREE_MAP.keys())


def build_sigma_trees_activation(domain: str) -> dict[str, Any]:
    """Return readonly tree activation vector for a Sigma domain.

    Returns tree_indices for the domain and a dominance_threshold.
    Never decides, never ACTs.
    """
    tree_indices = SIGMA_DOMAIN_TREE_MAP.get(domain, [])
    activation_vector = [0.0] * N_TREES
    for idx in tree_indices:
        if 0 <= idx < N_TREES:
            activation_vector[idx] = 1.0

    return {
        "trees_version": TREES_VERSION,
        "domain": domain,
        "domain_valid": domain in _CANONICAL_DOMAINS,
        "n_trees": N_TREES,
        "dominance_threshold": DEFAULT_DOMINANCE_THRESHOLD,
        "tree_indices": tree_indices,
        "activation_vector_length": N_TREES,
        "active_trees_count": len(tree_indices),
        "activation_mode": "SIGMA_DOMAIN_READONLY",
        **_BOUNDARY,
    }


def validate_sigma_trees_activation() -> dict[str, Any]:
    """Validate the Sigma trees activation map (in-process only).

    Checks all canonical domains have non-empty tree mappings.
    Returns status=PASS/FAIL.
    """
    errors: list[str] = []
    domains = list_sigma_domains()

    for d in _CANONICAL_DOMAINS:
        if d not in domains:
            errors.append(f"missing_sigma_domain:{d}")
        indices = SIGMA_DOMAIN_TREE_MAP.get(d, [])
        if not indices:
            errors.append(f"empty_tree_map:{d}")
        for idx in indices:
            if not (0 <= idx < N_TREES):
                errors.append(f"invalid_tree_index:{d}:{idx}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "trees_version": TREES_VERSION,
        "n_trees": N_TREES,
        "dominance_threshold": DEFAULT_DOMINANCE_THRESHOLD,
        "canonical_domains": list(_CANONICAL_DOMAINS),
        "domain_count": len(_CANONICAL_DOMAINS),
        "errors": errors,
        **_BOUNDARY,
    }
