import sys
import time

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows-only integration")

from jarvis.integrations.win32_driver import Win32Driver


def test_real_win32_lists_visible_windows():
    result = Win32Driver().list_windows()
    assert "windows" in result
    assert isinstance(result["windows"], list)


def test_real_win32_opens_and_finds_notepad():
    driver = Win32Driver()
    before = {item["hwnd"] for item in driver.list_windows()["windows"]}
    opened = driver.open_app("notepad.exe")
    assert opened["pid"] > 0
    try:
        deadline = time.time() + 10
        while time.time() < deadline:
            windows = driver.list_windows()["windows"]
            if any(
                item["pid"] == opened["pid"]
                or (
                    item["hwnd"] not in before
                    and item["class_name"] in {"Notepad", "ApplicationFrameWindow"}
                )
                for item in windows
            ):
                return
            time.sleep(0.25)
        pytest.fail("Notepad did not expose a visible window within 10 seconds")
    finally:
        try:
            import os
            import signal

            os.kill(opened["pid"], signal.SIGTERM)
        except OSError:
            pass
