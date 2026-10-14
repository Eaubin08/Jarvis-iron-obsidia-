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


class FakeLocator:
    def __init__(
        self,
        page,
        *,
        count=1,
        tag_name="input",
        input_type="radio",
        role="",
        name="plan",
        element_id="pro",
        form_owner="f1",
        checked=False,
        visible=True,
        enabled=True,
    ):
        self.page = page
        self._count = count
        self.tag_name = tag_name
        self.input_type = input_type
        self.role = role
        self.name = name
        self.element_id = element_id
        self.form_owner = form_owner
        self.checked = checked
        self.visible = visible
        self.enabled = enabled
        self.checks = 0
        self.first = self

    def count(self):
        return self._count

    def get_attribute(self, name):
        if name == "data-tag-name":
            return self.tag_name
        if name == "type":
            return self.input_type
        if name == "role":
            return self.role
        if name == "name":
            return self.name
        if name == "id":
            return self.element_id
        if name == "form":
            return self.form_owner
        return None

    def is_checked(self):
        return self.checked

    def is_visible(self):
        return self.visible

    def is_enabled(self):
        return self.enabled

    def check(self):
        self.checks += 1
        if self.page.event_to_fire:
            self.page.fire(self.page.event_to_fire)
            return
        if self.page.navigate_on_check:
            self.page._url = "https://example.com/other"
        self.checked = True


class FakePage:
    def __init__(self, locator):
        self._url = URL
        self._closed = False
        self.context = FakeContext()
        self.handlers = {}
        self.locator_obj = locator
        self.event_to_fire = ""
        self.navigate_on_check = False
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


def _select(driver, identity):
    return BrowserBackend(driver).execute(ActionRequest("browser.select_radio", dict(identity)))


def test_unchecked_to_selected_once_and_noop():
    d, _page, loc = _driver(FakeLocator(None, checked=False))
    result = _select(d, d.inspect_radio("input#pro"))
    assert result.ok
    assert result.data["checked"] is True
    assert result.data["mutation_performed"] is True
    assert loc.checks == 1

    result = _select(d, d.inspect_radio("input#pro"))
    assert result.ok
    assert result.data["mutation_performed"] is False
    assert loc.checks == 1


def test_exact_count_type_visibility_enabled_rejections():
    cases = [
        (FakeLocator(None, count=0), "SELECTOR_COUNT_DRIFT"),
        (FakeLocator(None, count=2), "SELECTOR_COUNT_DRIFT"),
        (FakeLocator(None, tag_name="button"), "UNSUPPORTED_RADIO_TARGET"),
        (FakeLocator(None, input_type="checkbox"), "UNSUPPORTED_RADIO_TARGET"),
        (FakeLocator(None, visible=False), "ELEMENT_NOT_VISIBLE"),
        (FakeLocator(None, enabled=False), "ELEMENT_NOT_ENABLED"),
    ]
    for loc, message in cases:
        d, _page, _loc = _driver(loc)
        result = _select(d, d.inspect_radio("input#pro"))
        assert not result.ok
        assert message in result.message


def test_missing_identity_iframe_closed_and_group_rejections():
    d, page, _loc = _driver(FakeLocator(None, checked=False))
    ident = d.inspect_radio("input#pro")
    for key, message in (
        ("browser_session_id", "SESSION_ID_DRIFT"),
        ("page_id", "PAGE_ID_DRIFT"),
        ("metadata_sha256", "ELEMENT_IDENTITY_DRIFT"),
        ("radio_group_identity", "RADIO_GROUP_DRIFT"),
    ):
        bad = dict(ident)
        bad[key] = ""
        result = _select(d, bad)
        assert not result.ok
        assert message in result.message

    page._closed = True
    assert "PAGE_CLOSED" in _select(d, ident).message
    page._closed = False
    bad = dict(ident)
    bad["main_frame"] = False
    assert "IFRAME_UNSUPPORTED" in _select(d, bad).message

    d2, _page2, _loc2 = _driver(FakeLocator(None, name=""))
    assert "RADIO_GROUP_IDENTITY_INVALID" in _select(d2, d2.inspect_radio("input#pro")).message


def test_drift_and_post_mismatch_rejections():
    d, _page, loc = _driver(FakeLocator(None, checked=False))
    ident = d.inspect_radio("input#pro")
    loc.checked = True
    result = _select(d, ident)
    assert not result.ok
    assert "PRE_CHECKED_DRIFT" in result.message

    d, _page, loc = _driver(FakeLocator(None, checked=False))
    ident = d.inspect_radio("input#pro")
    loc.check = lambda: setattr(loc, "checks", loc.checks + 1)
    result = _select(d, ident)
    assert not result.ok
    assert "REALIZED_STATE_MISMATCH" in result.message

    d, _page, loc = _driver(FakeLocator(None, checked=False))
    ident = d.inspect_radio("input#pro")
    original = loc.check

    def drifting_check():
        original()
        loc.name = "changed"

    loc.check = drifting_check
    result = _select(d, ident)
    assert not result.ok
    assert "RADIO_GROUP_DRIFT" in result.message or "POST_ELEMENT_IDENTITY_DRIFT" in result.message


def test_popup_new_page_download_navigation_fail_closed():
    for event, message in (
        ("popup", "UNEXPECTED_POPUP"),
        ("page", "UNEXPECTED_NEW_PAGE"),
        ("download", "UNEXPECTED_DOWNLOAD"),
    ):
        d, page, _loc = _driver(FakeLocator(None, checked=False))
        ident = d.inspect_radio("input#pro")
        page.event_to_fire = event
        result = _select(d, ident)
        assert not result.ok
        assert message in result.message
    d, page, _loc = _driver(FakeLocator(None, checked=False))
    ident = d.inspect_radio("input#pro")
    page.navigate_on_check = True
    result = _select(d, ident)
    assert not result.ok
    assert "UNEXPECTED_NAVIGATION" in result.message


def test_no_generic_click_or_false_public_surface_added():
    assert "browser.click" in BrowserBackend._supported
    assert "browser.select_radio" in BrowserBackend._supported
    assert "browser.set_radio" not in BrowserBackend._supported
    assert not hasattr(PlaywrightDriver, "evaluate")
    assert not hasattr(PlaywrightDriver, "js_eval")
