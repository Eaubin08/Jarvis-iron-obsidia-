"""Canonical Jarvis Iron V0 contracts.

Donor-specific objects stop at adapters. Core/runtime code speaks only these
types and protocols.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol
from uuid import uuid4


def _id() -> str:
    return uuid4().hex


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RiskClass(str, Enum):
    READ_ONLY = "read_only"
    LOW = "low"
    SENSITIVE = "sensitive"
    DESTRUCTIVE = "destructive"
    EXTERNAL_IMPACT = "external_impact"


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass(frozen=True)
class JarvisEvent:
    kind: str
    source: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=_id)
    timestamp: datetime = field(default_factory=_utc_now)
    session_id: str = "default"
    task_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None


@dataclass(frozen=True)
class ContextSnapshot:
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActionRequest:
    capability: str
    arguments: dict[str, Any] = field(default_factory=dict)
    target: str | None = None
    source: str = "jarvis"
    session_id: str = "default"
    task_id: str | None = None
    risk: RiskClass = RiskClass.LOW
    idempotency_key: str | None = None


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    backend: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Capability:
    name: str
    backend_family: str
    description: str = ""


class CognitionProvider(Protocol):
    def respond(self, user_input: str, context: ContextSnapshot) -> str: ...


class MemoryProvider(Protocol):
    def remember(self, event: JarvisEvent) -> None: ...
    def context(self) -> ContextSnapshot: ...


class PerceptionProvider(Protocol):
    def observe(self) -> list[JarvisEvent]: ...


class CapabilityRegistry(Protocol):
    def resolve(self, request: ActionRequest) -> Capability | None: ...


class PermissionPolicy(Protocol):
    def evaluate(
        self, request: ActionRequest, context: ContextSnapshot
    ) -> PermissionDecision: ...


class ActionBackend(Protocol):
    name: str
    priority: int

    def can_execute(self, request: ActionRequest, capability: Capability) -> bool: ...
    def execute(self, request: ActionRequest) -> ActionResult: ...


class MicrophoneProvider(Protocol):
    def capture(self, duration_seconds: float) -> bytes: ...


class WakeWordProvider(Protocol):
    def detect(self, audio: bytes) -> bool: ...


class SpeechToTextProvider(Protocol):
    def transcribe(self, audio: bytes) -> str: ...


class SpeechHandle(Protocol):
    def cancel(self) -> None: ...


class TextToSpeechProvider(Protocol):
    def speak(self, text: str) -> SpeechHandle: ...


class VoiceProvider(Protocol):
    """Compatibility seam for early donors; split providers are canonical."""

    def listen(self) -> str: ...
    def speak(self, text: str) -> None: ...
