"""Jarvis-owned HUD event client boundary."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .contracts import JarvisEvent
from .events import EventBus


class HUDTransport(Protocol):
    def send(self, message: dict) -> None: ...
    def close(self) -> None: ...


@dataclass(frozen=True)
class UserCommand:
    command_type: str
    payload: dict
    source: str = "hud"


@dataclass
class HUDState:
    listening: bool = False
    thinking: bool = False
    speaking: bool = False
    action_state: str = "idle"
    task_state: str = "idle"
    system_status: str = "unknown"


@dataclass
class HUDClient:
    transport: HUDTransport
    events: EventBus
    state: HUDState = field(default_factory=HUDState)
    connected: bool = False

    def connect(self) -> None:
        if self.connected:
            return
        self.connected = True
        self.events.subscribe_all(self.consume)

    def disconnect(self) -> None:
        self.connected = False
        self.transport.close()

    def consume(self, event: JarvisEvent) -> None:
        if not self.connected:
            return
        self._update_state(event)
        self.transport.send(
            {
                "event_id": event.event_id,
                "event_type": event.kind,
                "session_id": event.session_id,
                "task_id": event.task_id,
                "payload": event.payload,
                "state": self.state.__dict__.copy(),
            }
        )

    def command(self, command_type: str, payload: dict | None = None) -> UserCommand:
        command_type = command_type.strip()
        if not command_type:
            raise ValueError("command_type must not be empty")
        return UserCommand(command_type=command_type, payload=dict(payload or {}))

    def _update_state(self, event: JarvisEvent) -> None:
        if event.kind == "voice.listening":
            self.state.listening = True
        elif event.kind in {"voice.heard", "voice.idle"}:
            self.state.listening = False
        elif event.kind == "cognition.started":
            self.state.thinking = True
        elif event.kind in {"cognition.completed", "cognition.failed"}:
            self.state.thinking = False
        elif event.kind == "voice.speaking":
            self.state.speaking = True
        elif event.kind in {"voice.speech_finished", "voice.interrupted"}:
            self.state.speaking = False
        elif event.kind == "action.requested":
            self.state.action_state = "requested"
        elif event.kind == "action.completed":
            self.state.action_state = "completed"
        elif event.kind == "action.failed":
            self.state.action_state = "failed"
        elif event.kind.startswith("task."):
            self.state.task_state = str(event.payload.get("status", event.kind))
        elif event.kind == "system.status":
            self.state.system_status = str(event.payload.get("status", "unknown"))
