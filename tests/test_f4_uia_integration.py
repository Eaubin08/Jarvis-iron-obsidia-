import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows-only UIA integration")

from jarvis.integrations.uia_driver import UIADriver


def test_real_uia_finds_and_invokes_structured_controls():
    fixture = Path(__file__).with_name("fixtures") / "uia_app.py"
    process = subprocess.Popen([sys.executable, str(fixture)])
    driver = UIADriver()
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                win = driver.window(title="Jarvis UIA Fixture")
                win.wait("visible", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        else:
            pytest.fail("UIA fixture window did not appear")

        edit = win.child_window(control_type="Edit")
        edit.wait("ready", timeout=5)
        edit.set_edit_text("hello")

        buttons = win.descendants(control_type="Button")
        assert buttons, "UIA fixture exposes no Button control"
        buttons[0].invoke()

        deadline = time.time() + 5
        while time.time() < deadline:
            texts = [c.window_text() for c in win.descendants(control_type="Text")]
            if any("saved:hello" in value for value in texts):
                return
            time.sleep(0.1)
        pytest.fail(f"UIA action did not update fixture text; observed={texts!r}")
    finally:
        process.terminate()
        process.wait(timeout=10)
