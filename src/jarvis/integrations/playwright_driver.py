"""Optional Playwright implementation of the BrowserDriver protocol.

Import is lazy: the Jarvis core remains importable without Playwright installed.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse


_BLOCKED_LINK_SCHEMES = {"javascript", "data", "file", "mailto", "tel"}


def _canonical_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"}:
        netloc = parsed.netloc
        if parsed.scheme == "https" and netloc.endswith(":443"):
            netloc = netloc[:-4]
        if parsed.scheme == "http" and netloc.endswith(":80"):
            netloc = netloc[:-3]
        return urlunparse(parsed._replace(scheme=parsed.scheme.lower(), netloc=netloc.lower()))
    return url


def _scheme(url: str) -> str:
    return urlparse(url).scheme.lower()


def _bool_attr(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = str(value).strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None


def _indeterminate_status_from_snapshot(snapshot: str) -> str:
    normalized = " ".join(str(snapshot or "").lower().replace('"', " ").replace("'", " ").split())
    if "mixed" in normalized or "indeterminate" in normalized:
        return "TRUE_PROVEN"
    false_markers = (
        "checked: false",
        "checked=false",
        "[checked=false]",
        "checked false",
        "checked: off",
        "checked=off",
        "not checked",
        "unchecked",
    )
    true_markers = (
        "checked: true",
        "checked=true",
        "[checked]",
        "checked true",
        "checked: on",
        "checked=on",
    )
    if any(marker in normalized for marker in false_markers):
        return "FALSE_PROVEN"
    if any(marker in normalized for marker in true_markers):
        return "FALSE_PROVEN"
    return "UNKNOWN"


def _radio_group_identity(browser_session_id: str, page_id: str, name: str, form_owner: str) -> str:
    payload = "|".join([
        "RADIO_GROUP_IDENTITY_V1",
        browser_session_id,
        page_id,
        "main_frame",
        "radio",
        name,
        form_owner,
    ])
    return hashlib.sha256(payload.encode()).hexdigest()


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

    def inspect_element(self, selector: str) -> dict:
        page = self._ensure_page()
        locator = page.locator(selector)
        element_count = locator.count()
        result = {"url": page.url, "selector": selector, "element_count": element_count}
        result.update(self._identity_fields(page))
        if element_count != 1:
            return result

        item = locator.first
        text = item.inner_text()
        href = item.get_attribute("href") or ""
        resolved_href = urljoin(page.url, href) if href else ""
        role = item.get_attribute("role") or ""
        name = item.get_attribute("name") or ""
        aria_label = item.get_attribute("aria-label") or ""
        tag_name = item.get_attribute("data-tag-name") or ""
        if not tag_name and hasattr(item, "aria_snapshot"):
            try:
                snapshot = item.aria_snapshot() or ""
            except Exception:
                snapshot = ""
            if "link" in str(snapshot).lower():
                role = role or "link"
        result.update({
            "visible": bool(item.is_visible()),
            "enabled": bool(item.is_enabled()),
            "tag_name": tag_name.lower(),
            "role": role.lower(),
            "href": href,
            "resolved_href": _canonical_url(resolved_href) if resolved_href else "",
            "name": name,
            "aria_label": aria_label,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "metadata_sha256": hashlib.sha256(
                "|".join([selector, href, resolved_href, role, name, aria_label, text]).encode()
            ).hexdigest(),
            "main_frame": True,
            "link_class": "href_link" if href else "",
        })
        return result

    def activate_link_by_identity(self, identity: dict) -> dict:
        page = self._ensure_page()
        selector = str(identity.get("selector") or "").strip()
        expected_href = str(identity.get("href") or "")
        expected_resolved = _canonical_url(str(identity.get("resolved_href") or ""))
        if not selector:
            raise ValueError("missing browser argument: selector")
        if not expected_resolved:
            raise ValueError("missing browser argument: resolved_href")
        if _scheme(expected_resolved) not in {"http", "https"}:
            raise ValueError("BLOCKED_LINK_SCHEME")

        observed = self.inspect_element(selector)
        if observed.get("browser_session_id") != identity.get("browser_session_id"):
            raise ValueError("SESSION_ID_DRIFT")
        if observed.get("page_id") != identity.get("page_id"):
            raise ValueError("PAGE_ID_DRIFT")
        if _canonical_url(str(observed.get("url") or "")) != _canonical_url(str(identity.get("url") or "")):
            raise ValueError("URL_DRIFT")
        if observed.get("element_count") != 1:
            raise ValueError("SELECTOR_COUNT_DRIFT")
        if observed.get("href") != expected_href:
            raise ValueError("HREF_DRIFT")
        if _canonical_url(str(observed.get("resolved_href") or "")) != expected_resolved:
            raise ValueError("RESOLVED_HREF_DRIFT")
        if observed.get("metadata_sha256") != identity.get("metadata_sha256"):
            raise ValueError("ELEMENT_IDENTITY_DRIFT")
        if observed.get("visible") is not True:
            raise ValueError("ELEMENT_NOT_VISIBLE")
        if observed.get("enabled") is not True:
            raise ValueError("ELEMENT_NOT_ENABLED")
        if observed.get("closed") is True:
            raise ValueError("PAGE_CLOSED")

        events = {"popup": False, "new_page": False, "download": False}

        def _mark(name):
            def _handler(*_args):
                events[name] = True
            return _handler

        popup_handler = _mark("popup")
        page_handler = _mark("new_page")
        download_handler = _mark("download")
        if hasattr(page, "on"):
            page.on("popup", popup_handler)
            page.on("download", download_handler)
        context = getattr(page, "context", None)
        if context is not None and hasattr(context, "on"):
            context.on("page", page_handler)

        page.locator(selector).first.click()

        if events["popup"]:
            raise ValueError("UNEXPECTED_POPUP")
        if events["new_page"]:
            raise ValueError("UNEXPECTED_NEW_PAGE")
        if events["download"]:
            raise ValueError("UNEXPECTED_DOWNLOAD")

        post = self.read()
        if post.get("browser_session_id") != identity.get("browser_session_id"):
            raise ValueError("POST_SESSION_ID_DRIFT")
        if post.get("page_id") != identity.get("page_id"):
            raise ValueError("POST_PAGE_ID_DRIFT")
        if post.get("closed") is True:
            raise ValueError("POST_PAGE_CLOSED")
        final_url = _canonical_url(str(post.get("url") or ""))
        if final_url != expected_resolved:
            raise ValueError("REALIZED_STATE_MISMATCH")
        return {
            "url": post.get("url"),
            "final_url": final_url,
            "selector": selector,
            "href": expected_href,
            "resolved_href": expected_resolved,
            "browser_session_id": post.get("browser_session_id"),
            "page_id": post.get("page_id"),
            "origin": post.get("origin"),
            "closed": post.get("closed"),
            "popup_detected": events["popup"],
            "new_page_detected": events["new_page"],
            "download_detected": events["download"],
            "proof_strength": "STRONG",
            "realized_state_verified": True,
        }

    def inspect_disclosure(self, selector: str) -> dict:
        page = self._ensure_page()
        locator = page.locator(selector)
        element_count = locator.count()
        result = {"url": page.url, "selector": selector, "element_count": element_count}
        result.update(self._identity_fields(page))
        if element_count != 1:
            return result

        item = locator.first
        text = item.inner_text()
        role = item.get_attribute("role") or ""
        aria_expanded = item.get_attribute("aria-expanded")
        aria_controls = item.get_attribute("aria-controls") or ""
        open_attr = item.get_attribute("open")
        tag_name = (item.get_attribute("data-tag-name") or "").lower()
        selector_tag = selector.strip().split("#", 1)[0].split(".", 1)[0].lower()
        if not tag_name and selector_tag in {"details", "summary", "button"}:
            tag_name = selector_tag

        disclosure_class = ""
        current_expanded = None
        if tag_name == "details" or open_attr is not None:
            disclosure_class = "DETAILS_OPEN"
            current_expanded = open_attr is not None
        else:
            aria_state = _bool_attr(aria_expanded)
            if aria_state is not None:
                disclosure_class = "ARIA_EXPANDED"
                current_expanded = aria_state

        metadata_payload = "|".join([
            selector,
            tag_name,
            role.lower(),
            aria_controls,
            disclosure_class,
            text,
        ])
        result.update({
            "visible": bool(item.is_visible()),
            "enabled": bool(item.is_enabled()),
            "tag_name": tag_name,
            "role": role.lower(),
            "aria_expanded": aria_expanded,
            "aria_controls": aria_controls,
            "open": open_attr is not None,
            "disclosure_class": disclosure_class,
            "current_expanded": current_expanded,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "metadata_sha256": hashlib.sha256(metadata_payload.encode()).hexdigest(),
            "main_frame": True,
        })
        return result

    def set_disclosure_by_identity(self, identity: dict, target_expanded: bool) -> dict:
        page = self._ensure_page()
        selector = str(identity.get("selector") or "").strip()
        if not selector:
            raise ValueError("missing browser argument: selector")

        observed = self.inspect_disclosure(selector)
        for key, error in (
            ("browser_session_id", "SESSION_ID_DRIFT"),
            ("page_id", "PAGE_ID_DRIFT"),
            ("url", "URL_DRIFT"),
            ("origin", "ORIGIN_DRIFT"),
            ("disclosure_class", "DISCLOSURE_CLASS_DRIFT"),
            ("metadata_sha256", "ELEMENT_IDENTITY_DRIFT"),
        ):
            if str(observed.get(key) or "") != str(identity.get(key) or ""):
                raise ValueError(error)
        if observed.get("element_count") != 1:
            raise ValueError("SELECTOR_COUNT_DRIFT")
        if observed.get("current_expanded") is not identity.get("current_expanded"):
            raise ValueError("PRE_STATE_DRIFT")
        if observed.get("aria_controls") != identity.get("aria_controls"):
            raise ValueError("ARIA_CONTROLS_DRIFT")
        if observed.get("visible") is not True:
            raise ValueError("ELEMENT_NOT_VISIBLE")
        if observed.get("enabled") is not True:
            raise ValueError("ELEMENT_NOT_ENABLED")
        if observed.get("closed") is True:
            raise ValueError("PAGE_CLOSED")
        if identity.get("main_frame") is not True:
            raise ValueError("IFRAME_UNSUPPORTED")
        if observed.get("main_frame") is False:
            raise ValueError("IFRAME_UNSUPPORTED")
        if observed.get("disclosure_class") not in {"DETAILS_OPEN", "ARIA_EXPANDED"}:
            raise ValueError("UNSUPPORTED_DISCLOSURE_CLASS")

        events = {"popup": False, "new_page": False, "download": False}

        def _mark(name):
            def _handler(*_args):
                events[name] = True
            return _handler

        if observed.get("current_expanded") is target_expanded:
            post = self.inspect_disclosure(selector)
            mutation_performed = False
        else:
            if hasattr(page, "on"):
                page.on("popup", _mark("popup"))
                page.on("download", _mark("download"))
            context = getattr(page, "context", None)
            if context is not None and hasattr(context, "on"):
                context.on("page", _mark("new_page"))
            page.locator(selector).first.click()
            mutation_performed = True
            if events["popup"]:
                raise ValueError("UNEXPECTED_POPUP")
            if events["new_page"]:
                raise ValueError("UNEXPECTED_NEW_PAGE")
            if events["download"]:
                raise ValueError("UNEXPECTED_DOWNLOAD")
            post = self.inspect_disclosure(selector)

        if _canonical_url(str(post.get("url") or "")) != _canonical_url(str(identity.get("url") or "")):
            raise ValueError("UNEXPECTED_NAVIGATION")
        if post.get("browser_session_id") != identity.get("browser_session_id"):
            raise ValueError("POST_SESSION_ID_DRIFT")
        if post.get("page_id") != identity.get("page_id"):
            raise ValueError("POST_PAGE_ID_DRIFT")
        if post.get("metadata_sha256") != identity.get("metadata_sha256"):
            raise ValueError("POST_ELEMENT_IDENTITY_DRIFT")
        if post.get("closed") is True:
            raise ValueError("POST_PAGE_CLOSED")
        if post.get("current_expanded") is not target_expanded:
            raise ValueError("REALIZED_STATE_MISMATCH")
        return {
            "url": post.get("url"),
            "selector": selector,
            "browser_session_id": post.get("browser_session_id"),
            "page_id": post.get("page_id"),
            "origin": post.get("origin"),
            "closed": post.get("closed"),
            "disclosure_class": post.get("disclosure_class"),
            "target_expanded": target_expanded,
            "current_expanded": post.get("current_expanded"),
            "mutation_performed": mutation_performed,
            "popup_detected": events["popup"],
            "new_page_detected": events["new_page"],
            "download_detected": events["download"],
            "navigation_detected": False,
            "proof_strength": "STRONG",
            "realized_state_verified": True,
        }

    def inspect_checkbox(self, selector: str) -> dict:
        page = self._ensure_page()
        locator = page.locator(selector)
        element_count = locator.count()
        result = {"url": page.url, "selector": selector, "element_count": element_count}
        result.update(self._identity_fields(page))
        if element_count != 1:
            return result

        item = locator.first
        tag_name = (item.get_attribute("data-tag-name") or "").lower()
        selector_tag = selector.strip().split("#", 1)[0].split(".", 1)[0].lower()
        if not tag_name and selector_tag in {"input"}:
            tag_name = selector_tag
        input_type = (item.get_attribute("type") or "").lower()
        role = item.get_attribute("role") or ""
        name = item.get_attribute("name") or ""
        element_id = item.get_attribute("id") or ""
        form_owner = item.get_attribute("form") or ""
        checked = item.is_checked()
        snapshot = ""
        indeterminate_status = "UNKNOWN"
        if hasattr(item, "aria_snapshot"):
            try:
                snapshot = item.aria_snapshot() or ""
            except Exception:
                snapshot = ""
            indeterminate_status = _indeterminate_status_from_snapshot(snapshot)

        metadata_payload = "|".join([
            selector,
            tag_name,
            input_type,
            role.lower(),
            name,
            element_id,
            form_owner,
        ])
        result.update({
            "visible": bool(item.is_visible()),
            "enabled": bool(item.is_enabled()),
            "tag_name": tag_name,
            "type": input_type,
            "role": role.lower(),
            "name": name,
            "id": element_id,
            "form_owner": form_owner,
            "checked": bool(checked),
            "indeterminate_status": indeterminate_status,
            "metadata_sha256": hashlib.sha256(metadata_payload.encode()).hexdigest(),
            "main_frame": True,
        })
        return result

    def set_checked_by_identity(self, identity: dict, target_checked: bool) -> dict:
        page = self._ensure_page()
        selector = str(identity.get("selector") or "").strip()
        if not selector:
            raise ValueError("missing browser argument: selector")

        observed = self.inspect_checkbox(selector)
        for key, error in (
            ("browser_session_id", "SESSION_ID_DRIFT"),
            ("page_id", "PAGE_ID_DRIFT"),
            ("url", "URL_DRIFT"),
            ("origin", "ORIGIN_DRIFT"),
            ("tag_name", "TAG_DRIFT"),
            ("type", "TYPE_DRIFT"),
            ("form_owner", "FORM_OWNER_DRIFT"),
            ("metadata_sha256", "ELEMENT_IDENTITY_DRIFT"),
        ):
            if str(observed.get(key) or "") != str(identity.get(key) or ""):
                raise ValueError(error)
        if observed.get("element_count") != 1:
            raise ValueError("SELECTOR_COUNT_DRIFT")
        if observed.get("tag_name") != "input":
            raise ValueError("UNSUPPORTED_CHECKBOX_TARGET")
        if observed.get("type") != "checkbox":
            raise ValueError("UNSUPPORTED_CHECKBOX_TARGET")
        if observed.get("checked") is not identity.get("checked"):
            raise ValueError("PRE_CHECKED_DRIFT")
        if observed.get("indeterminate_status") != "FALSE_PROVEN":
            raise ValueError("INDETERMINATE_STATE_UNPROVABLE")
        if identity.get("indeterminate_status") != "FALSE_PROVEN":
            raise ValueError("INDETERMINATE_STATE_UNPROVABLE")
        if observed.get("visible") is not True:
            raise ValueError("ELEMENT_NOT_VISIBLE")
        if observed.get("enabled") is not True:
            raise ValueError("ELEMENT_NOT_ENABLED")
        if observed.get("closed") is True:
            raise ValueError("PAGE_CLOSED")
        if identity.get("main_frame") is not True:
            raise ValueError("IFRAME_UNSUPPORTED")
        if observed.get("main_frame") is not True:
            raise ValueError("IFRAME_UNSUPPORTED")

        events = {"popup": False, "new_page": False, "download": False}

        def _mark(name):
            def _handler(*_args):
                events[name] = True
            return _handler

        if observed.get("checked") is target_checked:
            post = self.inspect_checkbox(selector)
            mutation_performed = False
        else:
            if hasattr(page, "on"):
                page.on("popup", _mark("popup"))
                page.on("download", _mark("download"))
            context = getattr(page, "context", None)
            if context is not None and hasattr(context, "on"):
                context.on("page", _mark("new_page"))
            page.locator(selector).first.set_checked(target_checked)
            mutation_performed = True
            if events["popup"]:
                raise ValueError("UNEXPECTED_POPUP")
            if events["new_page"]:
                raise ValueError("UNEXPECTED_NEW_PAGE")
            if events["download"]:
                raise ValueError("UNEXPECTED_DOWNLOAD")
            post = self.inspect_checkbox(selector)

        if _canonical_url(str(post.get("url") or "")) != _canonical_url(str(identity.get("url") or "")):
            raise ValueError("UNEXPECTED_NAVIGATION")
        if post.get("browser_session_id") != identity.get("browser_session_id"):
            raise ValueError("POST_SESSION_ID_DRIFT")
        if post.get("page_id") != identity.get("page_id"):
            raise ValueError("POST_PAGE_ID_DRIFT")
        if post.get("metadata_sha256") != identity.get("metadata_sha256"):
            raise ValueError("POST_ELEMENT_IDENTITY_DRIFT")
        if post.get("closed") is True:
            raise ValueError("POST_PAGE_CLOSED")
        if post.get("indeterminate_status") != "FALSE_PROVEN":
            raise ValueError("POST_INDETERMINATE_STATE_UNPROVABLE")
        if post.get("checked") is not target_checked:
            raise ValueError("REALIZED_STATE_MISMATCH")
        return {
            "url": post.get("url"),
            "selector": selector,
            "browser_session_id": post.get("browser_session_id"),
            "page_id": post.get("page_id"),
            "origin": post.get("origin"),
            "closed": post.get("closed"),
            "target_checked": target_checked,
            "checked": post.get("checked"),
            "indeterminate_status": post.get("indeterminate_status"),
            "mutation_performed": mutation_performed,
            "popup_detected": events["popup"],
            "new_page_detected": events["new_page"],
            "download_detected": events["download"],
            "navigation_detected": False,
            "proof_strength": "STRONG",
            "realized_state_verified": True,
        }

    def inspect_radio(self, selector: str) -> dict:
        page = self._ensure_page()
        locator = page.locator(selector)
        element_count = locator.count()
        result = {"url": page.url, "selector": selector, "element_count": element_count}
        result.update(self._identity_fields(page))
        if element_count != 1:
            return result

        item = locator.first
        tag_name = (item.get_attribute("data-tag-name") or "").lower()
        selector_tag = selector.strip().split("#", 1)[0].split(".", 1)[0].lower()
        if not tag_name and selector_tag in {"input"}:
            tag_name = selector_tag
        input_type = (item.get_attribute("type") or "").lower()
        role = item.get_attribute("role") or ""
        name = item.get_attribute("name") or ""
        element_id = item.get_attribute("id") or ""
        form_owner = item.get_attribute("form") or ""
        checked = item.is_checked()
        group_identity = ""
        if name:
            group_identity = _radio_group_identity(
                self._browser_session_id, self._page_id, name, form_owner
            )
        metadata_payload = "|".join([
            selector,
            tag_name,
            input_type,
            role.lower(),
            name,
            element_id,
            form_owner,
            group_identity,
        ])
        result.update({
            "visible": bool(item.is_visible()),
            "enabled": bool(item.is_enabled()),
            "tag_name": tag_name,
            "type": input_type,
            "role": role.lower(),
            "name": name,
            "id": element_id,
            "form_owner": form_owner,
            "checked": bool(checked),
            "radio_group_identity": group_identity,
            "metadata_sha256": hashlib.sha256(metadata_payload.encode()).hexdigest(),
            "main_frame": True,
        })
        return result

    def select_radio_by_identity(self, identity: dict) -> dict:
        page = self._ensure_page()
        selector = str(identity.get("selector") or "").strip()
        if not selector:
            raise ValueError("missing browser argument: selector")

        observed = self.inspect_radio(selector)
        for key, error in (
            ("browser_session_id", "SESSION_ID_DRIFT"),
            ("page_id", "PAGE_ID_DRIFT"),
            ("url", "URL_DRIFT"),
            ("origin", "ORIGIN_DRIFT"),
            ("tag_name", "TAG_DRIFT"),
            ("type", "TYPE_DRIFT"),
            ("name", "RADIO_GROUP_DRIFT"),
            ("form_owner", "FORM_OWNER_DRIFT"),
            ("radio_group_identity", "RADIO_GROUP_DRIFT"),
            ("metadata_sha256", "ELEMENT_IDENTITY_DRIFT"),
        ):
            if str(observed.get(key) or "") != str(identity.get(key) or ""):
                raise ValueError(error)
        if observed.get("element_count") != 1:
            raise ValueError("SELECTOR_COUNT_DRIFT")
        if observed.get("tag_name") != "input":
            raise ValueError("UNSUPPORTED_RADIO_TARGET")
        if observed.get("type") != "radio":
            raise ValueError("UNSUPPORTED_RADIO_TARGET")
        if not observed.get("name") or not observed.get("radio_group_identity"):
            raise ValueError("RADIO_GROUP_IDENTITY_INVALID")
        if observed.get("checked") is not identity.get("checked"):
            raise ValueError("PRE_CHECKED_DRIFT")
        if observed.get("visible") is not True:
            raise ValueError("ELEMENT_NOT_VISIBLE")
        if observed.get("enabled") is not True:
            raise ValueError("ELEMENT_NOT_ENABLED")
        if observed.get("closed") is True:
            raise ValueError("PAGE_CLOSED")
        if identity.get("main_frame") is not True:
            raise ValueError("IFRAME_UNSUPPORTED")
        if observed.get("main_frame") is not True:
            raise ValueError("IFRAME_UNSUPPORTED")

        events = {"popup": False, "new_page": False, "download": False}

        def _mark(name):
            def _handler(*_args):
                events[name] = True
            return _handler

        if observed.get("checked") is True:
            post = self.inspect_radio(selector)
            mutation_performed = False
        else:
            if hasattr(page, "on"):
                page.on("popup", _mark("popup"))
                page.on("download", _mark("download"))
            context = getattr(page, "context", None)
            if context is not None and hasattr(context, "on"):
                context.on("page", _mark("new_page"))
            page.locator(selector).first.check()
            mutation_performed = True
            if events["popup"]:
                raise ValueError("UNEXPECTED_POPUP")
            if events["new_page"]:
                raise ValueError("UNEXPECTED_NEW_PAGE")
            if events["download"]:
                raise ValueError("UNEXPECTED_DOWNLOAD")
            post = self.inspect_radio(selector)

        if _canonical_url(str(post.get("url") or "")) != _canonical_url(str(identity.get("url") or "")):
            raise ValueError("UNEXPECTED_NAVIGATION")
        if post.get("browser_session_id") != identity.get("browser_session_id"):
            raise ValueError("POST_SESSION_ID_DRIFT")
        if post.get("page_id") != identity.get("page_id"):
            raise ValueError("POST_PAGE_ID_DRIFT")
        if post.get("metadata_sha256") != identity.get("metadata_sha256"):
            raise ValueError("POST_ELEMENT_IDENTITY_DRIFT")
        if post.get("radio_group_identity") != identity.get("radio_group_identity"):
            raise ValueError("POST_RADIO_GROUP_DRIFT")
        if post.get("closed") is True:
            raise ValueError("POST_PAGE_CLOSED")
        if post.get("checked") is not True:
            raise ValueError("REALIZED_STATE_MISMATCH")
        return {
            "url": post.get("url"),
            "selector": selector,
            "browser_session_id": post.get("browser_session_id"),
            "page_id": post.get("page_id"),
            "origin": post.get("origin"),
            "closed": post.get("closed"),
            "checked": post.get("checked"),
            "radio_group_identity": post.get("radio_group_identity"),
            "mutation_performed": mutation_performed,
            "popup_detected": events["popup"],
            "new_page_detected": events["new_page"],
            "download_detected": events["download"],
            "navigation_detected": False,
            "proof_strength": "STRONG",
            "realized_state_verified": True,
        }

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
