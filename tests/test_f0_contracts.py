from jarvis.actions import ActionRouter
from jarvis.contracts import (
    ActionRequest,
    ActionResult,
    Capability,
    ContextSnapshot,
    JarvisEvent,
    PermissionDecision,
    RiskClass,
)
from jarvis.events import EventBus


class Registry:
    def resolve(self, request):
        if request.capability == "app.open":
            return Capability("app.open", "native")
        return None


class Allow:
    def evaluate(self, request, context):
        return PermissionDecision.ALLOW


class Deny:
    def evaluate(self, request, context):
        return PermissionDecision.DENY


class Backend:
    def __init__(self, name, priority, compatible=True):
        self.name = name
        self.priority = priority
        self.compatible = compatible
        self.calls = []

    def can_execute(self, request, capability):
        return self.compatible

    def execute(self, request):
        self.calls.append(request)
        return ActionResult(True, self.name)


def test_event_has_identity_time_and_session():
    event = JarvisEvent(kind="session.started", source="test")
    assert event.event_id
    assert event.timestamp.tzinfo is not None
    assert event.session_id == "default"


def test_context_carries_provenance():
    context = ContextSnapshot("bounded", provenance=("event:a", "memory:b"))
    assert context.provenance == ("event:a", "memory:b")


def test_action_request_carries_risk_and_idempotency():
    request = ActionRequest(
        "app.open",
        target="notepad",
        risk=RiskClass.LOW,
        idempotency_key="open:notepad",
    )
    assert request.target == "notepad"
    assert request.idempotency_key == "open:notepad"


def test_router_prefers_more_structured_backend_by_priority():
    visual = Backend("visual", 40)
    native = Backend("native", 10)
    router = ActionRouter(Registry(), Allow(), [visual, native])
    result = router.execute(ActionRequest("app.open"), ContextSnapshot(""))
    assert result.backend == "native"
    assert len(native.calls) == 1
    assert visual.calls == []


def test_permission_denial_prevents_backend_execution():
    backend = Backend("native", 10)
    router = ActionRouter(Registry(), Deny(), [backend])
    result = router.execute(ActionRequest("app.open"), ContextSnapshot(""))
    assert not result.ok
    assert backend.calls == []


def test_event_bus_routes_without_ui_or_donor_dependency():
    seen = []
    bus = EventBus()
    bus.subscribe("voice.heard", seen.append)
    bus.publish(JarvisEvent("voice.heard", "test", {"text": "hello"}))
    assert seen[0].payload["text"] == "hello"
