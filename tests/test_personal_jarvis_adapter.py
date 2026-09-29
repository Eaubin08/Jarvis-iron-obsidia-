from jarvis.contracts import ContextSnapshot
from jarvis.providers.personal_jarvis import PersonalJarvisCognition


class FakeTransport:
    def __init__(self):
        self.calls = []

    def chat(self, text, context):
        self.calls.append((text, context))
        return "donor-response"


def test_adapter_maps_jarvis_contract_to_transport():
    transport = FakeTransport()
    adapter = PersonalJarvisCognition(transport)
    context = ContextSnapshot(summary="working on J1")

    assert adapter.respond("hello", context) == "donor-response"
    assert transport.calls == [("hello", context)]


def test_adapter_rejects_empty_turn_before_donor_call():
    transport = FakeTransport()
    adapter = PersonalJarvisCognition(transport)

    try:
        adapter.respond("   ", ContextSnapshot(summary=""))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")

    assert transport.calls == []
