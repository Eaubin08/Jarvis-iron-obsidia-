"""G2-0: stable UIA identity + bounded set_text_by_identity (JarJar executor substrate only).

JarJar stays an executor: no approval, policy or authority here. Identity is
(window_hwnd, process_id, runtime_id) plus drift guards; no fuzzy fallback. Text is set
only through ValuePattern.SetValue on an Edit / Document control, and proven by reading
the SAME control back (digests only, no plaintext in the result).
"""
from __future__ import annotations

import hashlib
import inspect
import subprocess
import sys
import time
from pathlib import Path

import pytest

from jarvis.contracts import ActionRequest, Capability
from jarvis.integrations import uia_identity
from jarvis.integrations.uia_identity import IdentityError, StableUIAController, UIAControlIdentity
from jarvis.structured_ui import StructuredUIBackend

WIN, PID = 1001, 77


class FakeElement:
    def __init__(self, rid, ctype="Edit", cls="Edit", aid="101", handle=5001, value="", password=False,
                 read_only=False, has_value=True, enabled=True, framework="Win32", parent=(42, WIN), pid=PID):
        self.info = dict(runtime_id=rid, native_handle=handle, automation_id=aid, control_type=ctype, class_name=cls,
                         framework_id=framework, process_id=pid, parent_runtime_id=parent, name="", enabled=enabled,
                         visible=True, is_password=password, bounds={"left": 0, "top": 0, "right": 10, "bottom": 10})
        self.value, self.read_only, self.has_value = value, read_only, has_value
        self.transform = None


class FakeSource:
    def __init__(self, elements, window_pid=PID):
        self.items, self.window_pid, self.set_calls = list(elements), window_pid, []

    def window_process_id(self, window_hwnd):
        return self.window_pid if window_hwnd == WIN else None

    def elements(self, window_hwnd):
        return list(self.items) if window_hwnd == WIN else []

    def describe(self, element):
        return dict(element.info)

    def has_value_pattern(self, element):
        return element.has_value

    def is_read_only(self, element):
        return element.read_only

    def get_value(self, element):
        return element.value

    def set_value(self, element, text):
        self.set_calls.append(text)
        element.value = element.transform(text) if element.transform else text


def _identity(**over):
    base = dict(window_hwnd=WIN, process_id=PID, runtime_id=[42, 5001], native_handle=5001, automation_id="101",
                control_type="Edit", class_name="Edit", framework_id="Win32", parent_runtime_id=[42, WIN])
    base.update(over)
    return base


def _ctl(*elements, **kw):
    src = FakeSource(elements or [FakeElement((42, 5001))], **kw)
    return StableUIAController(src), src


# A. identity serialization
def test_identity_roundtrip_and_required_primary_fields():
    ident = UIAControlIdentity.from_dict(_identity())
    assert UIAControlIdentity.from_dict(ident.to_dict()) == ident and ident.runtime_id == (42, 5001)
    for bad in ({"runtime_id": []}, {"process_id": 0}, {"window_hwnd": None}, {"nickname": "x"}):
        with pytest.raises(ValueError):
            UIAControlIdentity.from_dict(_identity(**bad))


# B / C. exact runtime_id
def test_exact_runtime_id_match_and_wrong_runtime_id_fails():
    ctl, _ = _ctl(FakeElement((42, 5001)), FakeElement((42, 5002), handle=5002, aid="102"))
    assert ctl.find_control_by_identity(_identity())["identity"]["runtime_id"] == [42, 5001]
    with pytest.raises(IdentityError):
        ctl.find_control_by_identity(_identity(runtime_id=[42, 9999]))


# D / E. process and window drift
def test_process_and_window_drift_fail():
    ctl, _ = _ctl(window_pid=88)
    with pytest.raises(IdentityError, match="process drift"):
        ctl.find_control_by_identity(_identity())
    ctl, _ = _ctl()
    with pytest.raises(IdentityError, match="window not found"):
        ctl.find_control_by_identity(_identity(window_hwnd=2002))


# F / G. drift guards
@pytest.mark.parametrize("field,value", [("automation_id", "999"), ("control_type", "Document"),
                                         ("class_name", "RichEdit"), ("native_handle", 7777),
                                         ("framework_id", "XAML"), ("parent_runtime_id", [42, 1])])
def test_bound_drift_field_fails(field, value):
    ctl, src = _ctl()
    with pytest.raises(IdentityError, match="drift"):
        ctl.set_text_by_identity(_identity(**{field: value}), "x")
    assert src.set_calls == []


# H / I / J and type / disabled guards
@pytest.mark.parametrize("element,reason", [
    (FakeElement((42, 5001), password=True), "password"),
    (FakeElement((42, 5001), read_only=True), "read-only"),
    (FakeElement((42, 5001), has_value=False), "ValuePattern"),
    (FakeElement((42, 5001), enabled=False), "disabled"),
    (FakeElement((42, 5001), ctype="TitleBar", cls=""), "text-entry"),
])
def test_unsafe_targets_rejected_without_write(element, reason):
    ctl, src = _ctl(element)
    ident = _identity(control_type=element.info["control_type"], class_name=element.info["class_name"])
    with pytest.raises(IdentityError, match=reason):
        ctl.set_text_by_identity(ident, "secret")
    assert src.set_calls == []


def test_password_value_is_never_read():
    ctl, _ = _ctl(FakeElement((42, 5001), password=True, value="hunter2"))
    with pytest.raises(IdentityError, match="password"):
        ctl.read_value_by_identity(_identity())


