"""G3-A1: stable page/session identity for PlaywrightDriver.

Identity is assigned by the wrapper at object creation and never derives from URL.
All tests use deterministic mocks -- no real browser launched.
"""
from __future__ import annotations
import uuid
from unittest.mock import MagicMock, patch

import pytest

from jarvis.integrations.playwright_driver import PlaywrightDriver


# __ fake page ________________________________________________________________

class FakePage:
    def __init__(self, url="https://example.com"):
        self._url = url
        self._closed = False

    @property
    def url(self):
        return self._url

    def title(self):
        return "FakeTitle"

    def is_closed(self):
        return self._closed

    def goto(self, url, wait_until=None):
        self._url = url
        r = MagicMock()
        r.status = 200
        return r

    def locator(self, selector):
        loc = MagicMock()
        loc.inner_text.return_value = "body text"
        loc.first = loc
        return loc


def _inject_page(driver, fake_page):
    """Inject a fake page via a patched Playwright launch stack."""
    driver._page = None
    driver._pw = None
    driver._browser = None
    fake_browser = MagicMock()
    fake_browser.new_page.return_value = fake_page
    fake_pw_ctx = MagicMock()
    fake_pw_ctx.chromium.launch.return_value = fake_browser
    fake_pw_instance = MagicMock()
    fake_pw_instance.start.return_value = fake_pw_ctx
    fake_pw_start = MagicMock(return_value=fake_pw_instance)
    with patch("playwright.sync_api.sync_playwright", fake_pw_start):
        driver._ensure_page()

# __ A / B / C. IDs exist and are strings _____________________________________

def test_driver_has_browser_session_id():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    assert hasattr(d, "_browser_session_id")


def test_driver_has_page_id():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    assert hasattr(d, "_page_id")


def test_both_ids_are_strings():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    assert isinstance(d._browser_session_id, str)
    assert isinstance(d._page_id, str)


def test_ids_are_valid_uuid4_format():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    uuid.UUID(d._browser_session_id)
    uuid.UUID(d._page_id)


# __ D. browser_session_id stable across reads ________________________________

def test_browser_session_id_stable_across_reads():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    sid1 = d._browser_session_id
    d.read()
    d.read()
    assert d._browser_session_id == sid1


# __ E. page_id stable across reads ___________________________________________

def test_page_id_stable_across_reads():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    pid1 = d._page_id
    d.read()
    d.read()
    assert d._page_id == pid1


# __ F. page_id stable across navigation ______________________________________

def test_page_id_stable_across_navigation():
    d = PlaywrightDriver()
    _inject_page(d, FakePage("https://example.com"))
    pid1 = d._page_id
    d.navigate("https://example.com/other")
    assert d._page_id == pid1


# __ G. page_id stable across reload (same Page object) ______________________

def test_page_id_stable_across_reload():
    d = PlaywrightDriver()
    _inject_page(d, FakePage("https://example.com"))
    pid1 = d._page_id
    d.navigate("https://example.com")
    assert d._page_id == pid1


# __ H. URL changes but page_id remains stable ________________________________

def test_url_changes_but_page_id_stable():
    d = PlaywrightDriver()
    page = FakePage("https://a.example.com")
    _inject_page(d, page)
    pid1 = d._page_id
    d.navigate("https://b.example.com")
    assert d._page_id == pid1
    assert page.url != "https://a.example.com"


# __ I. page_id != URL ________________________________________________________

def test_page_id_is_not_url():
    d = PlaywrightDriver()
    _inject_page(d, FakePage("https://example.com"))
    assert d._page_id != "https://example.com"
    assert not d._page_id.startswith("http")


# __ J. IDs immutable during lifetime _________________________________________

def test_ids_immutable_during_lifetime():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    sid = d._browser_session_id
    pid = d._page_id
    for _ in range(3):
        d.read()
    d.navigate("https://other.com")
    assert d._browser_session_id == sid
    assert d._page_id == pid

# __ K. new driver gets new browser_session_id ________________________________

def test_new_driver_gets_new_browser_session_id():
    d1 = PlaywrightDriver()
    _inject_page(d1, FakePage())
    d2 = PlaywrightDriver()
    _inject_page(d2, FakePage())
    assert d1._browser_session_id != d2._browser_session_id


