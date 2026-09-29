from jarvis.contracts import JarvisEvent
from jarvis.events import EventBus
from jarvis.hud import HUDClient, UserCommand


class Transport:
    def __init__(self):
        self.messages = []
        self.closed = False

    def send(self, message):
        self.messages.append(message)

    def close(self):
        self.closed = True


def test_hud_consumes_event_state_without_calling_donor_internals():
    bus = EventBus()
    transport = Transport()
    hud = HUDClient(transport, bus)
    hud.connect()

    bus.publish(JarvisEvent("voice.listening", "voice"))
    bus.publish(JarvisEvent("cognition.started", "runtime"))
    bus.publish(JarvisEvent("action.completed", "router", {"backend": "windows.structured"}))
    bus.publish(JarvisEvent("task.step.completed", "task_runtime", {"status": "waiting"}))
    bus.publish(JarvisEvent("system.status", "core", {"status": "ready"}))

    assert len(transport.messages) == 5
    assert transport.messages[-1]["state"]["listening"] is True
    assert transport.messages[-1]["state"]["thinking"] is True
    assert transport.messages[-1]["state"]["action_state"] == "completed"
    assert transport.messages[-1]["state"]["task_state"] == "waiting"
    assert transport.messages[-1]["state"]["system_status"] == "ready"


def test_hud_disconnect_does_not_stop_event_bus_or_core():
    bus = EventBus()
    transport = Transport()
    hud = HUDClient(transport, bus)
    core_seen = []
    bus.subscribe_all(core_seen.append)
    hud.connect()

    hud.disconnect()
    bus.publish(JarvisEvent("system.status", "core", {"status": "still-running"}))

    assert transport.closed is True
    assert transport.messages == []
    assert core_seen[-1].payload["status"] == "still-running"


def test_hud_emits_typed_user_command_without_direct_action_execution():
    hud = HUDClient(Transport(), EventBus())

    command = hud.command("action.request", {"capability": "app.open"})

    assert command == UserCommand(
        command_type="action.request",
        payload={"capability": "app.open"},
    )


def test_hud_command_rejects_empty_type():
    hud = HUDClient(Transport(), EventBus())
    try:
        hud.command("   ")
    except ValueError:
        pass
    else:
        raise AssertionError("expected empty HUD command to fail")
