from __future__ import annotations
import sys
from pathlib import Path
import pytest
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from jarvis.integrations.uia_identity import (
    TOGGLE_INDETERMINATE, TOGGLE_OFF, TOGGLE_ON,
    IdentityError, StableUIAController,
)
WIN, PID = 2001, 88

class FakeElement:
    def __init__(self, rid, ctype="CheckBox", cls="Button", aid="chk1",
                 enabled=True, toggle_state=TOGGLE_OFF, has_toggle=True, pid=PID,
                 parent=(42, WIN)):
        self.info = dict(runtime_id=rid, native_handle=0, automation_id=aid,
                         control_type=ctype, class_name=cls, framework_id="Win32",
                         process_id=pid, parent_runtime_id=parent, name="chkbox",
                         enabled=enabled, visible=True, is_password=False,
                         bounds={"left":0,"top":0,"right":100,"bottom":20})
        self.toggle_state = toggle_state
        self.has_toggle = has_toggle
        self.toggle_calls = 0
    def do_toggle(self):
        self.toggle_calls += 1
        self.toggle_state = TOGGLE_ON if self.toggle_state == TOGGLE_OFF else TOGGLE_OFF

class FakeSource:
    def __init__(self, elements, window_pid=PID):
        self.items, self.window_pid = list(elements), window_pid
    def window_process_id(self, hwnd):
        return self.window_pid if hwnd == WIN else None
    def elements(self, hwnd):
        return list(self.items) if hwnd == WIN else []
    def describe(self, el):
        return dict(el.info)
    def has_value_pattern(self, el):
        return False
    def is_read_only(self, el):
        return False
    def get_value(self, el):
        return ""
    def set_value(self, el, t):
        pass
    def has_toggle_pattern(self, el):
        return el.has_toggle
    def get_toggle_state(self, el):
        return el.toggle_state
    def do_toggle(self, el):
        el.do_toggle()

def _ident(**kw):
    base = dict(window_hwnd=WIN, process_id=PID, runtime_id=[10,20,30],
                native_handle=0, automation_id="chk1", control_type="CheckBox",
                class_name="Button", framework_id="Win32", parent_runtime_id=[42,WIN])
    base.update(kw)
    return base

def _ctrl(toggle_state=TOGGLE_OFF, ctype="CheckBox", enabled=True, has_toggle=True):
    el = FakeElement((10,20,30), ctype=ctype, enabled=enabled,
                     toggle_state=toggle_state, has_toggle=has_toggle)
    src = FakeSource([el])
    return StableUIAController(src), el

def test_read_off():
    ctl, _ = _ctrl(TOGGLE_OFF)
    r = ctl.read_checked_by_identity(_ident())
    assert r["ok"] and not r["checked"] and not r["indeterminate"]

def test_read_on():
    ctl, _ = _ctrl(TOGGLE_ON)
    r = ctl.read_checked_by_identity(_ident())
    assert r["checked"] and not r["indeterminate"]

def test_read_indeterminate():
    ctl, _ = _ctrl(TOGGLE_INDETERMINATE)
    r = ctl.read_checked_by_identity(_ident())
    assert r["toggle_state"] == TOGGLE_INDETERMINATE and r["indeterminate"]

def test_read_wrong_type_rejected():
    ctl, _ = _ctrl(ctype="Button")
    with pytest.raises(IdentityError, match="not CheckBox"):
        ctl.read_checked_by_identity(_ident(control_type="Button"))

def test_read_no_toggle_rejected():
    ctl, _ = _ctrl(has_toggle=False)
    with pytest.raises(IdentityError, match="TogglePattern"):
        ctl.read_checked_by_identity(_ident())

def test_read_includes_identity():
    ctl, _ = _ctrl(TOGGLE_ON)
    r = ctl.read_checked_by_identity(_ident())
    assert r["target_identity"]["automation_id"] == "chk1"

def test_set_off_to_on():
    ctl, el = _ctrl(TOGGLE_OFF)
    r = ctl.set_checked_by_identity(_ident(), True)
    assert el.toggle_calls == 1 and r["mutation_performed"] and r["post_toggle_state"] == TOGGLE_ON
    assert r["realized_state_verified"] and r["proof"] == "uia_toggle_pattern_readback"

