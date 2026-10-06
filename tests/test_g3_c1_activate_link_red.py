from __future__ import annotations

from jarvis.browser import BrowserBackend
from jarvis.contracts import ActionRequest
from jarvis.integrations.playwright_driver import PlaywrightDriver


SID = "sess-aaaaaaaaaaaaaaaaaaaaaaaaaaaa"
PID = "page-bbbbbbbbbbbbbbbbbbbbbbbb"
PRE_URL = "https://example.com/start"
DEST_URL = "https://example.com/dest"


class FakeLocator:
    def __init__(
        self,
        page,
        selector,
        *,
        count=1,
        text="Destination",
        href="/dest",
        visible=True,
        enabled=True,
        role="link",
        name="",
        aria_label="",
    ):
        self.page = page
        self.selector = selector
        self._count = count
        self._text = text
        self._href = href
        self._visible = visible
        self._enabled = enabled
        self._role = role
        self._name = name
        self._aria_label = aria_label
        self.first = self

    def count(self):
        return self._count

    def inner_text(self):
        return self._text

    def get_attribute(self, name):
        return {
            "href": self._href,
            "role": self._role,
            "name": self._name,
            "aria-label": self._aria_label,
            "data-tag-name": "a",
        }.get(name)

    def is_visible(self):
        return self._visible

    def is_enabled(self):
        return self._enabled

    def aria_snapshot(self):
        return '- link "Destination"'

    def click(self):
        if self.page.event_to_fire:
            self.page.fire(self.page.event_to_fire)
        else:
            self.page._url = self.page.post_url


class FakeContext:
    def __init__(self):
        self.handlers = {}

    def on(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)

    def fire(self, event):
        for handler in self.handlers.get(event, []):
            handler(object())


class FakePage:
    def __init__(self, *, count=1, href="/dest", visible=True, enabled=True):
        self._url = PRE_URL
        self.post_url = DEST_URL
        self._closed = False
        self.event_to_fire = ""
        self.context = FakeContext()
        self.locator_obj = FakeLocator(
            self, "a#go", count=count, href=href, visible=visible, enabled=enabled
        )
        self.handlers = {}

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


def _driver(page):
    d = PlaywrightDriver()
    d._page = page
    d._browser_session_id = SID
    d._page_id = PID
    return d


def _identity(driver):
    return driver.inspect_element("a#go")


def test_inspect_requires_exact_selector_count():
    d = _driver(FakePage(count=1))
    assert d.inspect_element("a#go")["element_count"] == 1
    assert d.inspect_element("a#go")["browser_session_id"] == SID
    assert d.inspect_element("a#go")["page_id"] == PID


def test_zero_match_rejected_by_activation():
    page = FakePage(count=1)
    d = _driver(page)
    ident = _identity(d)
    page.locator_obj._count = 0
    result = BrowserBackend(d).execute(ActionRequest("browser.activate_link", ident))
    assert not result.ok
    assert "SELECTOR_COUNT_DRIFT" in result.message


def test_multiple_match_rejected_by_activation():
    page = FakePage(count=1)
    d = _driver(page)
    ident = _identity(d)
    page.locator_obj._count = 2
    result = BrowserBackend(d).execute(ActionRequest("browser.activate_link", ident))
    assert not result.ok
    assert "SELECTOR_COUNT_DRIFT" in result.message


def test_invisible_link_rejected():
    d = _driver(FakePage(visible=False))
    ident = _identity(d)
    result = BrowserBackend(d).execute(ActionRequest("browser.activate_link", ident))
    assert not result.ok
    assert "ELEMENT_NOT_VISIBLE" in result.message


def test_disabled_link_rejected():
    d = _driver(FakePage(enabled=False))
    ident = _identity(d)
    result = BrowserBackend(d).execute(ActionRequest("browser.activate_link", ident))
    assert not result.ok
    assert "ELEMENT_NOT_ENABLED" in result.message


def test_href_required_and_blocked_schemes_rejected():
    for href in ("", "javascript:alert(1)", "data:text/plain,x", "file:///tmp/x", "mailto:x@y", "tel:123"):
        d = _driver(FakePage(href=href))
        ident = _identity(d)
        result = BrowserBackend(d).execute(ActionRequest("browser.activate_link", ident))
        assert not result.ok


def test_same_page_navigation_returns_final_url_and_identity():
    d = _driver(FakePage())
    ident = _identity(d)
    result = BrowserBackend(d).execute(ActionRequest("browser.activate_link", ident))
    assert result.ok
    assert result.data["final_url"] == DEST_URL
    assert result.data["browser_session_id"] == SID
    assert result.data["page_id"] == PID
    assert result.data["proof_strength"] == "STRONG"


def test_unexpected_popup_new_page_and_download_fail_closed():
    for event, message in (
        ("popup", "UNEXPECTED_POPUP"),
        ("page", "UNEXPECTED_NEW_PAGE"),
        ("download", "UNEXPECTED_DOWNLOAD"),
    ):
        page = FakePage()
        page.event_to_fire = event
        d = _driver(page)
        ident = _identity(d)
        result = BrowserBackend(d).execute(ActionRequest("browser.activate_link", ident))
        assert not result.ok
        assert message in result.message


def test_unexpected_page_replacement_fail_closed():
    d = _driver(FakePage())
    ident = _identity(d)
    d._page_id = "page-changed"
    result = BrowserBackend(d).execute(ActionRequest("browser.activate_link", ident))
    assert not result.ok
    assert "PAGE_ID_DRIFT" in result.message


def test_redirect_mismatch_fail_closed():
    page = FakePage()
    page.post_url = "https://example.com/elsewhere"
    d = _driver(page)
    ident = _identity(d)
    result = BrowserBackend(d).execute(ActionRequest("browser.activate_link", ident))
    assert not result.ok
    assert "REALIZED_STATE_MISMATCH" in result.message


def test_no_evaluate_route_added():
    assert not hasattr(PlaywrightDriver, "evaluate")
    assert not hasattr(PlaywrightDriver, "js_eval")
