"""Stable internal contracts for Jarvis.

External donor projects must connect through adapters implementing these
contracts. Jarvis core must not depend directly on donor-project internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class JarvisEvent:
    kind: str
    source: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextSnapshot:
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionRequest:
    capability: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)


class CognitionProvider(Protocol):
    def respond(self, user_input: str, context: ContextSnapshot) -> str: ...


class MemoryProvider(Protocol):
    def remember(self, event: JarvisEvent) -> None: ...
    def context(self) -> ContextSnapshot: ...


class PerceptionProvider(Protocol):
    def observe(self) -> list[JarvisEvent]: ...


class ActionProvider(Protocol):
    def execute(self, request: ActionRequest) -> ActionResult: ...


class VoiceProvider(Protocol):
    def listen(self) -> str: ...
    def speak(self, text: str) -> None: ...
