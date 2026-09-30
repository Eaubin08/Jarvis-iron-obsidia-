"""
Dominant Trees — DominantTrees(e) = {i | a_i >= theta}.
theta_default = 0.15. Dominant tree != authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .tree_registry import get_tree_by_id
from .tree_activation_vector import TreeActivationVector, DEFAULT_THETA


@dataclass
class DominantTreeResult:
    vector_id: str
    theta: float
    dominant_ids: list[int]        # 0-based activation dimensions (historical contract)
    dominant_names: list[str]
    dominant_count: int
    context_signal_only: bool = True
    dominant_is_authority: bool = False
    dominant_tree_ids: list[int] = field(default_factory=list)   # canonical TREE_IDs 1..34
    compiled_provenance: dict = field(default_factory=dict)       # keyed by TREE_ID

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "vector_id": self.vector_id,
            "theta": self.theta,
            "dominant_ids": self.dominant_ids,
            "dominant_names": self.dominant_names,
            "dominant_count": self.dominant_count,
            "context_signal_only": self.context_signal_only,
            "dominant_is_authority": self.dominant_is_authority,
        }
        if self.dominant_tree_ids:
            d["dominant_tree_ids"] = self.dominant_tree_ids
        if self.compiled_provenance:
            d["compiled_provenance"] = self.compiled_provenance
        return d


def find_dominant_trees(
    vector: TreeActivationVector,
    theta: float = DEFAULT_THETA,
) -> DominantTreeResult:
    # dominant_ids keeps the 0-based activation dimensions (historical contract).
    # tree_id = activation_dimension + 1 (canonical: activation_dimension = tree_id - 1).
    dominant_dims = [dim for dim, a in enumerate(vector.activations) if a >= theta]
    dominant_names: list[str] = []
    dominant_tree_ids: list[int] = []
    compiled_provenance: dict[int, dict] = {}
    for dim in dominant_dims:
        tree_id = dim + 1
        tree = get_tree_by_id(tree_id)
        dominant_names.append(tree.name if tree else f"TREE_{tree_id}")
        dominant_tree_ids.append(tree_id)
        if tree and tree.compilation_status is not None:
            compiled_provenance[tree_id] = {
                "tree_id":              tree_id,
                "activation_dimension": dim,
                "source_row_id":        tree.source_row_id,
                "source_pack":          tree.source_pack,
                "source_provenance":    tree.source_provenance,
                "source_reference":     tree.source_reference,
                "compilation_status":   tree.compilation_status,
                "authority":            tree.authority,
                "readonly":             tree.readonly,
                "emits_act":            tree.emits_act,
                "can_decide":           tree.can_decide,
                "memory_write":         tree.memory_write,
                "graphiti_write":       tree.graphiti_write,
                "neo4j_write":          tree.neo4j_write,
            }

    return DominantTreeResult(
        vector_id=vector.vector_id,
        theta=theta,
        dominant_ids=dominant_dims,      # historical: 0-based activation dimensions
        dominant_names=dominant_names,
        dominant_count=len(dominant_dims),
        context_signal_only=True,
        dominant_is_authority=False,
        dominant_tree_ids=dominant_tree_ids,
        compiled_provenance=compiled_provenance,
    )
