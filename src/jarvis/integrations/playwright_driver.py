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
_FIELD_MAX_TARGET_VALUE_LENGTH = 4096
_FIELD_SUPPORTED_INPUT_TYPES = {"text", "search", "email", "url", "tel"}
_FIELD_DEFERRED_INPUT_TYPES = {"number", "date", "time", "datetime-local", "password"}
_FIELD_BLOCKED_INPUT_TYPES = {"file", "hidden"}
_FIELD_SENSITIVE_AUTOCOMPLETE = {
    "current-password",
    "new-password",
    "one-time-code",
    "cc-number",
    "cc-csc",
    "cc-exp",
    "cc-exp-month",
    "cc-exp-year",
}
_SUBMIT_ALLOWED_CLASSES = {"button:submit", "input:submit", "input:image"}
_SUBMIT_SENSITIVE_AUTOCOMPLETE = _FIELD_SENSITIVE_AUTOCOMPLETE
_SUBMIT_SENSITIVE_INPUT_TYPES = {"password"}
_SUBMIT_PAYMENT_INPUT_TYPES = {"month"}
_SUBMIT_EXECUTION_STATES = {
    "NOT_DISPATCHED",
    "DISPATCHED",
    "RESPONSE_OBSERVED",
    "POSTCONDITION_CONFIRMED",
    "DISPATCHED_OUTCOME_UNCERTAIN",
}


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


def _option_counts(options: list[dict], key: str, value: str) -> int:
    return sum(1 for option in options if str(option.get(key) or "") == value)


def _selected_option_from_value(options: list[dict], current_value: str) -> dict | None:
    matches = [option for option in options if str(option.get("option_value") or "") == current_value]
    return dict(matches[0]) if len(matches) == 1 else None


def _resolve_option_identity(options: list[dict], target: dict) -> dict:
    if target.get("match_kind") in {"value", "label", "text", "index"}:
        option = dict(target)
        if option.get("match_count") != 1:
            raise ValueError("OPTION_MATCH_COUNT_INVALID")
        if option.get("option_disabled") is True:
            raise ValueError("OPTION_DISABLED")
        for existing in options:
            if _same_physical_option(existing, option):
                if _option_counts(options, "option_value", str(option.get("option_value") or "")) != 1:
                    raise ValueError("DUPLICATE_OPTION_VALUE")
                return option
        raise ValueError("OPTION_TARGET_NOT_FOUND")
    modes = [
        ("value", "option_value"),
        ("label", "option_label"),
        ("text", "option_text"),
        ("index", "option_index"),
    ]
    supplied = [(mode, key) for mode, key in modes if target.get(key) is not None]
    if len(supplied) != 1:
        raise ValueError("EXACTLY_ONE_OPTION_IDENTITY_MODE_REQUIRED")
    match_kind, key = supplied[0]
    match_value = target.get(key)
    if match_kind == "index":
        if not isinstance(match_value, int) or isinstance(match_value, bool) or match_value < 0:
            raise ValueError("OPTION_INDEX_INVALID")
        matches = [option for option in options if option.get("option_index") == match_value]
    else:
        match_value = str(match_value)
        if not match_value:
            raise ValueError("OPTION_IDENTITY_VALUE_REQUIRED")
        matches = [option for option in options if str(option.get(key) or "") == match_value]
    if len(matches) == 0:
        raise ValueError("OPTION_TARGET_NOT_FOUND")
    if len(matches) > 1:
        if match_kind == "value":
            raise ValueError("DUPLICATE_OPTION_VALUE")
        if match_kind == "label":
            raise ValueError("DUPLICATE_OPTION_LABEL")
        if match_kind == "text":
            raise ValueError("DUPLICATE_OPTION_TEXT")
        raise ValueError("DUPLICATE_OPTION_INDEX")
    option = dict(matches[0])
    if option.get("option_disabled") is True:
        raise ValueError("OPTION_DISABLED")
    option["match_kind"] = match_kind
    option["match_value"] = match_value
    option["match_count"] = 1
    # Post-read without evaluate can prove a selected option by value only when that value is unique.
    if _option_counts(options, "option_value", str(option.get("option_value") or "")) != 1:
        raise ValueError("DUPLICATE_OPTION_VALUE")
    return option


def _same_option_identity(a: dict, b: dict) -> bool:
    for key in (
        "match_kind", "match_value", "option_value", "option_label",
        "option_text", "option_index", "option_disabled", "match_count",
    ):
        if a.get(key) != b.get(key):
            return False
    return True


def _same_physical_option(a: dict | None, b: dict | None) -> bool:
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    for key in ("option_value", "option_label", "option_text", "option_index", "option_disabled"):
        if a.get(key) != b.get(key):
            return False
    return True


def _field_value_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _safe_url_evidence(url: str) -> dict:
    canonical = _canonical_url(str(url or ""))
    parsed = urlparse(canonical)
    endpoint = urlunparse(parsed._replace(query="", fragment=""))
    return {
        "url_hash": _hash_text(canonical),
        "endpoint": endpoint,
        "origin": f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else "",
        "has_query": bool(parsed.query),
    }


