"""Opt-in physical semantic-click gate for a real UI-TARS-compatible endpoint."""
from __future__ import annotations

import os
import tkinter as tk

import pytest

from jarvis.contracts import ActionRequest
from jarvis.integrations.pyautogui_visual_driver import PyAutoGUIVisualDriver
from jarvis.integrations.uitars_grounded_visual_driver import UITARSGroundedVisualDriver
from jarvis.integrations.uitars_openai_grounder import OpenAICompatibleUITARSGrounder
from jarvis.visual import VisualOperatorBackend


pytestmark = pytest.mark.skipif(
    os.getenv("JARVIS_REAL_UITARS_TEST") != "1",
    reason="set JARVIS_REAL_UITARS_TEST=1 for the physical semantic-click gate",
)


def test_real_uitars_semantic_click_hits_disposable_local_button(tmp_path):
    base_url = os.environ["JARVIS_UITARS_BASE_URL"]
    model = os.environ["JARVIS_UITARS_MODEL"]
    api_key = os.getenv("JARVIS_UITARS_API_KEY", "empty")

    root = tk.Tk()
    root.title("Jarvis UI-TARS Gate")
    root.geometry("520x260+180+180")
    root.attributes("-topmost", True)

    clicked = {"value": False}
    label = tk.Label(root, text="UI-TARS PHYSICAL GATE", font=("Arial", 18))
    label.pack(pady=30)
    button = tk.Button(
        root,
        text="CLICK TARGET",
        font=("Arial", 18),
        command=lambda: clicked.__setitem__("value", True),
    )
    button.pack(pady=20)
    root.update()

    try:
        physical = PyAutoGUIVisualDriver(evidence_dir=tmp_path / "visual")
        grounder = OpenAICompatibleUITARSGrounder(
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout_seconds=120,
        )
        driver = UITARSGroundedVisualDriver(
            physical_driver=physical,
            grounding_provider=grounder,
        )
        result = VisualOperatorBackend(driver).execute(
            ActionRequest(
                "visual.semantic_click",
                {
                    "description": (
                        "Click the large button labeled CLICK TARGET in the "
                        "Jarvis UI-TARS Gate window."
                    )
                },
            )
        )
        root.update()
        assert result.ok, result.message
        assert result.backend == "visual.operator"
        assert clicked["value"] is True
        assert any(ref.startswith("visual_state:") for ref in result.evidence_refs)
    finally:
        root.destroy()
