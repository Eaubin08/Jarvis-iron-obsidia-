"""Structured Windows action backend.

OS-specific implementation is injected. No raw coordinates or visual control
belong in this backend.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import ActionRequest, ActionResult, Capability


class WindowsDriver(Protocol):
    def open_app(self, app: str) -> dict: ...
    def list_windows(self) -> dict: ...
    def focus_window(self, title: str) -> dict: ...


@dataclass
class NativeWindowsBackend:
    driver: WindowsDriver
    name: str = "windows.structured"
    priority: int = 10

    _supported = frozenset({"app.open", "window.list", "window.focus"})

    def can_execute(self, request: ActionRequest, capability: Capability) -> bool:
        return capability.backend_family == "windows" and request.capability in self._supported

    def execute(self, request: ActionRequest) -> ActionResult:
        try:
            if request.capability == "app.open":
                data = self.driver.open_app(self._required(request, "app"))
            elif request.capability == "window.list":
                data = self.driver.list_windows()
            elif request.capability == "window.focus":
                data = self.driver.focus_window(self._required(request, "title"))
            else:
                return ActionResult(False, "unsupported Windows capability", backend=self.name)
        except (KeyError, ValueError) as exc:
            return ActionResult(False, str(exc), backend=self.name)
        except Exception as exc:
            return ActionResult(
                False,
                f"Windows driver failure: {type(exc).__name__}: {exc}",
                backend=self.name,
            )
        return ActionResult(True, "Windows action completed", data=data, backend=self.name)

    @staticmethod
    def _required(request: ActionRequest, key: str) -> str:
        value = request.arguments.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"missing Windows argument: {key}")
        return value.strip()
