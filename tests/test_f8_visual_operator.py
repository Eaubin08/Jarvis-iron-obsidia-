from jarvis.actions import ActionRouter
from jarvis.browser import BrowserBackend
from jarvis.contracts import ActionRequest, ActionResult, Capability, ContextSnapshot, PermissionDecision
from jarvis.visual import VisualOperatorBackend
from jarvis.windows import NativeWindowsBackend


class Allow:
    def evaluate(self, request, context):
        return PermissionDecision.ALLOW


class Registry:
    def __init__(self, family):
        self.family = family

    def resolve(self, request):
        return Capability(request.capability, self.family)


class NativeDriver:
    def __init__(self):
        self.calls = []

    def open_app(self, app):
        self.calls.append(("open_app", app))
        return {"app": app}

    def list_windows(self):
        self.calls.append(("list_windows",))
        return {"windows": []}

    def focus_window(self, title):
        self.calls.append(("focus_window", title))
        return {"title": title}


class BrowserDriver:
    def __init__(self):
        self.calls = []

    def navigate(self, url):
        self.calls.append(("navigate", url))
        return {"url": url}

    def read(self, selector=None):
        self.calls.append(("read", selector))
        return {"text": ""}

    def click(self, selector):
        self.calls.append(("click", selector))
        return {"selector": selector}

    def fill(self, selector, value):
        self.calls.append(("fill", selector, value))
        return {"selector": selector, "value": value}


class VisualDriver:
    def __init__(self, state=None):
        self.state = state or {"observation_id": "live-1", "pixels": "fresh"}
        self.calls = []

    def snapshot(self):
        self.calls.append(("snapshot",))
        return self.state

    def execute(self, request, state):
        self.calls.append(("execute", request.capability, state["observation_id"]))
        return {"ok": True, "evidence_ref": "receipt:visual-1"}


class RawBackend:
    name = "raw.input"
    priority = 50

    def __init__(self):
        self.calls = []

    def can_execute(self, request, capability):
        return capability.backend_family == "visual"

    def execute(self, request):
        self.calls.append(request)
        return ActionResult(True, "raw")


def test_action_router_prefers_native_over_visual_fallback():
    native_driver = NativeDriver()
    visual_driver = VisualDriver()
    router = ActionRouter(
        Registry("windows"),
        Allow(),
        [VisualOperatorBackend(visual_driver), NativeWindowsBackend(native_driver)],
    )

    result = router.execute(ActionRequest("app.open", {"app": "notepad"}), ContextSnapshot(""))

    assert result.ok
    assert result.backend == "windows.structured"
    assert native_driver.calls == [("open_app", "notepad")]
    assert visual_driver.calls == []


def test_action_router_prefers_browser_dom_over_visual_fallback():
    browser_driver = BrowserDriver()
    visual_driver = VisualDriver()
    router = ActionRouter(
        Registry("browser"),
        Allow(),
        [VisualOperatorBackend(visual_driver), BrowserBackend(browser_driver)],
    )

    result = router.execute(ActionRequest("browser.click", {"selector": "#save"}), ContextSnapshot(""))

    assert result.ok
    assert result.backend == "browser.structured"
    assert browser_driver.calls == [("click", "#save")]
    assert visual_driver.calls == []


def test_visual_operator_refreshes_current_state_before_consequential_action():
    driver = VisualDriver()
    backend = VisualOperatorBackend(driver)

    result = backend.execute(ActionRequest("visual.click", {"description": "save"}))

    assert result.ok
    assert driver.calls == [("snapshot",), ("execute", "visual.click", "live-1")]
    assert result.backend == "visual.operator"
    assert result.evidence_refs == ("visual_state:live-1", "receipt:visual-1")


def test_historical_screenpipe_observation_cannot_be_reused_as_visual_handle():
    driver = VisualDriver()
    backend = VisualOperatorBackend(driver)

    result = backend.execute(
        ActionRequest("visual.click", {"screenpipe_observation_id": "old-ocr-1", "x": 10, "y": 20})
    )

    assert not result.ok
    assert "historical observation" in result.message
    assert driver.calls == []


def test_visual_fallback_stays_above_raw_input():
    visual = VisualOperatorBackend(VisualDriver())
    raw = RawBackend()
    router = ActionRouter(Registry("visual"), Allow(), [raw, visual])

    result = router.execute(ActionRequest("visual.click", {"description": "save"}), ContextSnapshot(""))

    assert result.backend == "visual.operator"
    assert raw.calls == []