def _field_class(tag_name: str, input_type: str) -> str:
    if tag_name == "textarea":
        return "TEXTAREA"
    if tag_name == "input" and input_type in _FIELD_SUPPORTED_INPUT_TYPES:
        return f"INPUT_{input_type.upper()}"
    if tag_name == "input" and input_type in _FIELD_DEFERRED_INPUT_TYPES:
        return "DEFERRED"
    if tag_name == "input" and input_type in _FIELD_BLOCKED_INPUT_TYPES:
        return "BLOCKED"
    return "UNSUPPORTED"


def _validate_field_identity(identity: dict) -> str:
    if not identity.get("browser_session_id"):
        return "SESSION_ID_MISSING"
    if not identity.get("page_id"):
        return "PAGE_ID_MISSING"
    if identity.get("closed") is True:
        return "PAGE_CLOSED"
    if identity.get("element_count") != 1:
        return "FIELD_COUNT_NOT_ONE"
    if identity.get("main_frame") is not True:
        return "IFRAME_UNSUPPORTED"
    field_class = identity.get("supported_field_class")
    if field_class not in {"INPUT_TEXT", "INPUT_SEARCH", "INPUT_EMAIL", "INPUT_URL", "INPUT_TEL", "TEXTAREA"}:
        input_type = identity.get("type")
        if input_type == "password":
            return "PASSWORD_FIELD_DEFERRED"
        if input_type == "file":
            return "FILE_FIELD_BLOCKED"
        if input_type == "hidden":
            return "HIDDEN_FIELD_BLOCKED"
        if input_type in {"number", "date", "time", "datetime-local"}:
            return "FIELD_TYPE_DEFERRED"
        if identity.get("contenteditable"):
            return "CONTENTEDITABLE_DEFERRED"
        return "UNSUPPORTED_FIELD_TARGET"
    if str(identity.get("autocomplete") or "").strip().lower() in _FIELD_SENSITIVE_AUTOCOMPLETE:
        return "SENSITIVE_AUTOCOMPLETE_DEFERRED"
    if identity.get("visible") is not True:
        return "ELEMENT_NOT_VISIBLE"
    if identity.get("enabled") is not True:
        return "ELEMENT_NOT_ENABLED"
    if identity.get("editable") is not True:
        return "ELEMENT_NOT_EDITABLE"
    if identity.get("readonly") is True:
        return "ELEMENT_READONLY"
    if not isinstance(identity.get("current_value_sha256"), str) or not identity.get("current_value_sha256"):
        return "CURRENT_VALUE_HASH_MISSING"
    if not isinstance(identity.get("current_value_length"), int):
        return "CURRENT_VALUE_LENGTH_MISSING"
    return ""


def _same_field_identity(a: dict, b: dict) -> bool:
    for key in (
        "browser_session_id", "page_id", "url", "origin", "selector",
        "element_count", "tag_name", "type", "name", "id", "role",
        "autocomplete", "form_owner", "metadata_sha256", "main_frame",
        "supported_field_class",
    ):
        if a.get(key) != b.get(key):
            return False
    return True


def _form_pre_state_anchor(identity: dict) -> str:
    snapshot = {
        "anchor_schema": "BROWSER_SUBMIT_FORM_NAVIGATION_PRE_STATE_V1",
        "browser_session_id": identity.get("browser_session_id") or "",
        "page_id": identity.get("page_id") or "",
        "url": identity.get("url") or "",
        "origin": identity.get("origin") or "",
        "form_selector": identity.get("form_selector") or "",
        "submitter_selector": identity.get("submitter_selector") or "",
        "form_metadata_sha256": identity.get("metadata_sha256") or "",
        "submitter_metadata_sha256": identity.get("submitter_metadata_sha256") or "",
        "field_manifest_hash": identity.get("field_manifest_hash") or "",
    }
    return _hash_text(json_dumps_stable(snapshot))


def json_dumps_stable(value: Any) -> str:
    import json
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _same_form_submission_identity(a: dict, b: dict) -> bool:
    for key in (
        "browser_session_id", "page_id", "url", "origin",
        "form_selector", "form_count", "form_action", "resolved_action",
        "method", "target", "enctype", "name", "id", "autocomplete",
        "submitter_selector", "submitter_count", "submitter_tag",
        "submitter_type", "submitter_name", "submitter_value_sha256",
        "submitter_form_owner", "submitter_text_sha256",
        "metadata_sha256", "submitter_metadata_sha256",
        "field_manifest_hash", "field_count", "main_frame_only",
    ):
        if a.get(key) != b.get(key):
            return False
    return True


