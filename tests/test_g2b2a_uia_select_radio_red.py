from __future__ import annotations
import sys
from pathlib import Path
import pytest
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from jarvis.integrations.uia_identity import (
    RADIO_CONTROL_TYPE, IdentityError, StableUIAController,
)
WIN, PID = 3001, 99

class FakeRadioElement:
    def __init__(self, rid, ctype="RadioButton", cls="Button", aid="rad1",
                 enabled=True, is_selected=False, has_si=True, pid=PID,
                 parent=(50, WIN)):
        self.info = dict(runtime_id=rid, native_handle=0, automation_id=aid,
                         control_type=ctype, class_name=cls, framework_id="Win32",
                         process_id=pid, parent_runtime_id=parent, name="radio",
                         enabled=enabled, visible=True, is_password=False,
                         bounds={"left":0,"top":0,"right":100,"bottom":20})
        self._is_selected = is_selected
        self.has_si = has_si
        self.select_calls = 0
    def do_select(self):
        self.select_calls += 1
        self._is_selected = True

class FakeRadioSource:
    def __init__(self, elements, window_pid=PID):
        self.items, self.window_pid = list(elements), window_pid
    def window_process_id(self, hwnd):
        return self.window_pid if hwnd == WIN else None
    def elements(self, hwnd):
        return list(self.items) if hwnd == WIN else []
    def describe(self, el):
        return dict(el.info)
    def has_value_pattern(self, el): return False
    def is_read_only(self, el): return False
    def get_value(self, el): return ""
    def set_value(self, el, t): pass
    def has_toggle_pattern(self, el): return False
    def get_toggle_state(self, el): return 0
    def do_toggle(self, el): pass
    def has_selection_item_pattern(self, el): return el.has_si
    def get_is_selected(self, el): return el._is_selected
    def do_select(self, el): el.do_select()

def _ident(**kw):
    base = dict(window_hwnd=WIN, process_id=PID, runtime_id=[10,20,30],
                native_handle=0, automation_id="rad1", control_type="RadioButton",
                class_name="Button", framework_id="Win32", parent_runtime_id=[50,WIN])
    base.update(kw)
    return base

def _ctrl(is_selected=False, ctype="RadioButton", enabled=True, has_si=True):
    el = FakeRadioElement((10,20,30), ctype=ctype, enabled=enabled,
                          is_selected=is_selected, has_si=has_si)
    src = FakeRadioSource([el])
    return StableUIAController(src), el

def test_read_unselected():
    ctl, _ = _ctrl(is_selected=False)
    r = ctl.read_selected_by_identity(_ident())
    assert r["ok"] and r["is_selected"] is False

def test_read_selected():
    ctl, _ = _ctrl(is_selected=True)
    r = ctl.read_selected_by_identity(_ident())
    assert r["ok"] and r["is_selected"] is True

def test_select_unselected():
    ctl, el = _ctrl(is_selected=False)
    r = ctl.select_radio_by_identity(_ident())
    assert el.select_calls == 1
    assert r["ok"] and r["post_is_selected"] is True
    assert r["mutation_performed"] is True
    assert r["realized_state_verified"] is True
    assert r["proof"] == "uia_selection_item_pattern_readback"

def test_select_already_selected_noop():
    ctl, el = _ctrl(is_selected=True)
    r = ctl.select_radio_by_identity(_ident())
    assert el.select_calls == 0
    assert r["ok"] and r["mutation_performed"] is False
    assert r["post_is_selected"] is True
    assert r["realized_state_verified"] is True

def test_select_wrong_type_rejected():
    ctl, el = _ctrl(ctype="CheckBox")
    with pytest.raises(IdentityError, match="not RadioButton"):
        ctl.select_radio_by_identity(_ident(control_type="CheckBox"))
    assert el.select_calls == 0

def test_read_wrong_type_rejected():
    ctl, _ = _ctrl(ctype="CheckBox")
    with pytest.raises(IdentityError, match="not RadioButton"):
        ctl.read_selected_by_identity(_ident(control_type="CheckBox"))

def test_select_disabled_rejected():
    ctl, el = _ctrl(enabled=False)
    with pytest.raises(IdentityError, match="disabled"):
        ctl.select_radio_by_identity(_ident())
    assert el.select_calls == 0

def test_select_no_pattern_rejected():
    ctl, el = _ctrl(has_si=False)
    with pytest.raises(IdentityError, match="SelectionItemPattern"):
        ctl.select_radio_by_identity(_ident())
    assert el.select_calls == 0

def test_read_no_pattern_rejected():
    ctl, _ = _ctrl(has_si=False)
    with pytest.raises(IdentityError, match="SelectionItemPattern"):
        ctl.read_selected_by_identity(_ident())

def test_select_wrong_runtime_id_rejected():
    ctl, el = _ctrl()
    with pytest.raises(IdentityError):
        ctl.select_radio_by_identity(_ident(runtime_id=[99,99,99]))
    assert el.select_calls == 0

def test_select_wrong_window_rejected():
    ctl, el = _ctrl()
    with pytest.raises(IdentityError):
        ctl.select_radio_by_identity(_ident(window_hwnd=9999))
    assert el.select_calls == 0

def test_select_process_drift_rejected():
    ctl, el = _ctrl()
    with pytest.raises(IdentityError):
        ctl.select_radio_by_identity(_ident(process_id=9999))
    assert el.select_calls == 0

class _DefiantSrc(FakeRadioSource):
    def do_select(self, el):
        el.select_calls += 1

def test_post_state_false_fail_closed():
    el = FakeRadioElement((10,20,30), is_selected=False)
    ctl = StableUIAController(_DefiantSrc([el]))
    with pytest.raises(IdentityError, match="realized state mismatch"):
        ctl.select_radio_by_identity(_ident())
    assert el.select_calls == 1

def test_noop_independent_post_read():
    ctl, el = _ctrl(is_selected=True)
    src = ctl._source
    reads = {"n": 0}
    def flipping_read(element):
        reads["n"] += 1
        return True if reads["n"] == 1 else False
    src.get_is_selected = flipping_read
    with pytest.raises(IdentityError, match="realized state mismatch"):
        ctl.select_radio_by_identity(_ident())
    assert reads["n"] == 2 and el.select_calls == 0

def test_sanitized_includes_selection_item():
    ctl, _ = _ctrl(has_si=True)
    r = ctl.list_controls_uia(window_hwnd=WIN)
    assert "selection_item" in r["controls"][0]["patterns"]

def test_sanitized_no_selection_item_if_absent():
    ctl, _ = _ctrl(has_si=False)
    r = ctl.list_controls_uia(window_hwnd=WIN)
    assert "selection_item" not in r["controls"][0]["patterns"]

def test_radio_control_type_constant():
    assert RADIO_CONTROL_TYPE == "RadioButton"

def test_read_includes_identity():
    ctl, _ = _ctrl(is_selected=False)
    r = ctl.read_selected_by_identity(_ident())
    assert r["target_identity"]["automation_id"] == "rad1"
