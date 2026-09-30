"""Physical Windows visual fallback driver.

This adapter intentionally exposes only bounded coordinate actions. It always
captures a fresh screenshot before the VisualOperatorBackend invokes execute().
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from jarvis.contracts import ActionRequest


class PyAutoGUIVisualDriver:
    def __init__(self, *, evidence_dir: str | Path = "runtime_data/visual_snapshots"):
        self.evidence_dir = Path(evidence_dir)

    def _pyautogui(self):
        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError(
                "pyautogui is not installed; install the visual optional dependency"
            ) from exc
        return pyautogui

    def snapshot(self) -> dict:
        pyautogui = self._pyautogui()
        observation_id = uuid4().hex
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        path = self.evidence_dir / f"{observation_id}.png"
        image = pyautogui.screenshot()
        image.save(path)
        width, height = pyautogui.size()
        return {
            "observation_id": observation_id,
            "width": int(width),
            "height": int(height),
            "screenshot_path": str(path),
        }

    def execute(self, request: ActionRequest, state: dict) -> dict:
        if request.capability != "visual.click":
            raise ValueError(f"unsupported visual capability: {request.capability}")

        x = request.arguments.get("x")
        y = request.arguments.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            raise ValueError("visual.click requires integer x/y coordinates")

        width = int(state["width"])
        height = int(state["height"])
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError("visual.click coordinates are outside the fresh screen bounds")

        pyautogui = self._pyautogui()
        pyautogui.click(x=x, y=y)

        return {
            "ok": True,
            "x": x,
            "y": y,
            "evidence_ref": f"screenshot:{state['screenshot_path']}",
        }
