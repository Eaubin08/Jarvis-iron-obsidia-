"""
Tree Activation Vector — R^34, a_i ∈ [0,1].
Context signal only. Tree activation != truth. Dominant tree != authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

N_TREES = 34
DEFAULT_THETA = 0.15


@dataclass
class TreeActivationVector:
    vector_id: str
    activations: list[float]
    context_signal_only: bool = True
    can_decide: bool = False
    can_emit_act: bool = False

    def __post_init__(self):
        if len(self.activations) != N_TREES:
            raise ValueError(f"Activation vector must have {N_TREES} elements, got {len(self.activations)}")
        self.activations = [max(0.0, min(1.0, a)) for a in self.activations]

    def to_dict(self) -> dict[str, Any]:
        return {
            "vector_id": self.vector_id,
            "activations": self.activations,
            "context_signal_only": self.context_signal_only,
            "can_decide": self.can_decide,
            "can_emit_act": self.can_emit_act,
        }


def build_activation_vector(vector_id: str, activations: list[float]) -> TreeActivationVector:
    padded = (activations + [0.0] * N_TREES)[:N_TREES]
    return TreeActivationVector(
        vector_id=vector_id,
        activations=padded,
        context_signal_only=True,
        can_decide=False,
        can_emit_act=False,
    )


def uniform_activation(vector_id: str, value: float = 0.1) -> TreeActivationVector:
    return build_activation_vector(vector_id, [value] * N_TREES)
