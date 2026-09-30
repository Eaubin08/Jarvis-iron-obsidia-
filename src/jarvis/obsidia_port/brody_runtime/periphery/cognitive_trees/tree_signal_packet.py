from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .tree_activation_vector import build_activation_vector
from .shazam_cognitif import shazam_cognitif
from .memory_world_mapper import map_memory_world


@dataclass
class TreeSignalPacket:
    signal_id: str
    vector_id: str
    dominant_ids: list[int]
    dominant_trees: list[str]
    dominant_count: int
    patterns_detected: list[str]
    active_domains: list[str]
    memory_relevance: float
    world_relevance: float
    domain_sigma_envelope: dict[str, Any] = field(default_factory=dict)

    version: str = "TREE_SIGNAL_PACKET_V1"
    mode: str = "READONLY_TREE_SIGNAL"
    source: str = "F27_TREE_SIGNAL_BRIDGE"
    tree_signal_packet: bool = True
    domain_sigma_attached: bool = False

    readonly: bool = True
    advisory_only: bool = True
    context_signal_only: bool = True
    can_decide: bool = False
    can_emit_act: bool = False
    emits_act: bool = False
    emits_verdict: bool = False
    memory_write: bool = False
    graphiti_write: bool = False
    neo4j_write: bool = False
    kernel_mutation: bool = False
    x108_mutation: bool = False
    decision_authority: str = "KX108_ONLY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "mode": self.mode,
            "source": self.source,
            "tree_signal_packet": self.tree_signal_packet,
            "signal_id": self.signal_id,
            "vector_id": self.vector_id,
            "dominant_ids": self.dominant_ids,
            "dominant_trees": self.dominant_trees,
            "dominant_count": self.dominant_count,
            "patterns_detected": self.patterns_detected,
            "active_domains": self.active_domains,
            "memory_relevance": self.memory_relevance,
            "world_relevance": self.world_relevance,
            "domain_sigma_envelope": self.domain_sigma_envelope,
            "domain_sigma_attached": self.domain_sigma_attached,
            "readonly": self.readonly,
            "advisory_only": self.advisory_only,
            "context_signal_only": self.context_signal_only,
            "can_decide": self.can_decide,
            "can_emit_act": self.can_emit_act,
            "emits_act": self.emits_act,
            "emits_verdict": self.emits_verdict,
            "memory_write": self.memory_write,
            "graphiti_write": self.graphiti_write,
            "neo4j_write": self.neo4j_write,
            "kernel_mutation": self.kernel_mutation,
            "x108_mutation": self.x108_mutation,
            "decision_authority": self.decision_authority,
        }


def build_tree_signal_packet(
    signal_id: str,
    activations: list[float],
    *,
    theta: float = 0.15,
    domain_sigma_envelope: dict[str, Any] | None = None,
) -> TreeSignalPacket:
    vector = build_activation_vector(signal_id, activations)
    shazam = shazam_cognitif(vector, theta=theta)
    memory_world = map_memory_world(shazam)

    dse = domain_sigma_envelope if isinstance(domain_sigma_envelope, dict) else {}

    return TreeSignalPacket(
        signal_id=signal_id,
        vector_id=vector.vector_id,
        dominant_ids=shazam.dominant_result.dominant_ids,
        dominant_trees=shazam.dominant_result.dominant_names,
        dominant_count=shazam.dominant_result.dominant_count,
        patterns_detected=shazam.patterns_detected,
        active_domains=memory_world.active_domains,
        memory_relevance=memory_world.memory_relevance,
        world_relevance=memory_world.world_relevance,
        domain_sigma_envelope=dse,
        domain_sigma_attached=bool(dse),
        readonly=True,
        advisory_only=True,
        context_signal_only=True,
        can_decide=False,
        can_emit_act=False,
        emits_act=False,
        emits_verdict=False,
        memory_write=False,
        graphiti_write=False,
        neo4j_write=False,
        kernel_mutation=False,
        x108_mutation=False,
        decision_authority="KX108_ONLY",
    )
