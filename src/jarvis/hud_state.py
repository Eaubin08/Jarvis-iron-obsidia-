"""Jarjar HUD state model.

UI code consumes this model; runtime/backends do not depend on a GUI toolkit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import Lock


class HUDState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass(frozen=True)
class HUDMessage:
    speaker: str
    text: str


@dataclass
class HUDModel:
    state: HUDState = HUDState.IDLE
    voice_enabled: bool = True
    session_open: bool = False
    messages: list[HUDMessage] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def set_state(self, state: HUDState) -> None:
        with self._lock:
            self.state = state

    def set_voice_enabled(self, enabled: bool) -> None:
        with self._lock:
            self.voice_enabled = bool(enabled)
            if not self.voice_enabled:
                self.session_open = False

    def set_session_open(self, opened: bool) -> None:
        with self._lock:
            self.session_open = bool(opened)

    def append(self, speaker: str, text: str) -> None:
        clean = text.strip()
        if not clean:
            return
        with self._lock:
            self.messages.append(HUDMessage(speaker=speaker, text=clean))

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "state": self.state.value,
                "voice_enabled": self.voice_enabled,
                "session_open": self.session_open,
                "messages": [
                    {"speaker": item.speaker, "text": item.text}
                    for item in self.messages
                ],
            }
