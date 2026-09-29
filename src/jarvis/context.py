"""Bounded F7 context assembly across isolated memory categories."""
from __future__ import annotations

from dataclasses import dataclass

from .contracts import ContextSnapshot, PerceptualTimeline
from .memory import MemoryStore


@dataclass
class ContextAssembler:
    working: MemoryStore
    personal: MemoryStore
    project: MemoryStore
    episodic: MemoryStore
    perceptual: PerceptualTimeline | None = None
    max_items: int = 12
    max_chars: int = 4000

    def build(
        self,
        session_id: str,
        task_id: str | None,
        request: str,
    ) -> ContextSnapshot:
        if self.max_items <= 0:
            raise ValueError("max_items must be positive")
        if self.max_chars <= 0:
            raise ValueError("max_chars must be positive")

        candidates: list[tuple[str, str, str]] = []

        for store in (self.working, self.personal, self.project, self.episodic):
            for item in store.query(request, limit=self.max_items):
                candidates.append(
                    (
                        f"memory:{item.category}:{item.memory_id}",
                        item.category,
                        item.text,
                    )
                )

        if self.perceptual is not None:
            for obs in self.perceptual.query(request, limit=self.max_items):
                candidates.append(
                    (
                        f"perception:{obs.source}:{obs.observation_id}",
                        "perceptual",
                        obs.text,
                    )
                )

        selected: list[tuple[str, str, str]] = []
        used_chars = 0
        for provenance, category, text in candidates:
            if len(selected) >= self.max_items:
                break
            remaining = self.max_chars - used_chars
            if remaining <= 0:
                break
            clipped = text[:remaining]
            if not clipped:
                continue
            selected.append((provenance, category, clipped))
            used_chars += len(clipped)

        summary = "\n".join(
            f"[{category}] {text}" for _, category, text in selected
        )

        return ContextSnapshot(
            summary=summary,
            metadata={
                "session_id": session_id,
                "task_id": task_id,
                "request": request,
                "item_count": len(selected),
                "char_count": used_chars,
                "bounded": True,
            },
            provenance=tuple(provenance for provenance, _, _ in selected),
        )
