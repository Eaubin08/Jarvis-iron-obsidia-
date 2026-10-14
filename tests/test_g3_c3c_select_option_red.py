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


class FakeOption:
    def __init__(self, value, text, *, label=None, disabled=False):
        self.value = value
        self.text = text
        self.label = label
        self.disabled = disabled

    def inner_text(self):
        return self.text

    def get_attribute(self, name):
        if name == "value":
            return self.value
        if name == "label":
            return self.label
        if name == "disabled":
            return "" if self.disabled else None
        return None


class FakeOptionLocator:
    def __init__(self, options):
        self.options = options

    def count(self):
        return len(self.options)

    def nth(self, index):
        return self.options[index]


class FakeSelect:
    def __init__(
        self,
        page,
        *,
        count=1,
        tag_name="select",
        multiple=False,
        visible=True,
        enabled=True,
        current_value="basic",
        options=None,
    ):
        self.page = page
        self._count = count
        self.tag_name = tag_name
        self.multiple = multiple
        self.visible = visible
        self.enabled = enabled
        self.current_value = current_value
        self.options = options or [
            FakeOption("basic", "Basic", label="Basic"),
            FakeOption("pro", "Pro", label="Pro"),
        ]
        self.selects = []
        self.first = self

    def count(self):
        return self._count

    def get_attribute(self, name):
        if name == "data-tag-name":
            return self.tag_name
        if name == "multiple":
            return "" if self.multiple else None
        if name == "role":
            return ""
        if name == "name":
            return "plan"
        if name == "id":
            return "plan"
        if name == "form":
            return "f1"
        return None

    def input_value(self):
        return self.current_value

    def locator(self, selector):
        assert selector == "option"
        return FakeOptionLocator(self.options)

    def is_visible(self):
        return self.visible

    def is_enabled(self):
        return self.enabled

    def select_option(self, value=None, *, label=None, index=None):
        self.selects.append((value, label, index))
        if self.page.event_to_fire:
            self.page.fire(self.page.event_to_fire)
            return []
        if self.page.navigate_on_select:
            self.page._url = "https://example.com/other"
        if index is not None:
            self.current_value = self.options[index].value
        elif label is not None:
            self.current_value = next(option.value for option in self.options if (option.label or option.text) == label)
        else:
            self.current_value = value
        return [self.current_value]


class FakePage:
    def __init__(self, select):
        self._url = URL
        self._closed = False
        self.context = FakeContext()
        self.handlers = {}
        self.select_obj = select
        self.event_to_fire = ""
        self.navigate_on_select = False
        select.page = self

    @property
    def url(self):
        return self._url

    def title(self):
        return "Fake"

    def is_closed(self):
        return self._closed

    def locator(self, selector):
        return self.select_obj

    def on(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)

    def fire(self, event):
        target = self.context if event == "page" else self
        for handler in target.handlers.get(event, []):
            handler(object())


def _driver(select):
    page = FakePage(select)
    d = PlaywrightDriver()
    d._page = page
    d._browser_session_id = SID
    d._page_id = PID
    return d, page, select


def _target(driver, selector="select#plan", **target):
    inspected = driver.inspect_select(selector)
    return driver._resolve_for_test(inspected, target) if hasattr(driver, "_resolve_for_test") else target


def _select(driver, identity, option_identity):
    args = dict(identity)
    args["option_identity"] = option_identity
    return BrowserBackend(driver).execute(ActionRequest("browser.select_option", args))


def _option(driver, **target):
    inspected = driver.inspect_select("select#plan")
    from jarvis.integrations.playwright_driver import _resolve_option_identity
    return _resolve_option_identity(inspected["options"], target)


def test_select_by_value_and_noop():
    d, _page, sel = _driver(FakeSelect(None, current_value="basic"))
    ident = d.inspect_select("select#plan")
    target = _option(d, option_value="pro")
    result = _select(d, ident, target)
    assert result.ok
    assert result.data["current_selected_option"]["option_value"] == "pro"
    assert result.data["mutation_performed"] is True
    assert sel.selects == [("pro", None, None)]

    ident = d.inspect_select("select#plan")
    result = _select(d, ident, target)
    assert result.ok
    assert result.data["mutation_performed"] is False
    assert sel.selects == [("pro", None, None)]


