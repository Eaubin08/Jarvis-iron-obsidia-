from jarvis.integrations.win32_driver import Win32Driver


class Monitor:
    def __init__(self, left, top, width, height):
        self.left = left
        self.top = top
        self.width = width
        self.height = height


class Layout:
    monitors = (
        Monitor(0, 0, 1920, 1080),
        Monitor(1920, 0, 1280, 720),
    )


class Provider:
    def snapshot(self):
        return Layout()


class FakeGui:
    def IsWindow(self, hwnd):
        return True

    def GetWindowText(self, hwnd):
        return "Target"

    def GetWindowRect(self, hwnd):
        return (100, 100, 900, 700)

    def IsIconic(self, hwnd):
        return False

    def MoveWindow(self, hwnd, left, top, width, height, repaint):
        self.moved = (hwnd, left, top, width, height, repaint)


def test_move_window_reuses_monitor_provider(monkeypatch):
    gui = FakeGui()
    driver = Win32Driver()

    monkeypatch.setattr(driver, "_modules", lambda: (object(), gui, object()))
    monkeypatch.setattr(
        "jarvis.integrations.win32_driver.WindowsMonitorProvider",
        lambda: Provider(),
    )

    result = driver._move_window_to_monitor_hwnd(42, 2)

    assert result["monitor_index"] == 2
    assert result["monitor_count"] == 2
    assert result["bounds"]["left"] == 1920
    assert result["bounds"]["top"] == 0
    assert gui.moved[:3] == (42, 1920, 0)
