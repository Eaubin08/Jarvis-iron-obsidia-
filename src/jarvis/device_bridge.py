"""Minimal Jarvis-owned mobile/device bridge protocol."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from .contracts import ActionRequest, JarvisEvent, RiskClass
from .events import EventBus


class DeviceTransport(Protocol):
    def send(self, message: dict) -> None: ...
    def close(self) -> None: ...


@dataclass(frozen=True)
class DeviceSession:
    session_id: str
    device_id: str
    authenticated: bool
    created_at: datetime


@dataclass(frozen=True)
class DeviceCommand:
    command_type: str
    payload: dict
    session_id: str
    device_id: str


class DeviceBridgeRuntime:
    def __init__(self, *, token: str, events: EventBus | None = None) -> None:
        if not token:
            raise ValueError("token must not be empty")
        self._token = token
        self.events = events or EventBus()
        self._sessions: dict[str, DeviceSession] = {}

    def connect(self, *, device_id: str, token: str, transport: DeviceTransport) -> DeviceSession:
        authenticated = token == self._token
        session = DeviceSession(
            session_id=f"device_{uuid4().hex}",
            device_id=device_id,
            authenticated=authenticated,
            created_at=datetime.now(timezone.utc),
        )
        if authenticated:
            self._sessions[session.session_id] = session
            transport.send({"type": "device.connected", "session_id": session.session_id})
        else:
            transport.send({"type": "device.auth_failed", "device_id": device_id})
            transport.close()
        self.events.publish(
            JarvisEvent(
                kind="device.connected" if authenticated else "device.auth_failed",
                source="device_bridge",
                payload={"device_id": device_id, "authenticated": authenticated},
                session_id=session.session_id,
            )
        )
        return session

    def disconnect(self, session_id: str, transport: DeviceTransport) -> None:
        self._sessions.pop(session_id, None)
        transport.close()
        self.events.publish(
            JarvisEvent(
                kind="device.disconnected",
                source="device_bridge",
                payload={},
                session_id=session_id,
            )
        )

    def receive_command(self, session_id: str, command_type: str, payload: dict | None = None) -> DeviceCommand:
        session = self._require_session(session_id)
        command_type = command_type.strip()
        if not command_type:
            raise ValueError("command_type must not be empty")
        command = DeviceCommand(
            command_type=command_type,
            payload=dict(payload or {}),
            session_id=session.session_id,
            device_id=session.device_id,
        )
        self.events.publish(
            JarvisEvent(
                kind="device.command",
                source="device_bridge",
                payload={"command_type": command.command_type, **command.payload},
                session_id=session.session_id,
            )
        )
        return command

    def to_action_request(self, command: DeviceCommand) -> ActionRequest:
        capability = command.payload.get("capability")
        if command.command_type != "action.request" or not isinstance(capability, str):
            raise ValueError("device command is not a canonical action request")
        return ActionRequest(
            capability=capability,
            arguments=dict(command.payload.get("arguments", {})),
            source="device_bridge",
            session_id=command.session_id,
            risk=RiskClass(command.payload.get("risk", RiskClass.LOW.value)),
        )

    def _require_session(self, session_id: str) -> DeviceSession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise PermissionError("device session is not authenticated") from exc
