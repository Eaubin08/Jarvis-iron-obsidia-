from jarvis.contracts import ActionRequest, Capability
from jarvis.structured_ui import StructuredUIBackend


class FakeUI:
    def __init__(self):
        self.calls = []

    def list_controls(self, *, window_title):
        self.calls.append(("list_controls", window_title))
        return {"window": window_title, "controls": [{"name": "Save", "enabled": True}]}

    def click(self, *, window_title, control_name, control_type="Button"):
        self.calls.append(("click", window_title, control_name, control_type))
        return {"window": window_title, "control": control_name}

    def set_text(self, *, window_title, control_name, value):
        self.calls.append(("set_text", window_title, control_name, value))
        return {"value": value}

    def read_text(self, *, window_title, control_name, control_type="Text"):
        self.calls.append(("read_text", window_title, control_name, control_type))
        return {"text": "hello"}


def test_lists_controls_as_structured_windows_action():
    driver = FakeUI()
    backend = StructuredUIBackend(driver)
    request = ActionRequest("control.list", {"window_title": "Editor"})

    assert backend.can_execute(request, Capability("control.list", "windows"))
    result = backend.execute(request)

    assert result.ok
    assert result.backend == "windows.uia"
    assert driver.calls == [("list_controls", "Editor")]


def test_click_uses_named_control_not_coordinates():
    driver = FakeUI()
    result = StructuredUIBackend(driver).execute(
        ActionRequest(
            "control.click",
            {"window_title": "Editor", "control_name": "Save", "control_type": "Button"},
        )
    )

    assert result.ok
    assert driver.calls == [("click", "Editor", "Save", "Button")]


def test_set_and_read_text_are_structured():
    driver = FakeUI()
    backend = StructuredUIBackend(driver)

    assert backend.execute(
        ActionRequest(
            "control.set_text",
            {"window_title": "Editor", "control_name": "Name", "value": "Jarvis"},
        )
    ).ok
    assert backend.execute(
        ActionRequest(
            "control.read_text",
            {"window_title": "Editor", "control_name": "Status"},
        )
    ).data["text"] == "hello"


def test_missing_window_fails_closed():
    result = StructuredUIBackend(FakeUI()).execute(ActionRequest("control.list"))
    assert not result.ok
    assert "window_title" in result.message


def test_does_not_claim_visual_family():
    backend = StructuredUIBackend(FakeUI())
    assert not backend.can_execute(
        ActionRequest("control.click", {"window_title": "x", "control_name": "y"}),
        Capability("control.click", "visual"),
    )
