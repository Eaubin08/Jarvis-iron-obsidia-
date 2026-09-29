import pytest

from jarvis.events import EventBus
from jarvis.providers.local_stub import StubCognition, StubMemory
from jarvis.runtime import TextRuntime


def test_text_runtime_emits_canonical_event_sequence():
    seen = []
    bus = EventBus()
    bus.subscribe_all(seen.append)
    memory = StubMemory()
    runtime = TextRuntime(StubCognition(), memory, bus, session_id="s1")

    assert runtime.handle("status") == "JARVIS_V0: status"
    assert [e.kind for e in seen] == [
        "voice.heard",
        "context.built",
        "cognition.started",
        "cognition.completed",
    ]
    assert all(e.session_id == "s1" for e in seen)
    assert seen[1].causation_id == seen[0].event_id
    assert seen[-1].causation_id == seen[0].event_id


def test_runtime_records_input_and_completed_reply_in_memory():
    memory = StubMemory()
    runtime = TextRuntime(StubCognition(), memory)
    runtime.handle("hello")
    assert [e.kind for e in memory.events] == ["voice.heard", "cognition.completed"]


def test_empty_text_fails_before_provider_call():
    runtime = TextRuntime(StubCognition(), StubMemory())
    with pytest.raises(ValueError):
        runtime.handle("   ")


class BrokenCognition:
    def respond(self, user_input, context):
        raise RuntimeError("provider offline")


def test_provider_failure_is_explicit_event_and_propagates():
    seen = []
    bus = EventBus()
    bus.subscribe_all(seen.append)
    runtime = TextRuntime(BrokenCognition(), StubMemory(), bus)

    with pytest.raises(RuntimeError, match="provider offline"):
        runtime.handle("status")

    assert seen[-1].kind == "cognition.failed"
    assert seen[-1].payload["error_type"] == "RuntimeError"
