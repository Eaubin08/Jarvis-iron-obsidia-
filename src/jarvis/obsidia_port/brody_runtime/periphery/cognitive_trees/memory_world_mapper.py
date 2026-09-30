"""
Memory-World Mapper — maps cognitive tree activation to memory-world context.
Memory-world context != decision. Output is ContextPacket-compatible signal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .shazam_cognitif import ShazamCognitifResult


@dataclass
class MemoryWorldContext:
    source_vector_id: str
    active_domains: list[str]
    patterns: list[str]
    memory_relevance: float
    world_relevance: float
    context_signal_only: bool = True
    can_decide: bool = False
    can_emit_act: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_vector_id": self.source_vector_id,
            "active_domains": self.active_domains,
            "patterns": self.patterns,
            "memory_relevance": self.memory_relevance,
            "world_relevance": self.world_relevance,
            "context_signal_only": self.context_signal_only,
            "can_decide": self.can_decide,
            "can_emit_act": self.can_emit_act,
        }


_MEMORY_DOMAINS = {"memory", "context", "epistemics"}
_WORLD_DOMAINS = {"governance", "ethics", "planning", "social"}


def map_memory_world(shazam: ShazamCognitifResult) -> MemoryWorldContext:
    from .tree_registry import get_all_trees
    trees = get_all_trees()
    id_to_domain = {t.id: t.domain for t in trees}

    # Use canonical TREE_IDs (1-based) for domain lookup.
    # dominant_tree_ids is the correct source; fall back to dim+1 for callers
    # that construct DominantTreeResult without populating dominant_tree_ids
    # (e.g. periphery_ops /cognitive/memory-world-map endpoint).
    tree_ids = shazam.dominant_result.dominant_tree_ids
    if not tree_ids:
        tree_ids = [dim + 1 for dim in shazam.dominant_result.dominant_ids]

    active_domains = []
    for tree_id in tree_ids:
        domain = id_to_domain.get(tree_id, "unknown")
        if domain not in active_domains:
            active_domains.append(domain)

    memory_hits = sum(1 for d in active_domains if d in _MEMORY_DOMAINS)
    world_hits = sum(1 for d in active_domains if d in _WORLD_DOMAINS)
    total = max(len(active_domains), 1)

    return MemoryWorldContext(
        source_vector_id=shazam.vector_id,
        active_domains=active_domains,
        patterns=shazam.patterns_detected,
        memory_relevance=round(memory_hits / total, 3),
        world_relevance=round(world_hits / total, 3),
        context_signal_only=True,
        can_decide=False,
        can_emit_act=False,
    )
