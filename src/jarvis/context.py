"""Bounded Jarvis-owned context assembly."""
from __future__ import annotations

from dataclasses import dataclass

from .contracts import ContextSnapshot, PerceptualTimeline
from .memory import EpisodicMemory, MemoryRecord, PersonalMemory, ProjectMemory, WorkingMemory


@dataclass(frozen=True)
class ContextAssembler:
    working: WorkingMemory
    personal: PersonalMemory
    project: ProjectMemory
    episodic: EpisodicMemory
    perceptual_timeline: PerceptualTimeline | None = None
    per_category_limit: int = 5
    max_summary_chars: int = 1200

    def build(
        self,
        *,
        session_id: str,
        task_id: str | None = None,
        request: str = "",
    ) -> ContextSnapshot:
        if self.per_category_limit <= 0:
            raise ValueError("per_category_limit must be positive")

        sections: list[str] = []
        provenance: list[str] = []
        metadata: dict[str, object] = {
            "session_id": session_id,
            "task_id": task_id,
            "bounded": True,
            "categories": ["working", "personal", "project", "episodic", "perceptual"],
        }

        for label, records in (
            ("working", self.working.query(request, limit=self.per_category_limit)),
            ("personal", self.personal.query(request, limit=self.per_category_limit)),
            ("project", self.project.query(request, limit=self.per_category_limit)),
            ("episodic", self.episodic.query(request, limit=self.per_category_limit)),
        ):
            self._append_records(sections, provenance, label, records)

        if self.perceptual_timeline is not None:
            observations = self.perceptual_timeline.query(request, limit=self.per_category_limit)
            for observation in observations:
                sections.append(f"perceptual: {observation.text}")
                provenance.append(f"perceptual:{observation.source}:{observation.observation_id}")

        summary = " | ".join(sections) if sections else "no context"
        if len(summary) > self.max_summary_chars:
            summary = summary[: self.max_summary_chars - 3] + "..."
            metadata["truncated"] = True

        return ContextSnapshot(summary=summary, metadata=metadata, provenance=tuple(provenance))

    @staticmethod
    def _append_records(
        sections: list[str],
        provenance: list[str],
        label: str,
        records: list[MemoryRecord],
    ) -> None:
        for record in records:
            sections.append(f"{label}: {record.text}")
            provenance.append(f"{label}:{record.record_id}:{record.provenance}")
