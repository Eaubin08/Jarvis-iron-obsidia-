from jarvis.integrations.win32_driver import Win32Driver


class FakeGui:
    def __init__(self):
        self.calls = []

    def IsWindow(self, hwnd):
        return hwnd == 42

    def GetWindowText(self, hwnd):
        return "Target"

    def ShowWindow(self, hwnd, command):
        self.calls.append((hwnd, command))


class FakeCon:
    SW_MINIMIZE = 1
    SW_MAXIMIZE = 2
    SW_RESTORE = 3


def test_hwnd_window_state_does_not_reresolve_title(monkeypatch):
    gui = FakeGui()
    driver = Win32Driver()
    monkeypatch.setattr(driver, "_modules", lambda: (FakeCon(), gui, object()))
    result = driver._window_state_hwnd(42, "restore")
    assert result["hwnd"] == 42
    assert result["title"] == "Target"
    assert gui.calls == [(42, FakeCon.SW_RESTORE)]
