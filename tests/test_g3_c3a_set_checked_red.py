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
        input_type="checkbox",
        role="",
        name="agree",
        element_id="agree",
        form_owner="f1",
        checked=False,
        indeterminate_status="FALSE_PROVEN",
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
        self.indeterminate_status = indeterminate_status
        self.visible = visible
        self.enabled = enabled
        self.sets = []
        self.first = self

    def count(self):
        return self._count

    def inner_text(self):
        return ""

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

    def aria_snapshot(self):
        if self.indeterminate_status == "TRUE_PROVEN":
            return "- checkbox \"Agree\" [checked=mixed]"
        if self.indeterminate_status == "FALSE_PROVEN":
            return "- checkbox \"Agree\" [checked=false]"
        return "- checkbox \"Agree\""

    def set_checked(self, value):
        self.sets.append(value)
        if self.page.event_to_fire:
            self.page.fire(self.page.event_to_fire)
            return
        if self.page.navigate_on_set:
            self.page._url = "https://example.com/other"
        self.checked = value


class FakePage:
    def __init__(self, locator):
        self._url = URL
        self._closed = False
        self.context = FakeContext()
        self.handlers = {}
        self.locator_obj = locator
        self.event_to_fire = ""
        self.navigate_on_set = False
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
    args["target_checked"] = target
    return BrowserBackend(driver).execute(ActionRequest("browser.set_checked", args))


def test_false_to_true_and_true_to_false_exactly_once():
    d, _page, loc = _driver(FakeLocator(None, checked=False))
    ident = d.inspect_checkbox("input#agree")
    result = _set(d, ident, True)
    assert result.ok
    assert result.data["checked"] is True
    assert result.data["mutation_performed"] is True
    assert loc.sets == [True]

    ident = d.inspect_checkbox("input#agree")
    result = _set(d, ident, False)
    assert result.ok
    assert result.data["checked"] is False
    assert loc.sets == [True, False]


def test_noop_is_verified_without_physical_set():
    d, _page, loc = _driver(FakeLocator(None, checked=True))
    result = _set(d, d.inspect_checkbox("input#agree"), True)
    assert result.ok
    assert result.data["mutation_performed"] is False
    assert loc.sets == []


def test_exact_count_and_type_rejections():
    cases = [
        (FakeLocator(None, count=0), "SELECTOR_COUNT_DRIFT"),
        (FakeLocator(None, count=2), "SELECTOR_COUNT_DRIFT"),
        (FakeLocator(None, tag_name="button"), "UNSUPPORTED_CHECKBOX_TARGET"),
        (FakeLocator(None, input_type="radio"), "UNSUPPORTED_CHECKBOX_TARGET"),
    ]
    for loc, message in cases:
        d, _page, _loc = _driver(loc)
        result = _set(d, d.inspect_checkbox("input#agree"), True)
        assert not result.ok
        assert message in result.message


def test_visibility_enabled_identity_closed_iframe_rejections():
    d, page, _loc = _driver(FakeLocator(None, checked=False))
    ident = d.inspect_checkbox("input#agree")
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

    for loc, message in (
        (FakeLocator(None, visible=False), "ELEMENT_NOT_VISIBLE"),
        (FakeLocator(None, enabled=False), "ELEMENT_NOT_ENABLED"),
    ):
        d2, _page2, _loc2 = _driver(loc)
        result = _set(d2, d2.inspect_checkbox("input#agree"), True)
        assert not result.ok
        assert message in result.message

    page._closed = True
    assert "PAGE_CLOSED" in _set(d, ident, True).message
    page._closed = False
    bad = dict(ident)
    bad["main_frame"] = False
    assert "IFRAME_UNSUPPORTED" in _set(d, bad, True).message


def test_indeterminate_true_or_unknown_rejects():
    for status in ("TRUE_PROVEN", "UNKNOWN"):
        d, _page, _loc = _driver(FakeLocator(None, indeterminate_status=status))
        result = _set(d, d.inspect_checkbox("input#agree"), True)
        assert not result.ok
        assert "INDETERMINATE_STATE_UNPROVABLE" in result.message


def test_post_state_mismatch_rejects():
    d, _page, loc = _driver(FakeLocator(None, checked=False))
    ident = d.inspect_checkbox("input#agree")
    loc.set_checked = lambda value: loc.sets.append(value)
    result = _set(d, ident, True)
    assert not result.ok
    assert "REALIZED_STATE_MISMATCH" in result.message


def test_popup_new_page_download_navigation_fail_closed():
    for event, message in (
        ("popup", "UNEXPECTED_POPUP"),
        ("page", "UNEXPECTED_NEW_PAGE"),
        ("download", "UNEXPECTED_DOWNLOAD"),
    ):
        d, page, _loc = _driver(FakeLocator(None, checked=False))
        ident = d.inspect_checkbox("input#agree")
        page.event_to_fire = event
        result = _set(d, ident, True)
        assert not result.ok
        assert message in result.message
    d, page, _loc = _driver(FakeLocator(None, checked=False))
    ident = d.inspect_checkbox("input#agree")
    page.navigate_on_set = True
    result = _set(d, ident, True)
    assert not result.ok
    assert "UNEXPECTED_NAVIGATION" in result.message


def test_pre_checked_drift_and_post_identity_drift_reject():
    d, _page, loc = _driver(FakeLocator(None, checked=False))
    ident = d.inspect_checkbox("input#agree")
    loc.checked = True
    result = _set(d, ident, True)
    assert not result.ok
    assert "PRE_CHECKED_DRIFT" in result.message

    d, _page, loc = _driver(FakeLocator(None, checked=False))
    ident = d.inspect_checkbox("input#agree")
    original = loc.set_checked

    def drifting_set(value):
        original(value)
        loc.name = "changed"

    loc.set_checked = drifting_set
    result = _set(d, ident, True)
    assert not result.ok
    assert "POST_ELEMENT_IDENTITY_DRIFT" in result.message


def test_no_generic_click_public_surface_added():
    assert "browser.click" in BrowserBackend._supported
    assert "browser.set_checked" in BrowserBackend._supported
    assert not hasattr(PlaywrightDriver, "evaluate")
    assert not hasattr(PlaywrightDriver, "js_eval")
