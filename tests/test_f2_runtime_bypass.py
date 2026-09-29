from jarvis.actions import ActionRouter
from jarvis.capabilities import LocalCapabilityRegistry
from jarvis.contracts import Capability
from jarvis.events import EventBus
from jarvis.fast_intent import FastIntentRouter
from jarvis.local_actions import LocalPermissionPolicy, SystemBackend
from jarvis.providers.local_stub import StubCognition, StubMemory
from jarvis.runtime import TextRuntime


class ForbiddenCognition:
    def respond(self, user_input, context):
        raise AssertionError("cognition must not be called for deterministic fast intent")


def build_actions():
    registry = LocalCapabilityRegistry()
    registry.register(Capability("system.status", "system"))
    return ActionRouter(registry, LocalPermissionPolicy(), [SystemBackend()])


def test_fast_status_bypasses_cognition_end_to_end():
    seen = []
    bus = EventBus()
    bus.subscribe_all(seen.append)
    runtime = TextRuntime(
        ForbiddenCognition(),
        StubMemory(),
        bus,
        fast_intent=FastIntentRouter(),
        actions=build_actions(),
    )
    assert runtime.handle("Jarvis status") == "JARVIS_IRON_STATUS: READY"
    kinds = [event.kind for event in seen]
    assert "action.requested" in kinds
    assert "action.completed" in kinds
    assert "cognition.started" not in kinds


def test_open_language_still_escalates_to_cognition():
    runtime = TextRuntime(
        StubCognition(),
        StubMemory(),
        fast_intent=FastIntentRouter(),
        actions=build_actions(),
    )
    text = "what is the status of my project?"
    assert runtime.handle(text) == f"JARVIS_V0: {text}"
