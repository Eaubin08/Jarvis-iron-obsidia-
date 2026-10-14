from __future__ import annotations

from jarvis.browser import BrowserBackend
from jarvis.contracts import ActionRequest
from jarvis.integrations.playwright_driver import PlaywrightDriver


SID = "sess-aaaaaaaaaaaaaaaaaaaaaaaaaaaa"
PID = "page-bbbbbbbbbbbbbbbbbbbbbbbb"
URL = "https://example.com/page"


class FakeContext:
    def __init__(self):
        self.handlers = {}

    def on(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)

    def fire(self, event):
        for handler in self.handlers.get(event, []):
            handler(object())


class FakeLocator:
    def __init__(
        self,
        page,
        *,
        count=1,
        tag_name="details",
        role="",
        aria_expanded=None,
        aria_controls="",
        open_state=False,
        visible=True,
        enabled=True,
        text="Disclosure",
    ):
        self.page = page
        self._count = count
        self.tag_name = tag_name
        self.role = role
        self.aria_expanded = aria_expanded
        self.aria_controls = aria_controls
        self.open_state = open_state
        self.visible = visible
        self.enabled = enabled
        self.text = text
        self.clicks = 0
        self.first = self

    def count(self):
        return self._count

    def inner_text(self):
        return self.text

    def get_attribute(self, name):
        if name == "data-tag-name":
            return self.tag_name
        if name == "role":
            return self.role
        if name == "aria-expanded":
            return self.aria_expanded
        if name == "aria-controls":
            return self.aria_controls
        if name == "open":
            return "" if self.open_state else None
        return None

    def is_visible(self):
        return self.visible

    def is_enabled(self):
        return self.enabled

    def click(self):
        self.clicks += 1
        if self.page.event_to_fire:
            self.page.fire(self.page.event_to_fire)
            return
        if self.page.navigate_on_click:
            self.page._url = "https://example.com/other"
        if self.tag_name == "details":
            self.open_state = not self.open_state
        elif self.aria_expanded in {"true", "false"}:
            self.aria_expanded = "false" if self.aria_expanded == "true" else "true"


class FakePage:
    def __init__(self, locator):
        self._url = URL
        self._closed = False
        self.context = FakeContext()
        self.handlers = {}
        self.locator_obj = locator
        self.event_to_fire = ""
        self.navigate_on_click = False
        locator.page = self

    @property
    def url(self):
        return self._url

    def title(self):
        return "Fake"

    def is_closed(self):
        return self._closed

    def locator(self, selector):
        return self.locator_obj

    def on(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)

    def fire(self, event):
        target = self.context if event == "page" else self
        for handler in target.handlers.get(event, []):
            handler(object())


def _driver(locator):
    page = FakePage(locator)
    d = PlaywrightDriver()
    d._page = page
    d._browser_session_id = SID
    d._page_id = PID
    return d, page, locator


def _set(driver, identity, target):
    args = dict(identity)
    args["target_expanded"] = target
    return BrowserBackend(driver).execute(ActionRequest("browser.set_disclosure", args))


def test_details_closed_to_expanded_true():
    d, _page, loc = _driver(FakeLocator(None, open_state=False))
    ident = d.inspect_disclosure("details#x")
    result = _set(d, ident, True)
    assert result.ok
    assert result.data["current_expanded"] is True
    assert result.data["mutation_performed"] is True
    assert loc.clicks == 1


def test_details_open_to_expanded_false():
    d, _page, loc = _driver(FakeLocator(None, open_state=True))
    result = _set(d, d.inspect_disclosure("details#x"), False)
    assert result.ok
    assert result.data["current_expanded"] is False
    assert loc.clicks == 1


def test_details_noop_is_verified_without_activation():
    d, _page, loc = _driver(FakeLocator(None, open_state=True))
    result = _set(d, d.inspect_disclosure("details#x"), True)
    assert result.ok
    assert result.data["mutation_performed"] is False
    assert loc.clicks == 0


