"""Structured Windows UI-control backend inspired by UFO² inspection/execution seams.

Jarvis owns the capability contract and routing. The injected driver may use
pywinauto/UIA internally but cannot bypass ActionRouter or permission policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import ActionRequest, ActionResult, Capability


class StructuredUIDriver(Protocol):
    def list_controls(self, *, window_title: str) -> dict: ...
    def click(self, *, window_title: str, control_name: str, control_type: str = "Button") -> dict: ...
    def set_text(self, *, window_title: str, control_name: str, value: str) -> dict: ...
    def read_text(self, *, window_title: str, control_name: str, control_type: str = "Text") -> dict: ...


@dataclass
class StructuredUIBackend:
    driver: StructuredUIDriver
    name: str = "windows.uia"
    priority: int = 8

    _supported = frozenset({
        "control.list",
        "control.click",
        "control.set_text",
        "control.read_text",
    })

    def can_execute(self, request: ActionRequest, capability: Capability) -> bool:
        return capability.backend_family == "windows" and request.capability in self._supported

    def execute(self, request: ActionRequest) -> ActionResult:
        try:
            window_title = self._required(request, "window_title")
            if request.capability == "control.list":
                data = self.driver.list_controls(window_title=window_title)
            elif request.capability == "control.click":
                data = self.driver.click(
                    window_title=window_title,
                    control_name=self._required(request, "control_name"),
                    control_type=self._optional(request, "control_type", "Button"),
                )
            elif request.capability == "control.set_text":
                data = self.driver.set_text(
                    window_title=window_title,
                    control_name=self._required(request, "control_name"),
                    value=self._required(request, "value"),
                )
            elif request.capability == "control.read_text":
                data = self.driver.read_text(
                    window_title=window_title,
                    control_name=self._required(request, "control_name"),
                    control_type=self._optional(request, "control_type", "Text"),
                )
            else:
                return ActionResult(False, "unsupported structured UI capability", backend=self.name)
        except (KeyError, ValueError) as exc:
            return ActionResult(False, str(exc), backend=self.name)
        except Exception as exc:
            return ActionResult(
                False,
                f"structured UI driver failure: {type(exc).__name__}: {exc}",
                backend=self.name,
            )

        return ActionResult(True, "structured UI action completed", data=data, backend=self.name)

    @staticmethod
    def _required(request: ActionRequest, key: str) -> str:
        value = request.arguments.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"missing structured UI argument: {key}")
        return value.strip()

    @staticmethod
    def _optional(request: ActionRequest, key: str, default: str) -> str:
        value = request.arguments.get(key, default)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"invalid structured UI argument: {key}")
        return value.strip()
