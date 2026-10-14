from __future__ import annotations

import hashlib

from jarvis.browser import BrowserBackend
from jarvis.contracts import ActionRequest
from jarvis.integrations.playwright_driver import PlaywrightDriver


SID = "sess-aaaaaaaaaaaaaaaaaaaaaaaaaaaa"
PID = "page-bbbbbbbbbbbbbbbbbbbbbbbb"
PRE_URL = "https://example.com/search"
DEST_URL = "https://example.com/results?q=cats&csrf=token"


def _h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class FakeRequest:
    method = "GET"
    url = DEST_URL
    resource_type = "document"
    post_data = None


class FakeResponse:
    status = 200
    url = DEST_URL

    def __init__(self):
        self.request = FakeRequest()


class FakeContext:
    def __init__(self):
        self.handlers = {}

    def on(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)


class FakeControls:
    def __init__(self, controls):
        self.controls = controls

    def count(self):
        return len(self.controls)

    def nth(self, index):
        return self.controls[index]


class FakeControl:
    def __init__(
        self,
        *,
        tag="input",
        typ="text",
        name="q",
        value="cats",
        autocomplete="",
        enabled=True,
        checked=None,
    ):
        self.tag = tag
        self.typ = typ
        self.name = name
        self.value = value
        self.autocomplete = autocomplete
        self.enabled = enabled
        self.checked = checked

    def get_attribute(self, name):
        return {
            "data-tag-name": self.tag,
            "type": self.typ,
            "name": self.name,
            "value": self.value,
            "autocomplete": self.autocomplete,
            "form": "f1",
        }.get(name)

    def input_value(self):
        return self.value

    def is_enabled(self):
        return self.enabled

    def is_checked(self):
        if self.checked is None:
            raise RuntimeError("not checkable")
        return self.checked


class FakeForm:
    def __init__(self, page, *, count=1, method="get", action="/results", target="", tag="form", controls=None):
        self.page = page
        self._count = count
        self.method = method
        self.action = action
        self.target = target
        self.tag = tag
        self.controls = controls or [
            FakeControl(name="q", value="cats"),
            FakeControl(typ="hidden", name="csrf", value="token"),
        ]
        self.first = self

    def count(self):
        return self._count

    def get_attribute(self, name):
        return {
            "data-tag-name": self.tag,
            "method": self.method,
            "action": self.action,
            "target": self.target,
            "enctype": "application/x-www-form-urlencoded",
            "name": "search",
            "id": "f1",
            "autocomplete": "",
        }.get(name)

    def locator(self, selector):
        assert selector == "input, textarea, select"
        return FakeControls(self.controls)


class FakeSubmitter:
    def __init__(self, page, *, count=1, tag="button", typ="submit", visible=True, enabled=True, form_owner=""):
        self.page = page
        self._count = count
        self.tag = tag
        self.typ = typ
        self.visible = visible
        self.enabled = enabled
        self.form_owner = form_owner
        self.clicks = 0
        self.first = self

    def count(self):
        return self._count

    def get_attribute(self, name):
        return {
            "data-tag-name": self.tag,
            "type": self.typ,
            "name": "go",
            "value": "Search",
            "form": self.form_owner,
        }.get(name)

    def inner_text(self):
        return "Search"

    def is_visible(self):
        return self.visible

    def is_enabled(self):
        return self.enabled

    def click(self):
        self.clicks += 1
        self.page.dispatch_submit()


class FakePage:
    def __init__(self, *, form=None, submitter=None):
        self._url = PRE_URL
        self._closed = False
        self.context = FakeContext()
        self.handlers = {}
        self.form = form or FakeForm(self)
        self.submitter = submitter or FakeSubmitter(self)
        self.form.page = self
        self.submitter.page = self
        self.emit_request = True
        self.emit_response = True
        self.final_url = DEST_URL
        self.post_read_fails = False

    @property
    def url(self):
        return self._url

    def title(self):
        return "Fake"

    def is_closed(self):
        return self._closed

    def locator(self, selector):
        if selector == "form#search":
            return self.form
        if selector == "button#go":
            return self.submitter
        if selector == "body":
            return type("Body", (), {"inner_text": lambda _self: "Results"})()
        raise AssertionError(selector)

    def on(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)

    def dispatch_submit(self):
        if self.emit_request:
            for handler in self.handlers.get("request", []):
                handler(FakeRequest())
        if self.emit_response:
            for handler in self.handlers.get("response", []):
                handler(FakeResponse())
        self._url = self.final_url


def _driver(page):
    d = PlaywrightDriver()
    d._page = page
    d._browser_session_id = SID
    d._page_id = PID
    return d


def _inspect(d):
    return d.inspect_form_submission("form#search", "button#go")


def _submit(d, ident):
    return BrowserBackend(d).execute(ActionRequest("browser.submit_get_navigation", ident))


def test_inspect_binds_get_same_origin_form_submitter_and_hash_only_manifest():
    d = _driver(FakePage())
    ident = _inspect(d)
    assert ident["form_count"] == 1
    assert ident["submitter_count"] == 1
    assert ident["method"] == "get"
    assert ident["same_origin_action"] is True
    assert ident["field_count"] == 2
    assert ident["field_manifest_hash"]
    assert ident["field_manifest"][1]["hidden"] is True
    assert "cats" not in str(ident)
    assert "token" not in str(ident)