def test_reject_select_count_type_visibility_enabled_multi():
    cases = [
        (FakeSelect(None, count=0), "SELECTOR_COUNT_DRIFT"),
        (FakeSelect(None, count=2), "SELECTOR_COUNT_DRIFT"),
        (FakeSelect(None, tag_name="input"), "UNSUPPORTED_SELECT_TARGET"),
        (FakeSelect(None, visible=False), "ELEMENT_NOT_VISIBLE"),
        (FakeSelect(None, enabled=False), "ELEMENT_NOT_ENABLED"),
        (FakeSelect(None, multiple=True), "UNSUPPORTED_MULTI_SELECT_V0"),
    ]
    for sel, message in cases:
        d, _page, _sel = _driver(sel)
        result = _select(d, d.inspect_select("select#plan"), {"option_value": "pro"})
        assert not result.ok
        assert message in result.message


def test_option_resolution_rejections():
    cases = [
        ({"option_value": "missing"}, "OPTION_TARGET_NOT_FOUND"),
        ({"option_value": "dup"}, "DUPLICATE_OPTION_VALUE"),
        ({"option_label": "Same"}, "DUPLICATE_OPTION_LABEL"),
        ({"option_text": "Same Text"}, "DUPLICATE_OPTION_TEXT"),
        ({"option_index": -1}, "OPTION_INDEX_INVALID"),
        ({"option_value": "disabled"}, "OPTION_DISABLED"),
        ({"option_value": "pro", "option_label": "Pro"}, "EXACTLY_ONE_OPTION_IDENTITY_MODE_REQUIRED"),
        ({}, "EXACTLY_ONE_OPTION_IDENTITY_MODE_REQUIRED"),
    ]
    options = [
        FakeOption("basic", "Basic", label="Basic"),
        FakeOption("pro", "Pro", label="Pro"),
        FakeOption("dup", "Duplicate A", label="A"),
        FakeOption("dup", "Duplicate B", label="B"),
        FakeOption("a", "Same Text", label="Same"),
        FakeOption("b", "Same Text", label="Same"),
        FakeOption("disabled", "Disabled", label="Disabled", disabled=True),
    ]
    for target, message in cases:
        d, _page, _sel = _driver(FakeSelect(None, options=options))
        result = _select(d, d.inspect_select("select#plan"), target)
        assert not result.ok
        assert message in result.message


def test_identity_pre_state_post_and_side_effect_rejections():
    d, page, sel = _driver(FakeSelect(None, current_value="basic"))
    ident = d.inspect_select("select#plan")
    target = _option(d, option_value="pro")
    for key, message in (
        ("browser_session_id", "SESSION_ID_DRIFT"),
        ("page_id", "PAGE_ID_DRIFT"),
        ("metadata_sha256", "SELECT_IDENTITY_DRIFT"),
    ):
        bad = dict(ident)
        bad[key] = ""
        result = _select(d, bad, target)
        assert not result.ok
        assert message in result.message
    page._closed = True
    assert "PAGE_CLOSED" in _select(d, ident, target).message
    page._closed = False
    bad = dict(ident)
    bad["main_frame"] = False
    assert "IFRAME_UNSUPPORTED" in _select(d, bad, target).message

    sel.current_value = "pro"
    assert "PRE_SELECTED_DRIFT" in _select(d, ident, target).message

    for event, message in (
        ("popup", "UNEXPECTED_POPUP"),
        ("page", "UNEXPECTED_NEW_PAGE"),
        ("download", "UNEXPECTED_DOWNLOAD"),
    ):
        d, page, _sel = _driver(FakeSelect(None, current_value="basic"))
        ident = d.inspect_select("select#plan")
        target = _option(d, option_value="pro")
        page.event_to_fire = event
        assert message in _select(d, ident, target).message
    d, page, _sel = _driver(FakeSelect(None, current_value="basic"))
    ident = d.inspect_select("select#plan")
    target = _option(d, option_value="pro")
    page.navigate_on_select = True
    assert "UNEXPECTED_NAVIGATION" in _select(d, ident, target).message


def test_post_mismatch_rejects():
    d, _page, sel = _driver(FakeSelect(None, current_value="basic"))
    ident = d.inspect_select("select#plan")
    target = _option(d, option_value="pro")
    sel.select_option = lambda *args, **kwargs: sel.selects.append((args, kwargs))
    result = _select(d, ident, target)
    assert not result.ok
    assert "REALIZED_STATE_MISMATCH" in result.message


def test_no_generic_boundaries():
    assert "browser.click" in BrowserBackend._supported
    assert "browser.select_option" in BrowserBackend._supported
    assert not hasattr(PlaywrightDriver, "evaluate")
    assert not hasattr(PlaywrightDriver, "js_eval")
