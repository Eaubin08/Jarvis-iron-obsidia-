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

        driver.set_text(
            window_title="Jarvis UIA Fixture",
            control_name="",
            value="hello",
        )

        driver.click(window_title="Jarvis UIA Fixture", control_name="Save")

        deadline = time.time() + 5
        while time.time() < deadline:
            result = driver.read_text(
                window_title="Jarvis UIA Fixture",
                control_name="saved:hello",
            )
            if result["text"] == "saved:hello":
                return
            time.sleep(0.1)
        pytest.fail("UIA action did not update fixture text")
    finally:
        process.terminate()
        process.wait(timeout=10)
