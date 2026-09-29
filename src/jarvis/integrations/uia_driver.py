"""UI Automation driver for structured control-level Windows interaction."""
from __future__ import annotations

from pathlib import Path
import sys
import types


def _prepare_comtypes_cache() -> None:
    """Keep generated UIA wrappers out of user AppData and site-packages."""

    try:
        import comtypes
    except ImportError:
        return
    cache_dir = Path.cwd() / "runtime_data" / "comtypes_gen"
    cache_dir.mkdir(parents=True, exist_ok=True)
    init_file = cache_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("# comtypes.gen package, directory for generated files.\n", encoding="utf-8")
    gen = types.ModuleType("comtypes.gen")
    gen.__path__ = [str(cache_dir)]
    sys.modules["comtypes.gen"] = gen
    comtypes.gen = gen


class UIADriver:
    def _desktop(self):
        try:
            _prepare_comtypes_cache()
            sys.coinit_flags = 2
            from pywinauto import Desktop
        except ImportError as exc:
            raise RuntimeError("pywinauto is not installed; install the windows optional dependency") from exc
        return Desktop(backend="win32")

    def window(self, *, title: str):
        return self._desktop().window(title=title)

    def set_text(self, *, window_title: str, control_name: str, value: str) -> dict:
        win = self.window(title=window_title)
        control = win.child_window(title=control_name, class_name="Edit")
        control.wait("ready", timeout=10)
        control.set_edit_text(value)
        return {"window": window_title, "control": control_name, "value": value}

    def click(self, *, window_title: str, control_name: str, control_type: str = "Button") -> dict:
        win = self.window(title=window_title)
        class_name = "Button" if control_type == "Button" else control_type
        control = win.child_window(title=control_name, class_name=class_name)
        control.wait("enabled", timeout=10)
        control.click()
        return {"window": window_title, "control": control_name}

    def read_text(self, *, window_title: str, control_name: str, control_type: str = "Text") -> dict:
        win = self.window(title=window_title)
        class_name = "Static" if control_type == "Text" else control_type
        control = win.child_window(title=control_name, class_name=class_name)
        control.wait("exists", timeout=10)
        return {"window": window_title, "control": control_name, "text": control.window_text()}
