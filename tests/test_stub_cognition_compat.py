from jarvis.contracts import ContextSnapshot
from jarvis.providers.local_stub import StubCognition


def test_stub_respond_preserves_legacy_deterministic_fallback():
    stub = StubCognition()
    assert stub.respond("status", ContextSnapshot("test")) == "JARVIS_V0: status"


def test_stub_try_respond_remains_escalation_friendly():
    stub = StubCognition()
    assert stub.try_respond("an open-ended unknown request", ContextSnapshot("test")) is None
