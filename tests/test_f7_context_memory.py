from datetime import datetime, timezone
from pathlib import Path

from jarvis.context import ContextAssembler
from jarvis.contracts import PerceptualObservation
from jarvis.memory import (
    EpisodicMemory,
    JsonlMemoryBackend,
    PersonalMemory,
    ProjectMemory,
    WorkingMemory,
)
from jarvis.providers.local_stub import StubCognition, StubMemory
from jarvis.runtime import TextRuntime


class FakeTimeline:
    def __init__(self):
        self.queries = []

    def query(self, query, *, start=None, end=None, limit=20):
        self.queries.append((query, limit))
        return [
            PerceptualObservation(
                observation_id="obs-1",
                source="fake-screenpipe",
                kind="ocr",
                timestamp=datetime(2026, 9, 29, 20, 0, tzinfo=timezone.utc),
                text="Jarvis screen context",
                live_handle=True,
            )
        ][:limit]


def build_assembler(root: Path, timeline=None, **kwargs):
    backend = JsonlMemoryBackend(root)
    return ContextAssembler(
        working=WorkingMemory(),
        personal=PersonalMemory(backend),
        project=ProjectMemory(backend),
        episodic=EpisodicMemory(backend),
        perceptual_timeline=timeline,
        per_category_limit=2,
        **kwargs,
    )


def test_context_assembler_is_bounded_and_records_provenance(tmp_path):
    assembler = build_assembler(tmp_path, FakeTimeline(), max_items=2, max_chars=200)
    assembler.working.admit("Jarvis current turn", provenance="unit", memory_id="w1")
    assembler.project.admit("Jarvis project architecture", provenance="explicit", memory_id="p1")

    snapshot = assembler.build("s1", "t1", "Jarvis")

    assert snapshot.metadata["bounded"] is True
    assert snapshot.metadata["item_count"] == 2
    assert snapshot.metadata["request"] == "Jarvis"
    assert len(snapshot.summary) <= 200
    assert snapshot.provenance == (
        "memory:working:w1",
        "memory:project:p1",
    )


def test_context_assembler_keeps_all_categories_and_perceptual_provenance(tmp_path):
    timeline = FakeTimeline()
    assembler = build_assembler(tmp_path, timeline)
    assembler.working.admit("current user request mentions Jarvis", provenance="unit")
    assembler.personal.admit("user prefers concise Jarvis replies", provenance="explicit")
    assembler.project.admit("project branch is build/jarvis-v0", provenance="explicit")
    assembler.episodic.admit("Jarvis answered a status request", provenance="event:e1")

    snapshot = assembler.build(session_id="s1", request="Jarvis")

    assert "[working]" in snapshot.summary
    assert "[personal]" in snapshot.summary
    assert "[project]" in snapshot.summary
    assert "[episodic]" in snapshot.summary
    assert "[perceptual]" in snapshot.summary
    assert "perception:fake-screenpipe:obs-1" in snapshot.provenance
    assert timeline.queries == [("Jarvis", 2)]


def test_memory_categories_remain_isolated_and_do_not_cross_write(tmp_path):
    assembler = build_assembler(tmp_path)

    assembler.personal.admit("favorite editor is Code", provenance="explicit")
    assembler.project.admit("repo is Jarvis Iron", provenance="explicit")

    assert [r.text for r in assembler.personal.query("repo")] == []
    assert [r.text for r in assembler.project.query("repo")] == ["repo is Jarvis Iron"]
    assert assembler.working.query("favorite") == []
    assert assembler.episodic.query("favorite") == []


def test_memory_clear_is_category_local():
    working = WorkingMemory()
    personal = PersonalMemory()

    working.admit("working-only", memory_id="w")
    personal.admit("personal-only", memory_id="u")
    working.clear()

    assert working.query() == []
    assert [x.text for x in personal.query()] == ["personal-only"]


def test_restart_preserves_durable_memory_but_not_working_memory(tmp_path):
    first = build_assembler(tmp_path)
    first.working.admit("scratchpad only", provenance="session")
    first.personal.admit("user prefers local deterministic storage", provenance="explicit")
    first.project.admit("F7 is in progress", provenance="explicit")
    first.episodic.admit("completed a turn", provenance="event:e1")

    restarted = build_assembler(tmp_path)

    assert restarted.working.query("scratchpad") == []
    assert [r.text for r in restarted.personal.query("deterministic")] == [
        "user prefers local deterministic storage"
    ]
    assert [r.text for r in restarted.project.query("F7")] == ["F7 is in progress"]
    assert [r.text for r in restarted.episodic.query("completed")] == ["completed a turn"]


def test_text_runtime_can_use_context_assembler_without_breaking_memory_provider(tmp_path):
    assembler = build_assembler(tmp_path)
    assembler.project.admit("project context is assembled", provenance="explicit")
    legacy_memory = StubMemory()
    runtime = TextRuntime(
        StubCognition(),
        legacy_memory,
        session_id="s1",
        context_assembler=assembler,
    )

    assert runtime.handle("project context") == "Oui, je t'écoute."
    assert [event.kind for event in legacy_memory.events] == [
        "voice.heard",
        "cognition.completed",
    ]


def test_text_runtime_legacy_memory_provider_still_works():
    runtime = TextRuntime(StubCognition(), StubMemory())
    assert runtime.handle("hello") == "Oui, je t'écoute."
