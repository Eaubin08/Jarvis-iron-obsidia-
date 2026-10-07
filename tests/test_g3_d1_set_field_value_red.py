from __future__ import annotations

import hashlib

from jarvis.browser import BrowserBackend
from jarvis.contracts import ActionRequest
from jarvis.integrations.playwright_driver import PlaywrightDriver


SID = "sess-aaaaaaaaaaaaaaaaaaaaaaaaaaaa"
PID = "page-bbbbbbbbbbbbbbbbbbbbbbbb"
URL = "https://example.com/page"


def _h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class FakeContext:
    def __init__(self):
        self.handlers = {}

    def on(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)


class FakeField:
    def __init__(
        self,
        page=None,
        *,
        count=1,
        tag_name="input",
        input_type="text",
        value="old",
        visible=True,
        enabled=True,
        editable=True,
        readonly=False,
        autocomplete="",
        contenteditable=False,
    ):
        self.page = page
        self._count = count
        self.tag_name = tag_name
        self.input_type = input_type
        self.value = value
        self.visible = visible
        self.enabled = enabled
        self.editable = editable
        self.readonly = readonly
        self.autocomplete = autocomplete
        self.contenteditable = contenteditable
        self.fills = []
        self.first = self

    def count(self):
        return self._count

    def get_attribute(self, name):
        values = {
            "data-tag-name": self.tag_name,
            "type": self.input_type,
            "name": "contact",
            "id": "contact",
            "role": "",
            "autocomplete": self.autocomplete,
            "form": "f1",
        }
        if name == "readonly":
            return "" if self.readonly else None
        if name == "contenteditable":
            return "true" if self.contenteditable else None
        return values.get(name)

    def input_value(self):
        return self.value

    def is_visible(self):
        return self.visible

    def is_enabled(self):
        return self.enabled

    def is_editable(self):
        return self.editable

    def fill(self, value):
        self.fills.append(value)
        if self.page.event_to_fire:
            self.page.fire(self.page.event_to_fire)
            return
        if self.page.navigate_on_fill:
            self.page._url = "https://example.com/other"
        self.value = value


class FakePage:
    def __init__(self, field):
        self._url = URL
        self._closed = False
        self.context = FakeContext()
        self.handlers = {}
        self.field = field
        self.event_to_fire = ""
        self.navigate_on_fill = False
        field.page = self

    @property
    def url(self):
        return self._url

    def is_closed(self):
        return self._closed

    def locator(self, selector):
        return self.field

    def on(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)

    def fire(self, event):
        target = self.context if event == "page" else self
        for handler in target.handlers.get(event, []):
            handler(object())


def _driver(field):
    page = FakePage(field)
    d = PlaywrightDriver()
    d._page = page
    d._browser_session_id = SID
    d._page_id = PID
    return d, page, field


def _set(driver, identity, value):
    args = dict(identity)
    args["target_value"] = value
    return BrowserBackend(driver).execute(ActionRequest("browser.set_field_value", args))


def test_supported_field_types_and_hash_only_inspection():
    cases = [
        (FakeField(input_type="text"), "INPUT_TEXT"),
        (FakeField(input_type="search"), "INPUT_SEARCH"),
        (FakeField(input_type="email"), "INPUT_EMAIL"),
        (FakeField(input_type="url"), "INPUT_URL"),
        (FakeField(input_type="tel"), "INPUT_TEL"),
        (FakeField(tag_name="textarea", input_type=""), "TEXTAREA"),
    ]
    for field, field_class in cases:
        d, _page, _field = _driver(field)
        inspected = d.inspect_field("input#contact")
        assert inspected["supported_field_class"] == field_class
        assert inspected["current_value_sha256"] == _h("old")
        assert "current_value" not in inspected
        assert inspected["current_value_length"] == 3


