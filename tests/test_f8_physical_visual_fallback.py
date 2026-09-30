import os
import tkinter as tk

import pytest

from jarvis.actions import ActionRouter
from jarvis.contracts import ActionRequest, Capability, ContextSnapshot, PermissionDecision
from jarvis.integrations.pyautogui_visual_driver import PyAutoGUIVisualDriver
from jarvis.visual import VisualOperatorBackend


ENV = "JARVIS_REAL_VISUAL_TEST"


class Allow:
    def evaluate(self, request, context):
        return PermissionDecision.ALLOW


class VisualRegistry:
    def resolve(self, request):
        return Capability(request.capability, "visual")


@pytest.mark.skipif(
    os.environ.get(ENV) != "1",
    reason="JARVIS_REAL_VISUAL_TEST=1 required for physical visual fallback",
)
def test_physical_visual_fallback_clicks_fresh_local_target():
    clicked = {"value": False}

    root = tk.Tk()
    root.title("Jarvis Visual Gate")
    root.geometry("420x220+120+120")
    root.attributes("-topmost", True)

    label = tk.Label(root, text="W07 VISUAL FALLBACK TEST")
    label.pack(pady=20)

    def mark_clicked():
        clicked["value"] = True

    button = tk.Button(root, text="CLICK ME", command=mark_clicked, width=20, height=3)
    button.pack(pady=20)

    try:
        root.update_idletasks()
        root.update()

        # Resolve the actual on-screen button centre from the local test fixture.
        x = button.winfo_rootx() + button.winfo_width() // 2
        y = button.winfo_rooty() + button.winfo_height() // 2

        router = ActionRouter(
            VisualRegistry(),
            Allow(),
            [VisualOperatorBackend(PyAutoGUIVisualDriver())],
        )
        result = router.execute(
            ActionRequest("visual.click", {"x": int(x), "y": int(y), "description": "local W07 test button"}),
            ContextSnapshot("physical W07 gate"),
        )

        root.update_idletasks()
        root.update()

        assert result.ok, result.message
        assert result.backend == "visual.operator"
        assert any(ref.startswith("visual_state:") for ref in result.evidence_refs)
        assert any(ref.startswith("screenshot:") for ref in result.evidence_refs)
        assert clicked["value"] is True
    finally:
        root.destroy()
