from datetime import datetime, timezone

from jarvis.context import ContextAssembler
from jarvis.contracts import PerceptualObservation
from jarvis.memory import EpisodicMemory, PersonalMemory, ProjectMemory, WorkingMemory


class FakeTimeline:
    def query(self, query, *, start=None, end=None, limit=20):
        return [
            PerceptualObservation(
                observation_id="obs-1",
                source="fake-screenpipe",
                kind="ocr",
                timestamp=datetime(2026, 9, 29, 20, 0, tzinfo=timezone.utc),
                text="Jarvis screen context",
                live_handle=False,
            )
        ][:limit]


def test_context_assembler_is_bounded_and_records_provenance():
    working = WorkingMemory()
    personal = PersonalMemory()
    project = ProjectMemory()
    episodic = EpisodicMemory()

    working.admit("Jarvis current turn", memory_id="w1")
    project.admit("Jarvis project architecture", memory_id="p1")

    assembler = ContextAssembler(
        working,
        personal,
        project,
        episodic,
        perceptual=FakeTimeline(),
        max_items=2,
        max_chars=200,
    )

    snapshot = assembler.build("s1", "t1", "Jarvis")

    assert snapshot.metadata["bounded"] is True
    assert snapshot.metadata["item_count"] == 2
    assert len(snapshot.summary) <= 200 + len("[working] ") + len("[project] ")
    assert snapshot.provenance == (
        "memory:working:w1",
        "memory:project:p1",
    )


def test_memory_categories_remain_isolated():
    working = WorkingMemory()
    personal = PersonalMemory()
    project = ProjectMemory()
    episodic = EpisodicMemory()

    working.admit("working-only", memory_id="w")
    personal.admit("personal-only", memory_id="u")
    project.admit("project-only", memory_id="p")
    episodic.admit("episodic-only", memory_id="e")

    assert [x.text for x in working.query()] == ["working-only"]
    assert [x.text for x in personal.query()] == ["personal-only"]
    assert [x.text for x in project.query()] == ["project-only"]
    assert [x.text for x in episodic.query()] == ["episodic-only"]

    working.clear()
    assert working.query() == []
    assert [x.text for x in personal.query()] == ["personal-only"]
    assert [x.text for x in project.query()] == ["project-only"]
    assert [x.text for x in episodic.query()] == ["episodic-only"]


def test_context_includes_perceptual_provenance_when_capacity_allows():
    assembler = ContextAssembler(
        WorkingMemory(),
        PersonalMemory(),
        ProjectMemory(),
        EpisodicMemory(),
        perceptual=FakeTimeline(),
        max_items=4,
    )

    snapshot = assembler.build("s1", None, "Jarvis")

    assert "perception:fake-screenpipe:obs-1" in snapshot.provenance
    assert "[perceptual] Jarvis screen context" in snapshot.summary