def test_form_and_submitter_rejections():
    cases = [
        (FakeForm(None, count=0), FakeSubmitter(None), "FORM_COUNT_NOT_ONE"),
        (FakeForm(None, count=2), FakeSubmitter(None), "FORM_COUNT_NOT_ONE"),
        (FakeForm(None, tag="div"), FakeSubmitter(None), "FORM_TAG_REQUIRED"),
        (FakeForm(None, method="post"), FakeSubmitter(None), "FORM_METHOD_NOT_GET"),
        (FakeForm(None, action="https://other.example/results"), FakeSubmitter(None), "CROSS_ORIGIN_ACTION_UNSUPPORTED"),
        (FakeForm(None, target="_blank"), FakeSubmitter(None), "FORM_TARGET_NEW_CONTEXT_UNSUPPORTED"),
        (FakeForm(None), FakeSubmitter(None, count=0), "SUBMITTER_COUNT_NOT_ONE"),
        (FakeForm(None), FakeSubmitter(None, count=2), "SUBMITTER_COUNT_NOT_ONE"),
        (FakeForm(None), FakeSubmitter(None, tag="a", typ=""), "UNSUPPORTED_SUBMITTER_TARGET"),
        (FakeForm(None), FakeSubmitter(None, visible=False), "SUBMITTER_NOT_VISIBLE"),
        (FakeForm(None), FakeSubmitter(None, enabled=False), "SUBMITTER_NOT_ENABLED"),
        (FakeForm(None), FakeSubmitter(None, form_owner="other"), "SUBMITTER_FORM_OWNER_MISMATCH"),
    ]
    for form, submitter, message in cases:
        page = FakePage(form=form, submitter=submitter)
        d = _driver(page)
        result = _submit(d, _inspect(d))
        assert not result.ok
        assert message in result.message


def test_sensitive_fields_rejected_and_no_plaintext_proof():
    cases = [
        (FakeControl(typ="password", name="pw", value="secret"), "PASSWORD_FORM_DEFERRED"),
        (FakeControl(name="otp", value="123456", autocomplete="one-time-code"), "OTP_FORM_DEFERRED"),
        (FakeControl(name="cc", value="4111111111111111", autocomplete="cc-number"), "PAYMENT_FORM_DEFERRED"),
    ]
    for control, message in cases:
        form = FakeForm(None, controls=[control])
        d = _driver(FakePage(form=form))
        ident = _inspect(d)
        assert "secret" not in str(ident)
        assert "411111" not in str(ident)
        result = _submit(d, ident)
        assert not result.ok
        assert message in result.message


def test_success_observes_request_response_navigation_and_single_activation():
    page = FakePage()
    d = _driver(page)
    result = _submit(d, _inspect(d))
    assert result.ok
    assert page.submitter.clicks == 1
    assert result.data["execution_state"] == "POSTCONDITION_CONFIRMED"
    assert result.data["request_observed"] is True
    assert result.data["request_method"] == "GET"
    assert result.data["response_observed"] is True
    assert result.data["transport_proof"] == "STRONG"
    assert result.data["navigation_proof"] == "STRONG"
    assert result.data["application_proof"] == "NOT_CLAIMED"
    assert "cats" not in str(result.data)
    assert "token" not in str(result.data)


def test_uncertainty_model_after_dispatch_and_not_dispatched_before_request():
    page = FakePage()
    page.emit_response = False
    d = _driver(page)
    result = _submit(d, _inspect(d))
    assert result.ok
    assert result.data["execution_state"] == "DISPATCHED_OUTCOME_UNCERTAIN"
    assert result.data["request_observed"] is True

    page = FakePage()
    page.emit_request = False
    d = _driver(page)
    result = _submit(d, _inspect(d))
    assert not result.ok
    assert "REQUEST_NOT_OBSERVED" in result.message

    page = FakePage()
    page.final_url = "https://other.example/results"
    d = _driver(page)
    result = _submit(d, _inspect(d))
    assert result.ok
    assert result.data["execution_state"] == "DISPATCHED_OUTCOME_UNCERTAIN"


def test_toctou_manifest_drift_rejects_before_dispatch_and_no_generic_submit_surface():
    page = FakePage()
    d = _driver(page)
    ident = _inspect(d)
    page.form.controls[0].value = "dogs"
    result = _submit(d, ident)
    assert not result.ok
    assert "FORM_SUBMISSION_IDENTITY_DRIFT" in result.message
    assert page.submitter.clicks == 0

    backend = BrowserBackend(d)
    assert not backend.can_execute(ActionRequest("browser.submit", {"selector": "form"}), type("C", (), {"backend_family": "browser"})())
    assert not hasattr(PlaywrightDriver, "submit")
    assert not hasattr(PlaywrightDriver, "press")
    assert not hasattr(PlaywrightDriver, "evaluate")
    assert not hasattr(PlaywrightDriver, "request_submit")
