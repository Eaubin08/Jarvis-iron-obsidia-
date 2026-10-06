from jarvis.actions import ActionRouter
from jarvis.capabilities import LocalCapabilityRegistry
from jarvis.contracts import Capability
from jarvis.core import JarvisCore
from jarvis.fast_intent import FastIntentRouter
from jarvis.local_actions import LocalPermissionPolicy
from jarvis.providers.local_stub import StubCognition, StubMemory
from jarvis.windows import NativeWindowsBackend


class FakeWindows:
    def __init__(self):
        self.calls = []

    def open_app(self, app):
        self.calls.append(("open_app", app))
        return {"app": app}

    def list_windows(self):
        return {"windows": []}

    def focus_window(self, title):
        return {"title": title}

    def close_window(self, title):
        self.calls.append(("close_window", title))
        return {"title": title}

    def media_key(self, key):
        self.calls.append(("media_key", key))
        return {"key": key}

    def battery_status(self):
        self.calls.append(("battery_status",))
        return {"battery_percent": 77, "ac_online": True}


def build_core():
    driver = FakeWindows()
    registry = LocalCapabilityRegistry()
    for name in (
        "app.open",
        "audio.volume_up",
        "audio.volume_down",
        "audio.mute_toggle",
        "media.play_pause",
        "media.next",
        "media.previous",
        "system.battery",
    ):
        registry.register(Capability(name, "windows"))
    actions = ActionRouter(
        registry,
        LocalPermissionPolicy(),
        [NativeWindowsBackend(driver)],
    )
    return JarvisCore(
        StubCognition(),
        StubMemory(),
        fast_intent=FastIntentRouter(),
        actions=actions,
    ), driver


def test_live_core_routes_volume_without_cognition():
    core, driver = build_core()
    assert core.handle_text("monte le volume") == "Windows action completed"
    assert driver.calls == [("media_key", "volume_up")]


def test_live_core_routes_battery_read_only():
    core, driver = build_core()
    assert core.handle_text("batterie") == "Batterie : 77 %. État : branché sur secteur."
    assert driver.calls == [("battery_status",)]


def test_live_core_opens_bounded_app():
    core, driver = build_core()
    assert core.handle_text("ouvre la calculatrice") == "Windows action completed"
    assert driver.calls == [("open_app", "calculatrice")]
