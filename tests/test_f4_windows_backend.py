from jarvis.contracts import ActionRequest, Capability
from jarvis.windows import NativeWindowsBackend


class FakeWindows:
    def __init__(self):
        self.calls = []

    def open_app(self, app):
        self.calls.append(("open_app", app))
        return {"app": app}

    def list_windows(self):
        self.calls.append(("list_windows",))
        return {"windows": ["Editor", "Browser"]}

    def focus_window(self, title):
        self.calls.append(("focus_window", title))
        return {"title": title}


def test_open_app_uses_structured_windows_driver():
    driver = FakeWindows()
    backend = NativeWindowsBackend(driver)
    result = backend.execute(ActionRequest("app.open", {"app": "notepad"}))
    assert result.ok
    assert driver.calls == [("open_app", "notepad")]


def test_window_list_needs_no_coordinates():
    result = NativeWindowsBackend(FakeWindows()).execute(ActionRequest("window.list"))
    assert result.ok
    assert result.data["windows"] == ["Editor", "Browser"]


def test_focus_requires_title():
    result = NativeWindowsBackend(FakeWindows()).execute(ActionRequest("window.focus"))
    assert not result.ok
    assert "title" in result.message


def test_backend_does_not_claim_visual_capability():
    backend = NativeWindowsBackend(FakeWindows())
    assert not backend.can_execute(
        ActionRequest("window.focus", {"title": "Editor"}),
        Capability("window.focus", "visual"),
    )
