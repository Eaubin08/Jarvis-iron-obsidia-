"""Physical Windows visual fallback driver.

This adapter intentionally exposes only bounded coordinate actions. It always
captures a fresh screenshot before the VisualOperatorBackend invokes execute().
Coordinates use Windows virtual-desktop space so secondary displays with
negative origins remain addressable.
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from jarvis.contracts import ActionRequest
from jarvis.monitor_layout import WindowsMonitorProvider


class PyAutoGUIVisualDriver:
    def __init__(
        self,
        *,
        evidence_dir: str | Path = "runtime_data/visual_snapshots",
        monitor_provider=None,
    ):
        self.evidence_dir = Path(evidence_dir)
        self.monitor_provider = monitor_provider or WindowsMonitorProvider()

    def _pyautogui(self):
        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError(
                "pyautogui is not installed; install the visual optional dependency"
            ) from exc
        return pyautogui

    def _capture_virtual_desktop(self, path: Path, layout) -> None:
        try:
            from PIL import ImageGrab
        except ImportError as exc:
            raise RuntimeError(
                "Pillow is not installed; install the visual optional dependency"
            ) from exc

        image = ImageGrab.grab(
            bbox=(layout.left, layout.top, layout.right, layout.bottom),
            all_screens=True,
        )
        image.save(path)

    def snapshot(self) -> dict:
        observation_id = uuid4().hex
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        path = self.evidence_dir / f"{observation_id}.png"
        layout = self.monitor_provider.layout()
        self._capture_virtual_desktop(path, layout)

        return {
            "observation_id": observation_id,
            "left": layout.left,
            "top": layout.top,
            "right": layout.right,
            "bottom": layout.bottom,
            "width": layout.width,
            "height": layout.height,
            "coordinate_space": "windows_virtual_desktop",
            "monitors": [
                {
                    "monitor_id": m.monitor_id,
                    "left": m.left,
                    "top": m.top,
                    "right": m.right,
                    "bottom": m.bottom,
                    "width": m.width,
                    "height": m.height,
                    "primary": m.primary,
                }
                for m in layout.monitors
            ],
            "screenshot_path": str(path),
        }

    def execute(self, request: ActionRequest, state: dict) -> dict:
        if request.capability != "visual.click":
            raise ValueError(f"unsupported visual capability: {request.capability}")

        x = request.arguments.get("x")
        y = request.arguments.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            raise ValueError("visual.click requires integer x/y coordinates")

        left = int(state.get("left", 0))
        top = int(state.get("top", 0))
        right = int(state.get("right", left + int(state["width"])))
        bottom = int(state.get("bottom", top + int(state["height"])))
        if not (left <= x < right and top <= y < bottom):
            raise ValueError(
                "visual.click coordinates are outside the fresh virtual-desktop bounds"
            )

        monitor_id = None
        for monitor in state.get("monitors", []):
            if (
                int(monitor["left"]) <= x < int(monitor["right"])
                and int(monitor["top"]) <= y < int(monitor["bottom"])
            ):
                monitor_id = str(monitor["monitor_id"])
                break
        if state.get("monitors") and monitor_id is None:
            raise ValueError("visual.click coordinates fall in a gap between monitors")

        pyautogui = self._pyautogui()
        pyautogui.click(x=x, y=y)

        return {
            "ok": True,
            "x": x,
            "y": y,
            "monitor_id": monitor_id,
            "coordinate_space": "windows_virtual_desktop",
            "evidence_ref": f"screenshot:{state['screenshot_path']}",
        }
