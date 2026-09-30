from jarvis.contracts import ContextSnapshot
from jarvis.providers.local_stub import DeterministicStubCognition, StubCognition


def test_deterministic_stub_preserves_plumbing_marker():
    stub = DeterministicStubCognition()
    assert stub.respond("status", ContextSnapshot("test")) == "JARVIS_V0: status"


def test_presence_stub_unknown_input_is_non_echo_ack():
    stub = StubCognition()
    assert stub.respond("an open-ended unknown request", ContextSnapshot("test")) == "Oui, je t'écoute."


def test_presence_stub_try_respond_remains_escalation_friendly():
    stub = StubCognition()
    assert stub.try_respond("an open-ended unknown request", ContextSnapshot("test")) is None
