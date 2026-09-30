from jarvis.contracts import ActionRequest, Capability, ContextSnapshot, RiskClass
from jarvis.fast_intent import FastIntentRouter
from jarvis.local_actions import LocalPermissionPolicy
from jarvis.windows import NativeWindowsBackend


class FakeWindows:
    def __init__(self):
        self.calls = []

    def wifi_status(self):
        self.calls.append(("wifi_status",))
        return {"available": True}

    def wifi_set_enabled(self, enabled):
        self.calls.append(("wifi_set_enabled", enabled))
        return {"enabled": enabled}

    def bluetooth_status(self):
        self.calls.append(("bluetooth_status",))
        return {"available": True}

    def bluetooth_set_enabled(self, enabled):
        self.calls.append(("bluetooth_set_enabled", enabled))
        return {"enabled": enabled}

    def window_state(self, title, state):
        self.calls.append(("window_state", title, state))
        return {"title": title, "state": state}

    def move_window_to_monitor(self, title, monitor_index):
        self.calls.append(("move_window_to_monitor", title, monitor_index))
        return {"title": title, "monitor_index": monitor_index}


def backend():
    return NativeWindowsBackend(FakeWindows())


def test_wifi_and_bluetooth_status_are_read_only_intents():
    wifi = FastIntentRouter().route("état wifi")
    bt = FastIntentRouter().route("bluetooth")
    assert wifi.request.capability == "wifi.status"
    assert wifi.request.risk is RiskClass.READ_ONLY
    assert bt.request.capability == "bluetooth.status"
    assert bt.request.risk is RiskClass.READ_ONLY


def test_network_toggles_require_approval():
    policy = LocalPermissionPolicy()
    context = ContextSnapshot("test")
    for text in ("coupe le wifi", "active le bluetooth"):
        match = FastIntentRouter().route(text)
        assert match is not None
        assert match.request.risk is RiskClass.SENSITIVE
        assert policy.evaluate(match.request, context).value == "ask"


def test_window_state_intents_are_structured():
    match = FastIntentRouter().route("maximise powershell")
    assert match is not None
    assert match.request.capability == "window.maximize"
    assert match.request.arguments == {"title": "powershell"}


def test_window_monitor_intent_is_structured():
    match = FastIntentRouter().route("mets powershell écran 2")
    assert match is not None
    assert match.request.capability == "window.move_monitor"
    assert match.request.arguments == {"title": "powershell", "monitor_index": 2}


def test_windows_backend_executes_network_status_and_window_move():
    driver = FakeWindows()
    backend = NativeWindowsBackend(driver)

    result = backend.execute(ActionRequest("wifi.status"))
    assert result.ok

    result = backend.execute(
        ActionRequest("window.move_monitor", {"title": "PowerShell", "monitor_index": 2})
    )
    assert result.ok
    assert driver.calls == [
        ("wifi_status",),
        ("move_window_to_monitor", "PowerShell", 2),
    ]


def test_windows_backend_rejects_invalid_monitor_index():
    result = backend().execute(
        ActionRequest("window.move_monitor", {"title": "PowerShell", "monitor_index": 0})
    )
    assert not result.ok
    assert "monitor_index" in result.message
