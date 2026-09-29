import json

import pytest

from jarvis.contracts import ContextSnapshot
from jarvis.transports.personal_jarvis_ws import (
    DonorProtocolError,
    PersonalJarvisWebSocketTransport,
)


class FakeSocket:
    def __init__(self, frames):
        self.frames = iter(frames)
        self.sent = []
        self.closed = False

    def recv(self):
        return next(self.frames)

    def send(self, value):
        self.sent.append(value)

    def close(self):
        self.closed = True


def test_text_roundtrip_uses_verified_upstream_wire_contract():
    socket = FakeSocket([
        json.dumps({"type": "welcome"}),
        json.dumps({
            "type": "event",
            "event_name": "ResponseGenerated",
            "payload": {"text": "Online."},
        }),
    ])
    transport = PersonalJarvisWebSocketTransport(
        connect=lambda url, timeout: socket
    )

    reply = transport.chat("status", ContextSnapshot(summary="J1"))

    assert reply == "Online."
    sent = json.loads(socket.sent[0])
    assert sent["type"] == "message"
    assert sent["kind"] == "text"
    assert sent["content"] == "status"
    assert sent["metadata"]["thread_id"] == "jarvis-iron"
    assert socket.closed is True


def test_brain_error_fails_closed():
    socket = FakeSocket([
        json.dumps({"type": "welcome"}),
        json.dumps({
            "type": "event",
            "event_name": "ErrorOccurred",
            "payload": {"layer": "brain", "message": "offline"},
        }),
    ])
    transport = PersonalJarvisWebSocketTransport(
        connect=lambda url, timeout: socket
    )

    with pytest.raises(DonorProtocolError, match="offline"):
        transport.chat("status", ContextSnapshot(summary="J1"))
