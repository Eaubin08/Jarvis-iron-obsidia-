"""Optional Playwright implementation of the BrowserDriver protocol.

Import is lazy: the Jarvis core remains importable without Playwright installed.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlaywrightDriver:
    headless: bool = False
    _pw: Any = field(default=None, init=False, repr=False)
    _browser: Any = field(default=None, init=False, repr=False)
    _page: Any = field(default=None, init=False, repr=False)
    _browser_session_id: str = field(default="", init=False, repr=False)
    _page_id: str = field(default="", init=False, repr=False)

    def _ensure_page(self):
        if self._page is not None:
            return self._page
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed; install the browser optional dependency"
            ) from exc
        if self._pw is None:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=self.headless)
            self._browser_session_id = str(uuid.uuid4())
        self._page = self._browser.new_page()
        self._page_id = str(uuid.uuid4())
        return self._page

    @staticmethod
    def _page_origin(url: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return url
        return f"{parsed.scheme}://{parsed.netloc}"

    def _identity_fields(self, page) -> dict:
        return {
            "browser_session_id": self._browser_session_id,
            "page_id": self._page_id,
            "origin": self._page_origin(page.url),
            "closed": bool(page.is_closed()),
        }

    def navigate(self, url: str) -> dict:
        page = self._ensure_page()
        response = page.goto(url, wait_until="domcontentloaded")
        result = {"url": page.url, "status": response.status if response else None, "title": page.title()}
        result.update(self._identity_fields(page))
        return result

    def read(self, selector: str | None = None) -> dict:
        page = self._ensure_page()
        if selector:
            locator = page.locator(selector)
            element_count = locator.count()
            text = locator.first.inner_text() if element_count > 0 else ""
            result = {"url": page.url, "selector": selector,
                      "element_count": element_count, "text": text}
            result.update(self._identity_fields(page))
            return result
        result = {"url": page.url, "title": page.title(), "text": page.locator("body").inner_text()}
        result.update(self._identity_fields(page))
        return result

    def click(self, selector: str) -> dict:
        page = self._ensure_page()
        page.locator(selector).first.click()
        return {"url": page.url, "selector": selector}

    def fill(self, selector: str, value: str) -> dict:
        page = self._ensure_page()
        page.locator(selector).first.fill(value)
        return {"url": page.url, "selector": selector}

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._pw is not None:
            self._pw.stop()
        self._page = self._browser = self._pw = None