def test_reject_count_identity_actionability_and_unsupported_types():
    cases = [
        (FakeField(count=0), "FIELD_COUNT_NOT_ONE"),
        (FakeField(count=2), "FIELD_COUNT_NOT_ONE"),
        (FakeField(input_type="password"), "PASSWORD_FIELD_DEFERRED"),
        (FakeField(input_type="file"), "FILE_FIELD_BLOCKED"),
        (FakeField(input_type="hidden"), "HIDDEN_FIELD_BLOCKED"),
        (FakeField(input_type="number"), "FIELD_TYPE_DEFERRED"),
        (FakeField(input_type="date"), "FIELD_TYPE_DEFERRED"),
        (FakeField(input_type="time"), "FIELD_TYPE_DEFERRED"),
        (FakeField(input_type="datetime-local"), "FIELD_TYPE_DEFERRED"),
        (FakeField(tag_name="div", contenteditable=True), "CONTENTEDITABLE_DEFERRED"),
        (FakeField(tag_name="select"), "UNSUPPORTED_FIELD_TARGET"),
        (FakeField(visible=False), "ELEMENT_NOT_VISIBLE"),
        (FakeField(enabled=False), "ELEMENT_NOT_ENABLED"),
        (FakeField(editable=False), "ELEMENT_NOT_EDITABLE"),
        (FakeField(readonly=True), "ELEMENT_READONLY"),
        (FakeField(autocomplete="current-password"), "SENSITIVE_AUTOCOMPLETE_DEFERRED"),
        (FakeField(autocomplete="one-time-code"), "SENSITIVE_AUTOCOMPLETE_DEFERRED"),
        (FakeField(autocomplete="cc-number"), "SENSITIVE_AUTOCOMPLETE_DEFERRED"),
    ]
    for field, message in cases:
        d, _page, _field = _driver(field)
        result = _set(d, d.inspect_field("input#contact"), "new")
        assert not result.ok
        assert message in result.message


def test_identity_and_pre_value_drift_reject():
    d, _page, _field = _driver(FakeField())
    ident = d.inspect_field("input#contact")
    for key, message in (
        ("browser_session_id", "FIELD_IDENTITY_DRIFT"),
        ("page_id", "FIELD_IDENTITY_DRIFT"),
        ("metadata_sha256", "FIELD_IDENTITY_DRIFT"),
    ):
        bad = dict(ident)
        bad[key] = ""
        result = _set(d, bad, "new")
        assert not result.ok
        assert message in result.message
    bad = dict(ident)
    bad["current_value_sha256"] = _h("different")
    assert "PRE_VALUE_HASH_DRIFT" in _set(d, bad, "new").message
    bad = dict(ident)
    bad["current_value_length"] = 99
    assert "PRE_VALUE_LENGTH_DRIFT" in _set(d, bad, "new").message
    bad = dict(ident)
    bad["main_frame"] = False
    assert "IFRAME_UNSUPPORTED" in _set(d, bad, "new").message


def test_set_value_empty_unicode_noop_and_max_length():
    d, _page, field = _driver(FakeField(value="old"))
    result = _set(d, d.inspect_field("input#contact"), "bonjour \u2603")
    assert result.ok
    assert result.data["mutation_performed"] is True
    assert result.data["target_value_sha256"] == _h("bonjour \u2603")
    assert "bonjour" not in str(result.data)
    assert field.fills == ["bonjour \u2603"]

    ident = d.inspect_field("input#contact")
    result = _set(d, ident, "bonjour \u2603")
    assert result.ok
    assert result.data["mutation_performed"] is False
    assert field.fills == ["bonjour \u2603"]

    result = _set(d, d.inspect_field("input#contact"), "")
    assert result.ok
    assert result.data["target_value_length"] == 0
    assert field.fills == ["bonjour \u2603", ""]

    result = _set(d, d.inspect_field("input#contact"), "x" * 4097)
    assert not result.ok
    assert "TARGET_VALUE_TOO_LONG" in result.message


def test_post_mismatch_and_side_effects_fail_closed():
    d, _page, field = _driver(FakeField())
    original_fill = field.fill

    def bad_fill(value):
        original_fill("wrong")

    field.fill = bad_fill
    result = _set(d, d.inspect_field("input#contact"), "new")
    assert not result.ok
    assert "REALIZED_STATE_MISMATCH" in result.message

    for event, message in (
        ("popup", "UNEXPECTED_POPUP"),
        ("page", "UNEXPECTED_NEW_PAGE"),
        ("download", "UNEXPECTED_DOWNLOAD"),
    ):
        d, page, _field = _driver(FakeField())
        page.event_to_fire = event
        result = _set(d, d.inspect_field("input#contact"), "new")
        assert not result.ok
        assert message in result.message

    d, page, _field = _driver(FakeField())
    page.navigate_on_fill = True
    result = _set(d, d.inspect_field("input#contact"), "new")
    assert not result.ok
    assert "UNEXPECTED_NAVIGATION" in result.message


def test_no_generic_fill_submit_press_or_evaluate_surface():
    backend = BrowserBackend(_driver(FakeField())[0])
    assert not backend.can_execute(ActionRequest("browser.fill", {"selector": "#x", "value": "y"}), type("C", (), {"backend_family": "browser"})())
    result = backend.execute(ActionRequest("browser.fill", {"selector": "#x", "value": "y"}))
    assert not result.ok
    assert "unsupported" in result.message
    assert not hasattr(PlaywrightDriver, "submit")
    assert not hasattr(PlaywrightDriver, "press")
    assert not hasattr(PlaywrightDriver, "evaluate")
