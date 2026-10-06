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
    def get_window_hwnd(self, *, window_title: str) -> int: ...


class StableIdentityDriver(Protocol):
    """G2-0 bounded identity driver (jarvis.integrations.uia_identity.StableUIAController)."""
    def list_controls_uia(self, *, window_hwnd: int) -> dict: ...
    def read_value_by_identity(self, target: dict) -> dict: ...
    def set_text_by_identity(self, target: dict, exact_text: str) -> dict: ...
    def read_checked_by_identity(self, target: dict) -> dict: ...
    def set_checked_by_identity(self, target: dict, target_checked: bool) -> dict: ...


@dataclass
class StructuredUIBackend:
    driver: StructuredUIDriver
    name: str = "windows.uia"
    priority: int = 8
    # G2-0: stable-identity capabilities exist only when an identity driver is injected.
    # They are NOT registered in the live runtime: a governed caller (Obsidia) owns approval.
    identity_driver: StableIdentityDriver | None = None

    _supported = frozenset({
        "control.list",
        "control.click",
        "control.set_text",
        "control.read_text",
        "control.get_window_hwnd",
    })
    _identity_supported = frozenset({
        "control.list_uia",
        "control.read_value",
        "control.set_text_by_identity",
        "control.read_checked",
        "control.set_checked_by_identity",
    })

    def can_execute(self, request: ActionRequest, capability: Capability) -> bool:
        if capability.backend_family != "windows":
            return False
        if request.capability in self._identity_supported:
            return self.identity_driver is not None
        return request.capability in self._supported

    def execute(self, request: ActionRequest) -> ActionResult:
        if request.capability in self._identity_supported:
            return self._execute_identity(request)
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
            elif request.capability == "control.get_window_hwnd":
                hwnd = self.driver.get_window_hwnd(window_title=window_title)
                data = {"hwnd": hwnd}
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

    def _execute_identity(self, request: ActionRequest) -> ActionResult:
        if self.identity_driver is None:
            return ActionResult(False, "stable identity driver not configured", backend=self.name)
        try:
            if request.capability == "control.list_uia":
                hwnd = request.arguments.get("window_hwnd")
                if not isinstance(hwnd, int) or isinstance(hwnd, bool):
                    raise ValueError("window_hwnd must be an int")
                data = self.identity_driver.list_controls_uia(window_hwnd=hwnd)
            else:
                target = request.arguments.get("target_identity")
                if not isinstance(target, dict):
                    raise ValueError("target_identity must be a dict")
                if request.capability == "control.read_value":
                    data = self.identity_driver.read_value_by_identity(target)
                elif request.capability == "control.read_checked":
                    data = self.identity_driver.read_checked_by_identity(target)
                elif request.capability == "control.set_checked_by_identity":
                    checked = request.arguments.get("target_checked")
                    if not isinstance(checked, bool):
                        raise ValueError("target_checked must be a bool")
                    data = self.identity_driver.set_checked_by_identity(target, checked)
                else:
                    text = request.arguments.get("text")
                    if not isinstance(text, str):
                        raise ValueError("text must be a string")
                    data = self.identity_driver.set_text_by_identity(target, text)
        except (KeyError, ValueError) as exc:
            return ActionResult(False, str(exc), backend=self.name)
        except Exception as exc:
            return ActionResult(False, f"stable identity failure: {type(exc).__name__}: {exc}", backend=self.name)
        return ActionResult(True, "structured UI identity action completed", data=data, backend=self.name)

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
