"""Structured browser backend.

Playwright is isolated behind an injectable driver so Jarvis contracts and unit
tests do not depend on Playwright objects.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import ActionRequest, ActionResult, Capability


class BrowserDriver(Protocol):
    def navigate(self, url: str) -> dict: ...
    def read(self, selector: str | None = None) -> dict: ...
    def inspect_element(self, selector: str) -> dict: ...
    def activate_link_by_identity(self, identity: dict) -> dict: ...
    def inspect_disclosure(self, selector: str) -> dict: ...
    def set_disclosure_by_identity(self, identity: dict, target_expanded: bool) -> dict: ...
    def inspect_checkbox(self, selector: str) -> dict: ...
    def set_checked_by_identity(self, identity: dict, target_checked: bool) -> dict: ...
    def inspect_radio(self, selector: str) -> dict: ...
    def select_radio_by_identity(self, identity: dict) -> dict: ...
    def inspect_select(self, selector: str) -> dict: ...
    def select_option_by_identity(self, identity: dict, option_identity: dict) -> dict: ...
    def inspect_field(self, selector: str) -> dict: ...
    def set_field_value_by_identity(self, identity: dict, target_value: str) -> dict: ...
    def inspect_form_submission(self, form_selector: str, submitter_selector: str) -> dict: ...
    def submit_get_navigation_by_identity(self, identity: dict) -> dict: ...
    def click(self, selector: str) -> dict: ...
    def fill(self, selector: str, value: str) -> dict: ...


@dataclass
class BrowserBackend:
    driver: BrowserDriver
    name: str = "browser.structured"
    priority: int = 20

    _supported = frozenset({
        "browser.navigate",
        "browser.read",
        "browser.inspect_element",
        "browser.activate_link",
        "browser.inspect_disclosure",
        "browser.set_disclosure",
        "browser.inspect_checkbox",
        "browser.set_checked",
        "browser.inspect_radio",
        "browser.select_radio",
        "browser.inspect_select",
        "browser.select_option",
        "browser.inspect_field",
        "browser.set_field_value",
        "browser.inspect_form_submission",
        "browser.submit_get_navigation",
        "browser.click",
    })

    def can_execute(self, request: ActionRequest, capability: Capability) -> bool:
        return capability.backend_family == "browser" and request.capability in self._supported

    def execute(self, request: ActionRequest) -> ActionResult:
        try:
            if request.capability == "browser.navigate":
                url = self._required(request, "url")
                data = self.driver.navigate(url)
            elif request.capability == "browser.read":
                data = self.driver.read(request.arguments.get("selector"))
            elif request.capability == "browser.inspect_element":
                selector = self._required(request, "selector")
                data = self.driver.inspect_element(selector)
            elif request.capability == "browser.activate_link":
                data = self.driver.activate_link_by_identity(dict(request.arguments))
            elif request.capability == "browser.inspect_disclosure":
                selector = self._required(request, "selector")
                data = self.driver.inspect_disclosure(selector)
            elif request.capability == "browser.set_disclosure":
                target_expanded = request.arguments.get("target_expanded")
                if not isinstance(target_expanded, bool):
                    raise ValueError("target_expanded must be bool")
                data = self.driver.set_disclosure_by_identity(dict(request.arguments), target_expanded)
            elif request.capability == "browser.inspect_checkbox":
                selector = self._required(request, "selector")
                data = self.driver.inspect_checkbox(selector)
            elif request.capability == "browser.set_checked":
                target_checked = request.arguments.get("target_checked")
                if not isinstance(target_checked, bool):
                    raise ValueError("target_checked must be bool")
                data = self.driver.set_checked_by_identity(dict(request.arguments), target_checked)
            elif request.capability == "browser.inspect_radio":
                selector = self._required(request, "selector")
                data = self.driver.inspect_radio(selector)
            elif request.capability == "browser.select_radio":
                data = self.driver.select_radio_by_identity(dict(request.arguments))
            elif request.capability == "browser.inspect_select":
                selector = self._required(request, "selector")
                data = self.driver.inspect_select(selector)
            elif request.capability == "browser.select_option":
                option_identity = request.arguments.get("option_identity")
                if not isinstance(option_identity, dict):
                    raise ValueError("option_identity must be dict")
                data = self.driver.select_option_by_identity(dict(request.arguments), option_identity)
            elif request.capability == "browser.inspect_field":
                selector = self._required(request, "selector")
                data = self.driver.inspect_field(selector)
            elif request.capability == "browser.set_field_value":
                target_value = request.arguments.get("target_value")
                if not isinstance(target_value, str):
                    raise ValueError("target_value must be str")
                data = self.driver.set_field_value_by_identity(dict(request.arguments), target_value)
            elif request.capability == "browser.inspect_form_submission":
                form_selector = self._required(request, "form_selector")
                submitter_selector = self._required(request, "submitter_selector")
                data = self.driver.inspect_form_submission(form_selector, submitter_selector)
            elif request.capability == "browser.submit_get_navigation":
                data = self.driver.submit_get_navigation_by_identity(dict(request.arguments))
            elif request.capability == "browser.click":
                selector = self._required(request, "selector")
                data = self.driver.click(selector)
            else:
                return ActionResult(False, "unsupported browser capability", backend=self.name)
        except (KeyError, ValueError) as exc:
            return ActionResult(False, str(exc), backend=self.name)
        except Exception as exc:
            return ActionResult(
                False,
                f"browser driver failure: {type(exc).__name__}: {exc}",
                backend=self.name,
            )
        return ActionResult(True, "browser action completed", data=data, backend=self.name)

    @staticmethod
    def _required(request: ActionRequest, key: str) -> str:
        value = request.arguments.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"missing browser argument: {key}")
        return value.strip()