# K / L. SetValue + exact readback, digests only
def test_set_text_success_with_exact_readback_proof():
    ctl, src = _ctl()
    proof = ctl.set_text_by_identity(_identity(), "Bonjour G2-0")
    digest = hashlib.sha256("Bonjour G2-0".encode()).hexdigest()
    assert src.set_calls == ["Bonjour G2-0"]
    assert proof["value_match"] is True and proof["requested_text_sha256"] == proof["readback_text_sha256"] == digest
    assert "Bonjour G2-0" not in repr(proof)


# M. readback mismatch fails closed
def test_readback_mismatch_fails_closed():
    element = FakeElement((42, 5001))
    element.transform = lambda t: t.upper()
    ctl, _ = _ctl(element)
    with pytest.raises(IdentityError, match="readback mismatch"):
        ctl.set_text_by_identity(_identity(), "lower")


def test_target_destroyed_after_write_fails_closed():
    element = FakeElement((42, 5001))
    ctl, src = _ctl(element)
    original = src.set_value

    def set_and_destroy(el, text):
        original(el, text)
        src.items.clear()
    src.set_value = set_and_destroy
    with pytest.raises(IdentityError, match="not found"):
        ctl.set_text_by_identity(_identity(), "x")


def test_duplicate_runtime_id_is_ambiguous_never_first():
    ctl, _ = _ctl(FakeElement((42, 5001)), FakeElement((42, 5001)))
    with pytest.raises(IdentityError, match="not unique"):
        ctl.find_control_by_identity(_identity())


# N / O / P. no generic surface, no raw objects
def test_public_surface_is_bounded():
    public = {n for n, _ in inspect.getmembers(StableUIAController, inspect.isfunction) if not n.startswith("_")}
    assert public == {"list_controls_uia", "find_control_by_identity", "read_value_by_identity", "set_text_by_identity", "read_checked_by_identity", "set_checked_by_identity"}
    src = inspect.getsource(StableUIAController) + inspect.getsource(uia_identity.PywinautoUIASource)
    for forbidden in ("type_keys", "send_keys", "press", "keyboard", "mouse", ".click(", "iface_invoke", "Invoke("):
        assert forbidden not in src


def test_results_are_sanitized_plain_data():
    ctl, _ = _ctl()
    listing = ctl.list_controls_uia(window_hwnd=WIN)

    def plain(obj):
        if isinstance(obj, dict):
            return all(isinstance(k, str) and plain(v) for k, v in obj.items())
        if isinstance(obj, (list, tuple)):
            return all(plain(v) for v in obj)
        return obj is None or isinstance(obj, (str, int, bool, float))
    assert plain(listing) and plain(ctl.find_control_by_identity(_identity()))


# backend wiring: identity capabilities only with an injected driver
def test_backend_identity_capabilities_require_injected_driver():
    cap = Capability("control.set_text_by_identity", "windows")
    req = ActionRequest("control.set_text_by_identity", {"target_identity": _identity(), "text": "ok"})
    assert not StructuredUIBackend(driver=object()).can_execute(req, cap)
    ctl, src = _ctl()
    backend = StructuredUIBackend(driver=object(), identity_driver=ctl)
    assert backend.can_execute(req, cap)
    result = backend.execute(req)
    assert result.ok and result.data["value_match"] is True and src.set_calls == ["ok"]
    bad = backend.execute(ActionRequest("control.set_text_by_identity", {"target_identity": _identity(), "text": 3}))
    assert not bad.ok


# Q. no live mutation route
def test_live_runtime_registers_no_identity_capability():
    live = (Path(__file__).resolve().parents[1] / "scripts" / "run_jarjar_live.py").read_text(encoding="utf-8")
    for name in ("control.list_uia", "control.read_value", "control.set_text_by_identity", "StableUIAController",
                 "StructuredUIBackend"):
        assert name not in live


# real disposable-fixture validation (Windows only, mutates only the test fixture)
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only UIA integration")
def test_real_fixture_set_text_by_identity_with_readback():
    win32gui = pytest.importorskip("win32gui")
    pytest.importorskip("pywinauto")
    fixture = Path(__file__).with_name("fixtures") / "uia_app.py"
    process = subprocess.Popen([sys.executable, str(fixture)])
    try:
        hwnd = 0
        deadline = time.time() + 15
        while time.time() < deadline and not hwnd:
            hwnd = win32gui.FindWindow("JarvisUIAFixture", None)
            time.sleep(0.2)
        assert hwnd, "fixture window did not appear"
        ctl = StableUIAController()
        listing = ctl.list_controls_uia(window_hwnd=hwnd)
        edit = next(c for c in listing["controls"] if c["identity"]["control_type"] == "Edit")
        assert edit["name"] == "" and edit["is_password"] is False and edit["is_read_only"] is False
        proof = ctl.set_text_by_identity(edit["identity"], "G2-0 exact text")
        assert proof["value_match"] is True
        assert ctl.read_value_by_identity(edit["identity"])["value_sha256"] == proof["requested_text_sha256"]
        wrong = dict(edit["identity"], runtime_id=edit["identity"]["runtime_id"][:-1] + [0])
        with pytest.raises(IdentityError):
            ctl.set_text_by_identity(wrong, "x")
        title_bar = next(c for c in listing["controls"] if c["identity"]["control_type"] == "TitleBar")
        with pytest.raises(IdentityError, match="text-entry"):
            ctl.set_text_by_identity(title_bar["identity"], "x")
    finally:
        process.terminate()
        process.wait(timeout=10)
