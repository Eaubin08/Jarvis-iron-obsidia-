import pytest

from jarvis.device_bridge import DeviceBridgeRuntime
from jarvis.events import EventBus


class Transport:
    def __init__(self):
        self.messages = []
        self.closed = False

    def send(self, message):
        self.messages.append(message)

    def close(self):
        self.closed = True


def test_device_connect_requires_authenticated_session_boundary():
    transport = Transport()
    bridge = DeviceBridgeRuntime(token="secret")

    session = bridge.connect(device_id="phone", token="wrong", transport=transport)

    assert session.authenticated is False
    assert transport.messages == [{"type": "device.auth_failed", "device_id": "phone"}]
    assert transport.closed is True
    with pytest.raises(PermissionError):
        bridge.receive_command(session.session_id, "action.request")


def test_authenticated_device_command_becomes_canonical_request():
    transport = Transport()
    bridge = DeviceBridgeRuntime(token="secret")
    session = bridge.connect(device_id="phone", token="secret", transport=transport)

    command = bridge.receive_command(
        session.session_id,
        "action.request",
        {"capability": "app.open", "arguments": {"app": "notepad"}, "risk": "low"},
    )
    request = bridge.to_action_request(command)

    assert session.authenticated is True
    assert request.capability == "app.open"
    assert request.arguments == {"app": "notepad"}
    assert request.source == "device_bridge"
    assert request.session_id == session.session_id


def test_disconnect_does_not_corrupt_event_bus_or_other_state():
    seen = []
    bus = EventBus()
    bus.subscribe_all(seen.append)
    transport = Transport()
    bridge = DeviceBridgeRuntime(token="secret", events=bus)
    session = bridge.connect(device_id="phone", token="secret", transport=transport)

    bridge.disconnect(session.session_id, transport)
    bus.publish(type(seen[-1])("system.status", "core", {"status": "running"}))

    assert transport.closed is True
    assert seen[-2].kind == "device.disconnected"
    assert seen[-1].kind == "system.status"


def test_non_action_device_command_cannot_bypass_action_router():
    bridge = DeviceBridgeRuntime(token="secret")
    transport = Transport()
    session = bridge.connect(device_id="phone", token="secret", transport=transport)
    command = bridge.receive_command(session.session_id, "raw.tap", {"x": 1, "y": 2})

    with pytest.raises(ValueError):
        bridge.to_action_request(command)