# __ L. new physical page gets new page_id ____________________________________

def test_new_physical_page_gets_new_page_id():
    d = PlaywrightDriver()
    _inject_page(d, FakePage("https://p1.com"))
    pid1 = d._page_id
    d._page._closed = True
    d._page = None
    _inject_page(d, FakePage("https://p2.com"))
    assert d._page_id != pid1


# __ M. closed state readable _________________________________________________

def test_closed_state_readable_open():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    assert d.read().get("closed") is False


def test_closed_state_readable_closed():
    d = PlaywrightDriver()
    page = FakePage()
    _inject_page(d, page)
    page._closed = True
    assert d.read().get("closed") is True


# __ N. read output exposes identity __________________________________________

def test_read_output_contains_browser_session_id():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    r = d.read()
    assert "browser_session_id" in r and isinstance(r["browser_session_id"], str)


def test_read_output_contains_page_id():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    r = d.read()
    assert "page_id" in r and isinstance(r["page_id"], str)


def test_read_output_contains_origin():
    d = PlaywrightDriver()
    _inject_page(d, FakePage("https://example.com/path?q=1"))
    assert d.read().get("origin") == "https://example.com"


def test_read_output_origin_preserves_non_default_port():
    d = PlaywrightDriver()
    _inject_page(d, FakePage("https://sub.domain.com:8443/deep/path"))
    assert d.read().get("origin") == "https://sub.domain.com:8443"


def test_read_output_identity_matches_driver_ids():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    r = d.read()
    assert r["browser_session_id"] == d._browser_session_id
    assert r["page_id"] == d._page_id


def test_selector_read_output_contains_identity():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    r = d.read(selector="body p")
    assert "browser_session_id" in r
    assert "page_id" in r
    assert "origin" in r
    assert "closed" in r


# __ O. navigate output exposes identity ______________________________________

def test_navigate_output_contains_browser_session_id():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    r = d.navigate("https://example.com/target")
    assert "browser_session_id" in r and isinstance(r["browser_session_id"], str)


def test_navigate_output_contains_page_id():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    r = d.navigate("https://example.com/target")
    assert "page_id" in r and isinstance(r["page_id"], str)


def test_navigate_output_contains_origin():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    r = d.navigate("https://example.com/target")
    assert r.get("origin") == "https://example.com"


def test_navigate_output_contains_closed():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    r = d.navigate("https://example.com/target")
    assert "closed" in r and r["closed"] is False


def test_navigate_ids_consistent_with_driver():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    r = d.navigate("https://example.com")
    assert r["page_id"] == d._page_id
    assert r["browser_session_id"] == d._browser_session_id


# __ P. no evaluate/new mutation surface added ________________________________

def test_no_evaluate_on_driver():
    import inspect
    public = {n for n, _ in inspect.getmembers(PlaywrightDriver, inspect.isfunction)
              if not n.startswith("_")}
    for forbidden in ("evaluate", "js_eval", "execute_script"):
        assert forbidden not in public


# __ origin edge cases ________________________________________________________

def test_origin_http_no_port():
    d = PlaywrightDriver()
    _inject_page(d, FakePage("http://example.com/path"))
    assert d.read().get("origin") == "http://example.com"


def test_origin_preserves_non_default_http_port():
    d = PlaywrightDriver()
    _inject_page(d, FakePage("http://localhost:8080/page"))
    assert d.read().get("origin") == "http://localhost:8080"


def test_origin_about_blank_does_not_crash():
    d = PlaywrightDriver()
    _inject_page(d, FakePage("about:blank"))
    r = d.read()
    assert "origin" in r


# __ backward compat __________________________________________________________

def test_read_still_returns_url_title_text():
    d = PlaywrightDriver()
    _inject_page(d, FakePage("https://example.com"))
    r = d.read()
    assert "url" in r and "title" in r and "text" in r


def test_navigate_still_returns_url_status_title():
    d = PlaywrightDriver()
    _inject_page(d, FakePage())
    r = d.navigate("https://example.com")
    assert "url" in r and "status" in r and "title" in r
