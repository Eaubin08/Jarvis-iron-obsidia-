"""Bounded Jarvis-owned context assembly across isolated memory categories."""
from __future__ import annotations

from dataclasses import dataclass

from .contracts import ContextSnapshot, PerceptualTimeline
from .memory import MemoryRecord, MemoryStore


@dataclass(init=False)
class ContextAssembler:
    working: MemoryStore
    personal: MemoryStore
    project: MemoryStore
    episodic: MemoryStore
    perceptual_timeline: PerceptualTimeline | None
    per_category_limit: int
    max_summary_chars: int
    max_items: int

    def __init__(
        self,
        working: MemoryStore,
        personal: MemoryStore,
        project: MemoryStore,
        episodic: MemoryStore,
        perceptual_timeline: PerceptualTimeline | None = None,
        per_category_limit: int = 5,
        max_summary_chars: int = 1200,
        *,
        perceptual: PerceptualTimeline | None = None,
        max_items: int | None = None,
        max_chars: int | None = None,
    ) -> None:
        self.working = working
        self.personal = personal
        self.project = project
        self.episodic = episodic
        self.perceptual_timeline = perceptual_timeline if perceptual_timeline is not None else perceptual
        self.per_category_limit = per_category_limit
        self.max_summary_chars = max_chars if max_chars is not None else max_summary_chars
        self.max_items = max_items if max_items is not None else per_category_limit * 5

    def build(
        self,
        session_id: str,
        task_id: str | None = None,
        request: str = "",
    ) -> ContextSnapshot:
        if self.per_category_limit <= 0:
            raise ValueError("per_category_limit must be positive")
        if self.max_items <= 0:
            raise ValueError("max_items must be positive")
        if self.max_summary_chars <= 0:
            raise ValueError("max_summary_chars must be positive")

        candidates: list[tuple[str, str, str]] = []
        for label, records in (
            ("working", self.working.query(request, limit=self.per_category_limit)),
            ("personal", self.personal.query(request, limit=self.per_category_limit)),
            ("project", self.project.query(request, limit=self.per_category_limit)),
            ("episodic", self.episodic.query(request, limit=self.per_category_limit)),
        ):
            self._append_records(candidates, label, records)

        if self.perceptual_timeline is not None:
            observations = self.perceptual_timeline.query(request, limit=self.per_category_limit)
            for observation in observations:
                candidates.append(
                    (
                        f"perception:{observation.source}:{observation.observation_id}",
                        "perceptual",
                        observation.text,
                    )
                )

        sections: list[str] = []
        provenance: list[str] = []
        used_chars = 0
        for item_provenance, category, text in candidates:
            if len(sections) >= self.max_items:
                break
            section_prefix = f"[{category}] "
            remaining = self.max_summary_chars - used_chars - len(section_prefix)
            if remaining <= 0:
                break
            clipped = text[:remaining]
            if not clipped:
                continue
            sections.append(f"{section_prefix}{clipped}")
            provenance.append(item_provenance)
            used_chars += len(section_prefix) + len(clipped)

        return ContextSnapshot(
            summary="\n".join(sections) if sections else "no context",
            metadata={
                "session_id": session_id,
                "task_id": task_id,
                "request": request,
                "item_count": len(sections),
                "char_count": used_chars,
                "bounded": True,
                "categories": ["working", "personal", "project", "episodic", "perceptual"],
            },
            provenance=tuple(provenance),
        )

    @staticmethod
    def _append_records(
        candidates: list[tuple[str, str, str]],
        label: str,
        records: list[MemoryRecord],
    ) -> None:
        for record in records:
            candidates.append((f"memory:{label}:{record.record_id}", label, record.text))
