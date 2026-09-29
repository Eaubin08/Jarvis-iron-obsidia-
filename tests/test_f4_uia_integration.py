import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows-only UIA integration")

from jarvis.integrations.uia_driver import UIADriver


def test_real_uia_finds_and_invokes_named_controls():
    fixture = Path(__file__).with_name("fixtures") / "uia_app.py"
    process = subprocess.Popen([sys.executable, str(fixture)])
    driver = UIADriver()
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                driver.window(title="Jarvis UIA Fixture").wait("visible", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        else:
            pytest.fail("UIA fixture window did not appear")

        # Tk exposes the edit control without relying on screen coordinates.
        win = driver.window(title="Jarvis UIA Fixture")
        edit = win.child_window(control_type="Edit")
        edit.wait("ready", timeout=5)
        edit.set_edit_text("hello")

        driver.click(window_title="Jarvis UIA Fixture", control_name="Save")
        text_controls = win.descendants(control_type="Text")
        assert any("saved:hello" in control.window_text() for control in text_controls)
    finally:
        process.terminate()
        process.wait(timeout=10)