def _validate_form_submission_identity(identity: dict) -> str:
    if not identity.get("browser_session_id"):
        return "SESSION_ID_MISSING"
    if not identity.get("page_id"):
        return "PAGE_ID_MISSING"
    if identity.get("closed") is True:
        return "PAGE_CLOSED"
    if identity.get("main_frame_only") is not True:
        return "IFRAME_UNSUPPORTED"
    if identity.get("form_count") != 1:
        return "FORM_COUNT_NOT_ONE"
    if identity.get("submitter_count") != 1:
        return "SUBMITTER_COUNT_NOT_ONE"
    if identity.get("form_tag") != "form":
        return "FORM_TAG_REQUIRED"
    if str(identity.get("method") or "").lower() != "get":
        return "FORM_METHOD_NOT_GET"
    if str(identity.get("target") or "").lower() in {"_blank", "_parent", "_top"}:
        return "FORM_TARGET_NEW_CONTEXT_UNSUPPORTED"
    if identity.get("same_origin_action") is not True:
        return "CROSS_ORIGIN_ACTION_UNSUPPORTED"
    submitter_class = f"{identity.get('submitter_tag')}:{identity.get('submitter_type')}"
    if submitter_class not in _SUBMIT_ALLOWED_CLASSES:
        return "UNSUPPORTED_SUBMITTER_TARGET"
    if identity.get("submitter_visible") is not True:
        return "SUBMITTER_NOT_VISIBLE"
    if identity.get("submitter_enabled") is not True:
        return "SUBMITTER_NOT_ENABLED"
    if identity.get("submitter_belongs_to_form") is not True:
        return "SUBMITTER_FORM_OWNER_MISMATCH"
    if identity.get("contains_password") is True:
        return "PASSWORD_FORM_DEFERRED"
    if identity.get("contains_otp_sensitive") is True:
        return "OTP_FORM_DEFERRED"
    if identity.get("contains_payment_sensitive") is True:
        return "PAYMENT_FORM_DEFERRED"
    return ""


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

    def inspect_select(self, selector: str) -> dict:
        page = self._ensure_page()
        locator = page.locator(selector)
        select_count = locator.count()
        result = {"url": page.url, "select_selector": selector, "select_count": select_count}
        result.update(self._identity_fields(page))
        if select_count != 1:
            return result

        item = locator.first
        tag_name = (item.get_attribute("data-tag-name") or "").lower()
        selector_tag = selector.strip().split("#", 1)[0].split(".", 1)[0].lower()
        if not tag_name and selector_tag in {"select"}:
            tag_name = selector_tag
        multiple = item.get_attribute("multiple") is not None
        role = item.get_attribute("role") or ""
        name = item.get_attribute("name") or ""
        element_id = item.get_attribute("id") or ""
        form_owner = item.get_attribute("form") or ""
        current_value = item.input_value()
        options = []
        option_locator = item.locator("option") if hasattr(item, "locator") else locator.locator("option")
        option_count = option_locator.count()
        for index in range(option_count):
            option = option_locator.nth(index)
            text = option.inner_text()
            value_attr = option.get_attribute("value")
            option_value = text if value_attr is None else value_attr
            label = option.get_attribute("label") or text
            options.append({
                "option_index": index,
                "option_value": option_value,
                "option_label": label,
                "option_text": text,
                "option_disabled": option.get_attribute("disabled") is not None,
            })
        current_selected_option = _selected_option_from_value(options, str(current_value or ""))
        current_selected_ambiguous = current_selected_option is None and current_value not in (None, "")
        metadata_payload = "|".join([
            selector,
            tag_name,
            str(multiple),
            role.lower(),
            name,
            element_id,
            form_owner,
            str(option_count),
        ])
        result.update({
            "visible": bool(item.is_visible()),
            "enabled": bool(item.is_enabled()),
            "tag_name": tag_name,
            "role": role.lower(),
            "name": name,
            "id": element_id,
            "form_owner": form_owner,
            "multiple": multiple,
            "current_value": current_value,
            "current_selected_option": current_selected_option,
            "current_selected_ambiguous": current_selected_ambiguous,
            "options": options,
            "option_count": option_count,
            "metadata_sha256": hashlib.sha256(metadata_payload.encode()).hexdigest(),
            "main_frame": True,
        })
        return result

    def select_option_by_identity(self, identity: dict, option_identity: dict) -> dict:
        page = self._ensure_page()
        selector = str(identity.get("select_selector") or "").strip()
        if not selector:
            raise ValueError("missing browser argument: select_selector")

        observed = self.inspect_select(selector)
        for key, error in (
            ("browser_session_id", "SESSION_ID_DRIFT"),
            ("page_id", "PAGE_ID_DRIFT"),
            ("url", "URL_DRIFT"),
            ("origin", "ORIGIN_DRIFT"),
            ("tag_name", "TAG_DRIFT"),
            ("multiple", "MULTI_SELECT_DRIFT"),
            ("metadata_sha256", "SELECT_IDENTITY_DRIFT"),
        ):
            if observed.get(key) != identity.get(key):
                raise ValueError(error)
        if observed.get("select_count") != 1:
            raise ValueError("SELECTOR_COUNT_DRIFT")
        if observed.get("tag_name") != "select":
            raise ValueError("UNSUPPORTED_SELECT_TARGET")
        if observed.get("multiple") is True:
            raise ValueError("UNSUPPORTED_MULTI_SELECT_V0")
        if not _same_physical_option(observed.get("current_selected_option"), identity.get("current_selected_option")):
            raise ValueError("PRE_SELECTED_DRIFT")
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

        target = _resolve_option_identity(list(observed.get("options") or []), option_identity)
        if not _same_option_identity(target, option_identity):
            raise ValueError("OPTION_IDENTITY_DRIFT")

        events = {"popup": False, "new_page": False, "download": False}

        def _mark(name):
            def _handler(*_args):
                events[name] = True
            return _handler

        if _same_physical_option(observed.get("current_selected_option"), option_identity):
            post = self.inspect_select(selector)
            mutation_performed = False
        else:
            if hasattr(page, "on"):
                page.on("popup", _mark("popup"))
                page.on("download", _mark("download"))
            context = getattr(page, "context", None)
            if context is not None and hasattr(context, "on"):
                context.on("page", _mark("new_page"))
            if option_identity.get("match_kind") == "label":
                page.locator(selector).first.select_option(label=str(option_identity.get("match_value") or ""))
            elif option_identity.get("match_kind") == "index":
                page.locator(selector).first.select_option(index=int(option_identity.get("match_value")))
            else:
                page.locator(selector).first.select_option(str(option_identity.get("option_value") or ""))
            mutation_performed = True
            if events["popup"]:
                raise ValueError("UNEXPECTED_POPUP")
            if events["new_page"]:
                raise ValueError("UNEXPECTED_NEW_PAGE")
            if events["download"]:
                raise ValueError("UNEXPECTED_DOWNLOAD")
            post = self.inspect_select(selector)

        if _canonical_url(str(post.get("url") or "")) != _canonical_url(str(identity.get("url") or "")):
            raise ValueError("UNEXPECTED_NAVIGATION")
        if post.get("browser_session_id") != identity.get("browser_session_id"):
            raise ValueError("POST_SESSION_ID_DRIFT")
        if post.get("page_id") != identity.get("page_id"):
            raise ValueError("POST_PAGE_ID_DRIFT")
        if post.get("metadata_sha256") != identity.get("metadata_sha256"):
            raise ValueError("POST_SELECT_IDENTITY_DRIFT")
        post_target = _resolve_option_identity(list(post.get("options") or []), option_identity)
        if not _same_option_identity(post_target, option_identity):
            raise ValueError("POST_OPTION_IDENTITY_DRIFT")
        if not _same_physical_option(post.get("current_selected_option"), option_identity):
            raise ValueError("REALIZED_STATE_MISMATCH")
        if post.get("closed") is True:
            raise ValueError("POST_PAGE_CLOSED")
        return {
            "url": post.get("url"),
            "select_selector": selector,
            "browser_session_id": post.get("browser_session_id"),
            "page_id": post.get("page_id"),
            "origin": post.get("origin"),
            "closed": post.get("closed"),
            "current_value": post.get("current_value"),
            "current_selected_option": post.get("current_selected_option"),
            "target_option_identity": option_identity,
            "mutation_performed": mutation_performed,
            "popup_detected": events["popup"],
            "new_page_detected": events["new_page"],
            "download_detected": events["download"],
            "navigation_detected": False,
            "proof_strength": "STRONG",
            "realized_state_verified": True,
        }

    def inspect_field(self, selector: str) -> dict:
        page = self._ensure_page()
        locator = page.locator(selector)
        element_count = locator.count()
        result = {"url": page.url, "selector": selector, "element_count": element_count}
        result.update(self._identity_fields(page))
        if element_count != 1:
            return result

        item = locator.first
        tag_name = (item.get_attribute("data-tag-name") or "").strip().lower()
        selector_tag = selector.strip().split("#", 1)[0].split(".", 1)[0].lower()
        if not tag_name and selector_tag in {"input", "textarea"}:
            tag_name = selector_tag
        input_type = (item.get_attribute("type") or ("text" if tag_name == "input" else "")).strip().lower()
        name = item.get_attribute("name") or ""
        element_id = item.get_attribute("id") or ""
        role = (item.get_attribute("role") or "").lower()
        autocomplete = (item.get_attribute("autocomplete") or "").strip().lower()
        form_owner = item.get_attribute("form") or ""
        readonly = item.get_attribute("readonly") is not None
        contenteditable = item.get_attribute("contenteditable") is not None
        visible = bool(item.is_visible())
        enabled = bool(item.is_enabled())
        field_class = _field_class(tag_name, input_type)
        current_value = ""
        current_hash = ""
        current_length = None
        editable = False
        if field_class in {"INPUT_TEXT", "INPUT_SEARCH", "INPUT_EMAIL", "INPUT_URL", "INPUT_TEL", "TEXTAREA"}:
            current_value = item.input_value()
            current_hash = _field_value_sha256(current_value)
            current_length = len(current_value)
            editable = bool(item.is_editable())
        elif hasattr(item, "is_editable"):
            try:
                editable = bool(item.is_editable())
            except Exception:
                editable = False
        metadata_payload = "|".join([
            selector,
            tag_name,
            input_type,
            name,
            element_id,
            role,
            autocomplete,
            form_owner,
            field_class,
        ])
        result.update({
            "tag_name": tag_name,
            "type": input_type,
            "name": name,
            "id": element_id,
            "role": role,
            "autocomplete": autocomplete,
            "form_owner": form_owner,
            "visible": visible,
            "enabled": enabled,
            "editable": editable,
            "readonly": readonly,
            "contenteditable": contenteditable,
            "supported_field_class": field_class,
            "current_value_sha256": current_hash,
            "current_value_length": current_length,
            "metadata_sha256": hashlib.sha256(metadata_payload.encode()).hexdigest(),
            "main_frame": True,
            "max_target_value_length": _FIELD_MAX_TARGET_VALUE_LENGTH,
            "sensitive_autocomplete_denylist": sorted(_FIELD_SENSITIVE_AUTOCOMPLETE),
        })
        return result

    def set_field_value_by_identity(self, identity: dict, target_value: str) -> dict:
        if not isinstance(target_value, str):
            raise ValueError("TARGET_VALUE_STRING_REQUIRED")
        if len(target_value) > _FIELD_MAX_TARGET_VALUE_LENGTH:
            raise ValueError("TARGET_VALUE_TOO_LONG")
        selector = str(identity.get("selector") or "").strip()
        if not selector:
            raise ValueError("missing browser argument: selector")

        observed = self.inspect_field(selector)
        reason = _validate_field_identity(observed)
        if reason:
            raise ValueError(reason)
        if identity.get("main_frame") is not True:
            raise ValueError("IFRAME_UNSUPPORTED")
        if not _same_field_identity(identity, observed):
            raise ValueError("FIELD_IDENTITY_DRIFT")
        if observed.get("current_value_sha256") != identity.get("current_value_sha256"):
            raise ValueError("PRE_VALUE_HASH_DRIFT")
        if observed.get("current_value_length") != identity.get("current_value_length"):
            raise ValueError("PRE_VALUE_LENGTH_DRIFT")

        page = self._ensure_page()
        target_hash = _field_value_sha256(target_value)
        target_length = len(target_value)
        events = {"popup": False, "new_page": False, "download": False}

        def _mark(name):
            def _handler(*_args):
                events[name] = True
            return _handler

        if observed.get("current_value_sha256") == target_hash and observed.get("current_value_length") == target_length:
            post = self.inspect_field(selector)
            mutation_performed = False
        else:
            if hasattr(page, "on"):
                page.on("popup", _mark("popup"))
                page.on("download", _mark("download"))
            context = getattr(page, "context", None)
            if context is not None and hasattr(context, "on"):
                context.on("page", _mark("new_page"))
            page.locator(selector).first.fill(target_value)
            mutation_performed = True
            if events["popup"]:
                raise ValueError("UNEXPECTED_POPUP")
            if events["new_page"]:
                raise ValueError("UNEXPECTED_NEW_PAGE")
            if events["download"]:
                raise ValueError("UNEXPECTED_DOWNLOAD")
            post = self.inspect_field(selector)

        if _canonical_url(str(post.get("url") or "")) != _canonical_url(str(identity.get("url") or "")):
            raise ValueError("UNEXPECTED_NAVIGATION")
        if post.get("browser_session_id") != identity.get("browser_session_id"):
            raise ValueError("POST_SESSION_ID_DRIFT")
        if post.get("page_id") != identity.get("page_id"):
            raise ValueError("POST_PAGE_ID_DRIFT")
        if not _same_field_identity({**identity, "current_value_sha256": post.get("current_value_sha256"),
                                     "current_value_length": post.get("current_value_length")}, post):
            raise ValueError("POST_FIELD_IDENTITY_DRIFT")
        if post.get("current_value_sha256") != target_hash:
            raise ValueError("REALIZED_STATE_MISMATCH")
        if post.get("current_value_length") != target_length:
            raise ValueError("REALIZED_STATE_LENGTH_MISMATCH")
        if post.get("closed") is True:
            raise ValueError("POST_PAGE_CLOSED")
        return {
            "url": post.get("url"),
            "selector": selector,
            "browser_session_id": post.get("browser_session_id"),
            "page_id": post.get("page_id"),
            "origin": post.get("origin"),
            "closed": post.get("closed"),
            "field_identity": {k: post.get(k) for k in (
                "selector", "element_count", "tag_name", "type", "name", "id",
                "role", "autocomplete", "form_owner", "metadata_sha256",
                "main_frame", "supported_field_class",
            )},
            "target_value_sha256": target_hash,
            "post_value_sha256": post.get("current_value_sha256"),
            "target_value_length": target_length,
            "post_value_length": post.get("current_value_length"),
            "mutation_performed": mutation_performed,
            "popup_detected": events["popup"],
            "new_page_detected": events["new_page"],
            "download_detected": events["download"],
            "navigation_detected": False,
            "proof_strength": "STRONG",
            "realized_state_verified": True,
        }

    def inspect_form_submission(self, form_selector: str, submitter_selector: str) -> dict:
        page = self._ensure_page()
        form_selector = str(form_selector or "").strip()
        submitter_selector = str(submitter_selector or "").strip()
        form = page.locator(form_selector)
        submitter = page.locator(submitter_selector)
        form_count = form.count()
        submitter_count = submitter.count()
        result = {
            "url": page.url,
            "origin": self._page_origin(page.url),
            "form_selector": form_selector,
            "form_count": form_count,
            "submitter_selector": submitter_selector,
            "submitter_count": submitter_count,
            "main_frame_only": True,
        }
        result.update(self._identity_fields(page))
        if form_count != 1 or submitter_count != 1:
            return result

        form_item = form.first
        submit_item = submitter.first
        form_tag = (form_item.get_attribute("data-tag-name") or "").strip().lower()
        if not form_tag and form_selector.lower().lstrip().startswith("form"):
            form_tag = "form"
        method = (form_item.get_attribute("method") or "get").strip().lower() or "get"
        raw_action = form_item.get_attribute("action") or page.url
        resolved_action = _canonical_url(urljoin(page.url, raw_action))
        action_origin = self._page_origin(resolved_action)
        current_origin = self._page_origin(page.url)
        target = (form_item.get_attribute("target") or "").strip().lower()
        enctype = (form_item.get_attribute("enctype") or "application/x-www-form-urlencoded").strip().lower()
        form_name = form_item.get_attribute("name") or ""
        form_id = form_item.get_attribute("id") or ""
        autocomplete = (form_item.get_attribute("autocomplete") or "").strip().lower()

        submitter_tag = (submit_item.get_attribute("data-tag-name") or "").strip().lower()
        if not submitter_tag:
            s = submitter_selector.lower()
            if s.lstrip().startswith("button"):
                submitter_tag = "button"
            elif s.lstrip().startswith("input"):
                submitter_tag = "input"
        submitter_type = (submit_item.get_attribute("type") or ("submit" if submitter_tag == "button" else "")).strip().lower()
        if submitter_tag == "button" and not submitter_type:
            submitter_type = "submit"
        submitter_name = submit_item.get_attribute("name") or ""
        submitter_value = submit_item.get_attribute("value") or ""
        submitter_form_owner = submit_item.get_attribute("form") or ""
        submitter_text = ""
        if hasattr(submit_item, "inner_text"):
            try:
                submitter_text = submit_item.inner_text() or ""
            except Exception:
                submitter_text = ""
        submitter_belongs = submitter_form_owner in ("", form_id) if form_id else submitter_form_owner == ""

        field_manifest = self._form_field_manifest(form, form_id)
        field_manifest_hash = _hash_text(json_dumps_stable(field_manifest))
        metadata_payload = "|".join([
            form_selector, form_tag, raw_action, resolved_action, method,
            target, enctype, form_name, form_id, autocomplete,
        ])
        submitter_metadata_payload = "|".join([
            submitter_selector, submitter_tag, submitter_type, submitter_name,
            submitter_form_owner, submitter_value, submitter_text,
        ])
        result.update({
            "form_tag": form_tag,
            "form_action": raw_action,
            "resolved_action": resolved_action,
            "resolved_action_hash": _hash_text(resolved_action),
            "resolved_action_endpoint": _safe_url_evidence(resolved_action)["endpoint"],
            "method": method,
            "target": target,
            "enctype": enctype,
            "name": form_name,
            "id": form_id,
            "autocomplete": autocomplete,
            "same_origin_action": action_origin == current_origin,
            "submitter_tag": submitter_tag,
            "submitter_type": submitter_type,
            "submitter_name": submitter_name,
            "submitter_value_sha256": _hash_text(submitter_value),
            "submitter_value_length": len(submitter_value),
            "submitter_form_owner": submitter_form_owner,
            "submitter_belongs_to_form": submitter_belongs,
            "submitter_visible": bool(submit_item.is_visible()),
            "submitter_enabled": bool(submit_item.is_enabled()),
            "submitter_text_sha256": _hash_text(submitter_text),
            "field_manifest": field_manifest,
            "field_manifest_hash": field_manifest_hash,
            "field_count": len(field_manifest),
            "contains_password": any(f.get("sensitive_class") == "password" for f in field_manifest),
            "contains_otp_sensitive": any(f.get("sensitive_class") == "otp" for f in field_manifest),
            "contains_payment_sensitive": any(f.get("sensitive_class") == "payment" for f in field_manifest),
            "metadata_sha256": _hash_text(metadata_payload),
            "submitter_metadata_sha256": _hash_text(submitter_metadata_payload),
            "physical_state_anchor": "",
            "redirect_policy": "SAME_ORIGIN_REDIRECT_CHAIN",
            "expected_effect": "NAVIGATION",
        })
        result["physical_state_anchor"] = _form_pre_state_anchor(result)
        return result

    def _form_field_manifest(self, form, form_id: str) -> list[dict]:
        fields: list[dict] = []
        if not hasattr(form, "locator"):
            return fields
        try:
            controls = form.locator("input, textarea, select")
            count = controls.count()
        except Exception:
            return fields
        for index in range(count):
            control = controls.nth(index)
            tag = (control.get_attribute("data-tag-name") or "").strip().lower()
            input_type = (control.get_attribute("type") or ("text" if tag == "input" else "")).strip().lower()
            name = control.get_attribute("name") or ""
            autocomplete = (control.get_attribute("autocomplete") or "").strip().lower()
            form_owner = control.get_attribute("form") or form_id or ""
            enabled = bool(control.is_enabled())
            checked = None
            if hasattr(control, "is_checked"):
                try:
                    checked = bool(control.is_checked())
                except Exception:
                    checked = None
            value = ""
            if tag in {"input", "textarea", "select"} and hasattr(control, "input_value"):
                try:
                    value = control.input_value() or ""
                except Exception:
                    value = control.get_attribute("value") or ""
            sensitive = ""
            if input_type in _SUBMIT_SENSITIVE_INPUT_TYPES:
                sensitive = "password"
            elif autocomplete == "one-time-code":
                sensitive = "otp"
            elif autocomplete in _SUBMIT_SENSITIVE_AUTOCOMPLETE or input_type in _SUBMIT_PAYMENT_INPUT_TYPES:
                sensitive = "payment"
            fields.append({
                "index": index,
                "name_sha256": _hash_text(name),
                "type": input_type,
                "tag_name": tag,
                "form_owner_sha256": _hash_text(form_owner),
                "enabled": enabled,
                "checked": checked,
                "successful_control_v0": bool(enabled and name),
                "value_sha256": _hash_text(value),
                "value_length": len(value),
                "hidden": input_type == "hidden",
                "autocomplete": autocomplete,
                "sensitive_class": sensitive,
            })
        return fields

    def submit_get_navigation_by_identity(self, identity: dict) -> dict:
        page = self._ensure_page()
        form_selector = str(identity.get("form_selector") or "").strip()
        submitter_selector = str(identity.get("submitter_selector") or "").strip()
        if not form_selector:
            raise ValueError("missing browser argument: form_selector")
        if not submitter_selector:
            raise ValueError("missing browser argument: submitter_selector")

        observed = self.inspect_form_submission(form_selector, submitter_selector)
        reason = _validate_form_submission_identity(observed)
        if reason:
            raise ValueError(reason)
        if not _same_form_submission_identity(identity, observed):
            raise ValueError("FORM_SUBMISSION_IDENTITY_DRIFT")
        if observed.get("physical_state_anchor") != identity.get("physical_state_anchor"):
            raise ValueError("PRE_STATE_DRIFT")

        events = {"popup": False, "new_page": False, "download": False}
        request_seen: dict[str, Any] = {}
        response_seen: dict[str, Any] = {}
        execution_state = "NOT_DISPATCHED"

        approved_endpoint = _safe_url_evidence(str(identity.get("resolved_action") or "")).get("endpoint")
        approved_origin = str(identity.get("origin") or "")

        def _mark(name):
            def _handler(*_args):
                events[name] = True
            return _handler

        def _request_handler(request):
            nonlocal execution_state
            try:
                method = request.method
                url = request.url
                resource_type = getattr(request, "resource_type", "")
                post_data = request.post_data if hasattr(request, "post_data") else None
            except Exception:
                return
            safe = _safe_url_evidence(url)
            if str(method).upper() == "GET" and safe.get("endpoint") == approved_endpoint:
                request_seen.update({
                    "method": str(method).upper(),
                    "url_hash": safe["url_hash"],
                    "endpoint": safe["endpoint"],
                    "origin": safe["origin"],
                    "has_query": safe["has_query"],
                    "resource_type": resource_type,
                    "post_data_present": bool(post_data),
                    "fingerprint": _hash_text("|".join([
                        str(method).upper(), safe["url_hash"], str(resource_type), identity.get("field_manifest_hash") or "",
                    ])),
                })
                execution_state = "DISPATCHED"

        def _response_handler(response):
            nonlocal execution_state
            try:
                request = response.request
                method = request.method
                url = response.url
                status = response.status
            except Exception:
                return
            safe = _safe_url_evidence(url)
            if str(method).upper() == "GET" and safe.get("endpoint") == approved_endpoint:
                response_seen.update({
                    "status": status,
                    "url_hash": safe["url_hash"],
                    "endpoint": safe["endpoint"],
                    "origin": safe["origin"],
                    "same_origin": safe["origin"] == approved_origin,
                })
                execution_state = "RESPONSE_OBSERVED"

        if hasattr(page, "on"):
            page.on("popup", _mark("popup"))
            page.on("download", _mark("download"))
            page.on("request", _request_handler)
            page.on("response", _response_handler)
        context = getattr(page, "context", None)
        if context is not None and hasattr(context, "on"):
            context.on("page", _mark("new_page"))

        page.locator(submitter_selector).first.click()

        if not request_seen:
            raise ValueError("REQUEST_NOT_OBSERVED")
        if events["popup"]:
            execution_state = "DISPATCHED_OUTCOME_UNCERTAIN"
        if events["new_page"]:
            execution_state = "DISPATCHED_OUTCOME_UNCERTAIN"
        if events["download"]:
            execution_state = "DISPATCHED_OUTCOME_UNCERTAIN"
        if request_seen.get("method") != "GET" or request_seen.get("post_data_present"):
            execution_state = "DISPATCHED_OUTCOME_UNCERTAIN"
        if request_seen.get("origin") != approved_origin:
            execution_state = "DISPATCHED_OUTCOME_UNCERTAIN"

        try:
            post = self.read()
        except Exception as exc:
            return self._submission_uncertain_result(identity, request_seen, response_seen, events, f"POST_READ_FAILED:{type(exc).__name__}")

        final_safe = _safe_url_evidence(str(post.get("url") or ""))
        if execution_state == "DISPATCHED_OUTCOME_UNCERTAIN":
            return self._submission_uncertain_result(identity, request_seen, response_seen, events, "SIDE_EFFECT_OR_REQUEST_POLICY_VIOLATION", post, final_safe)
        if not response_seen:
            return self._submission_uncertain_result(identity, request_seen, response_seen, events, "RESPONSE_NOT_OBSERVED", post, final_safe)
        if response_seen.get("same_origin") is not True:
            return self._submission_uncertain_result(identity, request_seen, response_seen, events, "CROSS_ORIGIN_RESPONSE_OR_REDIRECT", post, final_safe)
        if post.get("browser_session_id") != identity.get("browser_session_id"):
            return self._submission_uncertain_result(identity, request_seen, response_seen, events, "POST_SESSION_ID_DRIFT", post, final_safe)
        if post.get("page_id") != identity.get("page_id"):
            return self._submission_uncertain_result(identity, request_seen, response_seen, events, "POST_PAGE_ID_DRIFT", post, final_safe)
        if post.get("closed") is True:
            return self._submission_uncertain_result(identity, request_seen, response_seen, events, "POST_PAGE_CLOSED", post, final_safe)
        if final_safe.get("origin") != approved_origin:
            return self._submission_uncertain_result(identity, request_seen, response_seen, events, "CROSS_ORIGIN_FINAL_URL", post, final_safe)

        return {
            "url_hash": final_safe["url_hash"],
            "final_url_hash": final_safe["url_hash"],
            "final_url_endpoint": final_safe["endpoint"],
            "final_origin": final_safe["origin"],
            "browser_session_id": post.get("browser_session_id"),
            "page_id": post.get("page_id"),
            "closed": post.get("closed"),
            "form_selector": form_selector,
            "submitter_selector": submitter_selector,
            "field_manifest_hash": identity.get("field_manifest_hash"),
            "request_observed": True,
            "request_method": request_seen.get("method"),
            "request_url_hash": request_seen.get("url_hash"),
            "request_endpoint": request_seen.get("endpoint"),
            "request_resource_type": request_seen.get("resource_type"),
            "request_fingerprint": request_seen.get("fingerprint"),
            "response_observed": True,
            "response_status": response_seen.get("status"),
            "response_url_hash": response_seen.get("url_hash"),
            "execution_state": "POSTCONDITION_CONFIRMED",
            "transport_proof": "STRONG",
            "navigation_proof": "STRONG",
            "application_proof": "NOT_CLAIMED",
            "realized_state_verified": True,
            "proof_strength": "STRONG",
            "redirect_policy": "SAME_ORIGIN_REDIRECT_CHAIN",
            "popup_detected": events["popup"],
            "new_page_detected": events["new_page"],
            "download_detected": events["download"],
            "plaintext_form_data_returned": False,
            "replay_physical_action_allowed": False,
            "idempotency_assumed": False,
        }

    def _submission_uncertain_result(
        self,
        identity: dict,
        request_seen: dict,
        response_seen: dict,
        events: dict,
        reason: str,
        post: dict | None = None,
        final_safe: dict | None = None,
    ) -> dict:
        post = post or {}
        final_safe = final_safe or {}
        return {
            "url_hash": final_safe.get("url_hash", ""),
            "final_url_hash": final_safe.get("url_hash", ""),
            "final_url_endpoint": final_safe.get("endpoint", ""),
            "final_origin": final_safe.get("origin", ""),
            "browser_session_id": post.get("browser_session_id", identity.get("browser_session_id")),
            "page_id": post.get("page_id", identity.get("page_id")),
            "closed": post.get("closed"),
            "form_selector": identity.get("form_selector"),
            "submitter_selector": identity.get("submitter_selector"),
            "field_manifest_hash": identity.get("field_manifest_hash"),
            "request_observed": bool(request_seen),
            "request_method": request_seen.get("method"),
            "request_url_hash": request_seen.get("url_hash"),
            "request_endpoint": request_seen.get("endpoint"),
            "request_resource_type": request_seen.get("resource_type"),
            "request_fingerprint": request_seen.get("fingerprint"),
            "response_observed": bool(response_seen),
            "response_status": response_seen.get("status"),
            "response_url_hash": response_seen.get("url_hash"),
            "execution_state": "DISPATCHED_OUTCOME_UNCERTAIN",
            "uncertain_reason": reason,
            "transport_proof": "STRONG" if request_seen else "NONE",
            "navigation_proof": "UNCERTAIN",
            "application_proof": "NOT_CLAIMED",
            "realized_state_verified": False,
            "proof_strength": "UNCERTAIN",
            "redirect_policy": "SAME_ORIGIN_REDIRECT_CHAIN",
            "popup_detected": events.get("popup", False),
            "new_page_detected": events.get("new_page", False),
            "download_detected": events.get("download", False),
            "plaintext_form_data_returned": False,
            "replay_physical_action_allowed": False,
            "idempotency_assumed": False,
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