def test_set_on_to_off():
    ctl, el = _ctrl(TOGGLE_ON)
    r = ctl.set_checked_by_identity(_ident(), False)
    assert el.toggle_calls == 1 and r["post_toggle_state"] == TOGGLE_OFF

def test_set_on_to_on_noop():
    ctl, el = _ctrl(TOGGLE_ON)
    r = ctl.set_checked_by_identity(_ident(), True)
    assert el.toggle_calls == 0 and not r["mutation_performed"] and r["post_toggle_state"] == TOGGLE_ON

def test_set_off_to_off_noop():
    ctl, el = _ctrl(TOGGLE_OFF)
    r = ctl.set_checked_by_identity(_ident(), False)
    assert el.toggle_calls == 0 and r["post_toggle_state"] == TOGGLE_OFF

def test_set_indeterminate_rejected():
    ctl, el = _ctrl(TOGGLE_INDETERMINATE)
    with pytest.raises(IdentityError, match="indeterminate"):
        ctl.set_checked_by_identity(_ident(), True)
    assert el.toggle_calls == 0

def test_set_wrong_type_rejected():
    ctl, el = _ctrl(ctype="Button")
    with pytest.raises(IdentityError, match="not CheckBox"):
        ctl.set_checked_by_identity(_ident(control_type="Button"), True)
    assert el.toggle_calls == 0

def test_set_disabled_rejected():
    ctl, el = _ctrl(enabled=False)
    with pytest.raises(IdentityError, match="disabled"):
        ctl.set_checked_by_identity(_ident(), True)
    assert el.toggle_calls == 0

def test_set_no_toggle_rejected():
    ctl, el = _ctrl(has_toggle=False)
    with pytest.raises(IdentityError, match="TogglePattern"):
        ctl.set_checked_by_identity(_ident(), True)
    assert el.toggle_calls == 0

def test_set_non_bool_rejected():
    ctl, el = _ctrl()
    with pytest.raises(ValueError, match="bool"):
        ctl.set_checked_by_identity(_ident(), 1)
    assert el.toggle_calls == 0

def test_set_identity_mismatch_rejected():
    ctl, el = _ctrl()
    with pytest.raises(IdentityError):
        ctl.set_checked_by_identity(_ident(runtime_id=[99,99,99]), True)
    assert el.toggle_calls == 0

def test_set_window_not_found_rejected():
    ctl, el = _ctrl()
    with pytest.raises(IdentityError):
        ctl.set_checked_by_identity(_ident(window_hwnd=9999), True)
    assert el.toggle_calls == 0

def test_set_process_drift_rejected():
    ctl, el = _ctrl()
    with pytest.raises(IdentityError):
        ctl.set_checked_by_identity(_ident(process_id=9999), True)
    assert el.toggle_calls == 0

class _DefiantSrc(FakeSource):
    def do_toggle(self, el):
        el.toggle_calls += 1

def test_post_state_mismatch_fail_closed():
    el = FakeElement((10,20,30), toggle_state=TOGGLE_OFF)
    ctl = StableUIAController(_DefiantSrc([el]))
    with pytest.raises(IdentityError, match="realized state mismatch"):
        ctl.set_checked_by_identity(_ident(), True)

def test_sanitized_includes_toggle():
    ctl, _ = _ctrl(has_toggle=True)
    r = ctl.list_controls_uia(window_hwnd=WIN)
    assert "toggle" in r["controls"][0]["patterns"]

def test_sanitized_no_toggle_if_absent():
    ctl, _ = _ctrl(has_toggle=False)
    r = ctl.list_controls_uia(window_hwnd=WIN)
    assert "toggle" not in r["controls"][0]["patterns"]


def test_noop_is_verified_by_an_independent_post_read():
    # G2-B1 contract: a no-op is still proven by re-acquiring the SAME identity and reading
    # the state again (here the state changes between the two reads -> fail closed)
    ctl, el = _ctrl(TOGGLE_ON)
    src = ctl._source
    reads = {"n": 0}
    original = src.get_toggle_state

    def flipping_read(element):
        reads["n"] += 1
        return TOGGLE_ON if reads["n"] == 1 else TOGGLE_OFF
    src.get_toggle_state = flipping_read
    with pytest.raises(IdentityError, match="realized state mismatch"):
        ctl.set_checked_by_identity(_ident(), True)
    assert reads["n"] == 2 and el.toggle_calls == 0
    src.get_toggle_state = original
