"""Optional Playwright implementation of the BrowserDriver protocol.

Import is lazy: the Jarvis core remains importable without Playwright installed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlaywrightDriver:
    headless: bool = False
    _pw: Any = field(default=None, init=False, repr=False)
    _browser: Any = field(default=None, init=False, repr=False)
    _page: Any = field(default=None, init=False, repr=False)

    def _ensure_page(self):
        if self._page is not None:
            return self._page
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed; install the browser optional dependency"
            ) from exc
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()
        return self._page

    def navigate(self, url: str) -> dict:
        page = self._ensure_page()
        response = page.goto(url, wait_until="domcontentloaded")
        return {"url": page.url, "status": response.status if response else None, "title": page.title()}

    def read(self, selector: str | None = None) -> dict:
        page = self._ensure_page()
        if selector:
            locator = page.locator(selector).first
            return {"url": page.url, "selector": selector, "text": locator.inner_text()}
        return {"url": page.url, "title": page.title(), "text": page.locator("body").inner_text()}

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
