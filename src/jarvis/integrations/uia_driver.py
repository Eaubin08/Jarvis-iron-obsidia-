"""UI Automation driver for structured control-level Windows interaction."""
from __future__ import annotations


class UIADriver:
    def _desktop(self):
        try:
            from pywinauto import Desktop
        except ImportError as exc:
            raise RuntimeError("pywinauto is not installed; install the windows optional dependency") from exc
        return Desktop(backend="uia")

    def window(self, *, title: str):
        return self._desktop().window(title=title)

    def set_text(self, *, window_title: str, control_name: str, value: str) -> dict:
        win = self.window(title=window_title)
        control = win.child_window(title=control_name, control_type="Edit")
        control.wait("ready", timeout=10)
        control.set_edit_text(value)
        return {"window": window_title, "control": control_name, "value": value}

    def click(self, *, window_title: str, control_name: str, control_type: str = "Button") -> dict:
        win = self.window(title=window_title)
        control = win.child_window(title=control_name, control_type=control_type)
        control.wait("enabled", timeout=10)
        control.invoke()
        return {"window": window_title, "control": control_name}

    def read_text(self, *, window_title: str, control_name: str, control_type: str = "Text") -> dict:
        win = self.window(title=window_title)
        control = win.child_window(title=control_name, control_type=control_type)
        control.wait("exists", timeout=10)
        return {"window": window_title, "control": control_name, "text": control.window_text()}
