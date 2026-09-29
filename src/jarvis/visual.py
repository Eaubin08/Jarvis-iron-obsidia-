"""Visual operator fallback backend.

Visual control is intentionally a low-priority fallback behind structured
native, browser, and accessibility backends.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from .contracts import ActionRequest, ActionResult, Capability


class VisualOperatorDriver(Protocol):
    def snapshot(self) -> dict: ...
    def execute(self, request: ActionRequest, state: dict) -> dict: ...


@dataclass
class VisualOperatorBackend:
    driver: VisualOperatorDriver
    name: str = "visual.operator"
    priority: int = 40

    def can_execute(self, request: ActionRequest, capability: Capability) -> bool:
        return capability.backend_family == "visual" and request.capability.startswith("visual.")

    def execute(self, request: ActionRequest) -> ActionResult:
        started = datetime.now(timezone.utc)
        try:
            if self._uses_historical_handle(request):
                return ActionResult(
                    False,
                    "historical observation is not a live visual action handle",
                    backend=self.name,
                    started_at=started,
                    finished_at=datetime.now(timezone.utc),
                )
            state = self.driver.snapshot()
            if not isinstance(state, dict) or not state.get("observation_id"):
                return ActionResult(
                    False,
                    "visual state refresh failed",
                    backend=self.name,
                    started_at=started,
                    finished_at=datetime.now(timezone.utc),
                )
            data = self.driver.execute(request, state)
        except Exception as exc:
            return ActionResult(
                False,
                f"visual operator failure: {type(exc).__name__}: {exc}",
                backend=self.name,
                started_at=started,
                finished_at=datetime.now(timezone.utc),
            )

        evidence = (f"visual_state:{state['observation_id']}",)
        if data.get("evidence_ref"):
            evidence = evidence + (str(data["evidence_ref"]),)
        return ActionResult(
            True,
            "visual action completed",
            data=data,
            backend=self.name,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            evidence_refs=evidence,
        )

    @staticmethod
    def _uses_historical_handle(request: ActionRequest) -> bool:
        for key in ("historical_observation_id", "screenpipe_observation_id", "observation_id"):
            if key in request.arguments:
                return True
        return request.arguments.get("live_handle") is False
