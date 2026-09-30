"""
Shazam Cognitif — identifies cognitive patterns from activation vectors.
Context packet only. Never a decision. Never ACT.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .tree_activation_vector import TreeActivationVector
from .dominant_trees import find_dominant_trees, DominantTreeResult

_PATTERN_MAP = {
    frozenset({2, 3, 4}):   "LANGUAGE_PATTERN_DETECTED",
    frozenset({5, 6, 15}):  "CAUSAL_REASONING_PATTERN",
    frozenset({7, 8, 29}):  "RISK_CONFLICT_PATTERN",
    frozenset({10, 11, 27}): "AUTHORITY_TRUST_PATTERN",
    frozenset({13, 14, 15}): "EPISTEMIC_UNCERTAINTY_PATTERN",
    frozenset({26, 27, 33}): "GOVERNANCE_SOVEREIGNTY_PATTERN",
}


@dataclass
class ShazamCognitifResult:
    vector_id: str
    patterns_detected: list[str]
    dominant_result: DominantTreeResult
    context_signal_only: bool = True
    can_decide: bool = False
    can_emit_act: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "vector_id": self.vector_id,
            "patterns_detected": self.patterns_detected,
            "dominant_trees": self.dominant_result.dominant_names,
            "dominant_count": self.dominant_result.dominant_count,
            "context_signal_only": self.context_signal_only,
            "can_decide": self.can_decide,
            "can_emit_act": self.can_emit_act,
        }


def shazam_cognitif(vector: TreeActivationVector, theta: float = 0.15) -> ShazamCognitifResult:
    dominant = find_dominant_trees(vector, theta=theta)
    dominant_set = frozenset(dominant.dominant_ids)
    patterns = []
    for pattern_key, pattern_name in _PATTERN_MAP.items():
        if pattern_key.issubset(dominant_set):
            patterns.append(pattern_name)
    return ShazamCognitifResult(
        vector_id=vector.vector_id,
        patterns_detected=patterns,
        dominant_result=dominant,
        context_signal_only=True,
        can_decide=False,
        can_emit_act=False,
    )
