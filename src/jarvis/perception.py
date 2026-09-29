"""Camera and gesture perception contracts for Jarvis V0."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from .contracts import ActionRequest, RiskClass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class CameraObservation:
    observation_id: str
    provider: str
    timestamp: datetime
    enabled: bool
    text: str = ""
    metadata: dict = field(default_factory=dict)


class CameraProvider(Protocol):
    name: str

    def snapshot(self) -> dict: ...


@dataclass(frozen=True)
class Gesture:
    gesture_id: str
    name: str
    confidence: float
    source_observation_id: str
    timestamp: datetime = field(default_factory=_utc_now)


@dataclass
class CameraRuntime:
    provider: CameraProvider
    enabled: bool = False
    permission_granted: bool = False

    def enable(self, *, permission_granted: bool) -> None:
        self.permission_granted = permission_granted
        self.enabled = permission_granted

    def disable(self) -> None:
        self.enabled = False

    def snapshot(self) -> CameraObservation:
        if not self.enabled or not self.permission_granted:
            return CameraObservation(
                observation_id=f"camera_{uuid4().hex}",
                provider=getattr(self.provider, "name", "unknown"),
                timestamp=_utc_now(),
                enabled=False,
                text="camera unavailable",
                metadata={"permission": "denied" if not self.permission_granted else "disabled"},
            )
        raw = self.provider.snapshot()
        return CameraObservation(
            observation_id=str(raw.get("observation_id") or f"camera_{uuid4().hex}"),
            provider=getattr(self.provider, "name", "unknown"),
            timestamp=raw.get("timestamp") or _utc_now(),
            enabled=True,
            text=str(raw.get("text", "")),
            metadata=dict(raw.get("metadata", {})),
        )


class GestureInterpreter:
    def interpret(self, observation: CameraObservation) -> Gesture | None:
        name = observation.metadata.get("gesture")
        confidence = float(observation.metadata.get("confidence", 0.0))
        if not observation.enabled or not name or confidence < 0.75:
            return None
        return Gesture(
            gesture_id=f"gesture_{uuid4().hex}",
            name=str(name),
            confidence=confidence,
            source_observation_id=observation.observation_id,
        )

    def to_action_request(self, gesture: Gesture, *, session_id: str = "default") -> ActionRequest:
        return ActionRequest(
            capability=f"gesture.{gesture.name}",
            arguments={
                "gesture_id": gesture.gesture_id,
                "source_observation_id": gesture.source_observation_id,
                "confidence": gesture.confidence,
            },
            source="gesture_interpreter",
            session_id=session_id,
            risk=RiskClass.LOW,
        )