def test_details_post_state_mismatch_fail_closed():
    d, _page, loc = _driver(FakeLocator(None, open_state=False))
    ident = d.inspect_disclosure("details#x")
    loc.click = lambda: setattr(loc, "clicks", loc.clicks + 1)
    result = _set(d, ident, True)
    assert not result.ok
    assert "REALIZED_STATE_MISMATCH" in result.message


def test_aria_false_to_true_and_true_to_false():
    d, _page, loc = _driver(FakeLocator(None, tag_name="button", aria_expanded="false"))
    r1 = _set(d, d.inspect_disclosure("button#menu"), True)
    assert r1.ok and r1.data["current_expanded"] is True and loc.clicks == 1
    ident = d.inspect_disclosure("button#menu")
    r2 = _set(d, ident, False)
    assert r2.ok and r2.data["current_expanded"] is False and loc.clicks == 2


def test_aria_noop_is_verified_without_activation():
    d, _page, loc = _driver(FakeLocator(None, tag_name="button", aria_expanded="false"))
    result = _set(d, d.inspect_disclosure("button#menu"), False)
    assert result.ok
    assert result.data["mutation_performed"] is False
    assert loc.clicks == 0


def test_invalid_or_missing_aria_expanded_rejected():
    for value in ("mixed", "", None):
        d, _page, _loc = _driver(FakeLocator(None, tag_name="button", aria_expanded=value))
        result = _set(d, d.inspect_disclosure("button#menu"), True)
        assert not result.ok
        assert "UNSUPPORTED_DISCLOSURE_CLASS" in result.message


def test_common_rejections():
    cases = [
        (FakeLocator(None, count=0), "SELECTOR_COUNT_DRIFT"),
        (FakeLocator(None, count=2), "SELECTOR_COUNT_DRIFT"),
        (FakeLocator(None, visible=False), "ELEMENT_NOT_VISIBLE"),
        (FakeLocator(None, enabled=False), "ELEMENT_NOT_ENABLED"),
        (FakeLocator(None, tag_name="div"), "UNSUPPORTED_DISCLOSURE_CLASS"),
    ]
    for loc, message in cases:
        d, _page, _loc = _driver(loc)
        result = _set(d, d.inspect_disclosure("details#x"), True)
        assert not result.ok
        assert message in result.message


def test_identity_missing_closed_iframe_and_drift_fail_closed():
    d, page, _loc = _driver(FakeLocator(None, open_state=False))
    ident = d.inspect_disclosure("details#x")
    for key, message in (
        ("browser_session_id", "SESSION_ID_DRIFT"),
        ("page_id", "PAGE_ID_DRIFT"),
        ("metadata_sha256", "ELEMENT_IDENTITY_DRIFT"),
    ):
        bad = dict(ident)
        bad[key] = ""
        result = _set(d, bad, True)
        assert not result.ok
        assert message in result.message
    page._closed = True
    assert "PAGE_CLOSED" in _set(d, ident, True).message
    page._closed = False
    bad = dict(ident)
    bad["main_frame"] = False
    assert not _set(d, bad, True).ok


def test_popup_new_page_download_navigation_fail_closed():
    for event, message in (
        ("popup", "UNEXPECTED_POPUP"),
        ("page", "UNEXPECTED_NEW_PAGE"),
        ("download", "UNEXPECTED_DOWNLOAD"),
    ):
        d, page, _loc = _driver(FakeLocator(None, open_state=False))
        ident = d.inspect_disclosure("details#x")
        page.event_to_fire = event
        result = _set(d, ident, True)
        assert not result.ok
        assert message in result.message
    d, page, _loc = _driver(FakeLocator(None, open_state=False))
    ident = d.inspect_disclosure("details#x")
    page.navigate_on_click = True
    result = _set(d, ident, True)
    assert not result.ok
    assert "UNEXPECTED_NAVIGATION" in result.message


def test_no_generic_click_public_surface_added():
    assert "browser.click" in BrowserBackend._supported
    assert "browser.set_disclosure" in BrowserBackend._supported
    assert not hasattr(PlaywrightDriver, "evaluate")
    assert not hasattr(PlaywrightDriver, "js_eval")
