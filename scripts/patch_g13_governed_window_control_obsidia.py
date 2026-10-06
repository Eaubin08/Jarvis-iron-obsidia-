from __future__ import annotations

from pathlib import Path
import shutil
import uuid

ROOT = Path.home() / "Desktop" / "obsidia-openjarvis-install-v0"
BRIDGE = ROOT / "scripts" / "jarjar_executor_bridge_v0.py"
PC2 = ROOT / "scripts" / "obsidia_pc_capabilities_v2.py"


def _backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".g13_window_control.bak")
    if not bak.exists():
        shutil.copy2(path, bak)


def patch_bridge() -> None:
    text = BRIDGE.read_text(encoding="utf-8")
    _backup(BRIDGE)
    marker = "# === G13 governed window control ==="
    if marker in text:
        text = text.split(marker, 1)[0].rstrip()

    payload = r'''
# === G13 governed window control ===
def _g13_window_control_by_hwnd(self, hwnd: int, action: str, monitor_index: int | None = None) -> dict:
    if action in {"minimize", "maximize", "restore"}:
        result = self._backend.driver._window_state_hwnd(int(hwnd), action)
        return {"ok": True, "data": result, "action": action}
    if action == "move_monitor":
        if not isinstance(monitor_index, int) or monitor_index < 1:
            return {"ok": False, "error": "MONITOR_INDEX_REQUIRED"}
        result = self._backend.driver._move_window_to_monitor_hwnd(int(hwnd), monitor_index)
        return {"ok": True, "data": result, "action": action}
    return {"ok": False, "error": "WINDOW_CONTROL_UNSUPPORTED"}


def _g13_window_observe(self, hwnd: int) -> dict:
    try:
        import win32gui
    except ImportError as exc:
        return {"ok": False, "error": f"PYWIN32_MISSING:{exc}"}
    if not win32gui.IsWindow(int(hwnd)):
        return {"ok": False, "error": "WINDOW_NOT_FOUND"}
    rect = win32gui.GetWindowRect(int(hwnd))
    return {
        "ok": True,
        "hwnd": int(hwnd),
        "title": win32gui.GetWindowText(int(hwnd)).strip(),
        "is_iconic": bool(win32gui.IsIconic(int(hwnd))),
        "is_zoomed": bool(win32gui.IsZoomed(int(hwnd))),
        "rect": tuple(int(v) for v in rect),
    }


if not hasattr(JarJarWindowsExecutor, "window_control_by_hwnd"):
    JarJarWindowsExecutor.window_control_by_hwnd = _g13_window_control_by_hwnd
if not hasattr(JarJarWindowsExecutor, "window_observe"):
    JarJarWindowsExecutor.window_observe = _g13_window_observe
'''
    BRIDGE.write_text(text.rstrip() + "\n\n" + payload.strip() + "\n", encoding="utf-8")


def patch_pc2() -> None:
    text = PC2.read_text(encoding="utf-8")
    _backup(PC2)
    marker = "# === G13 governed window control ==="
    if marker in text:
        text = text.split(marker, 1)[0].rstrip()

    payload = r'''
# === G13 governed window control ===
import uuid as _g13_window_uuid

OP_WINDOW_CONTROL = "V2_WINDOW_CONTROL"
_CAP_WINDOW_CONTROL_PREPARE = "PC_V2_WINDOW_CONTROL_PREPARE"
_CAP_WINDOW_CONTROL_EXECUTE = "PC_V2_WINDOW_CONTROL_EXECUTE"


def pc_v2_window_control_prepare(
        action, title, *, stores_base_dir, session_id="", monitor_index=None, executor=None):
    if executor is None:
        return _prep_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_PREPARE, "EXECUTOR_REQUIRED", session_id)

    action = str(action or "").strip().lower()
    if action not in {"minimize", "maximize", "restore", "move_monitor"}:
        return _prep_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_PREPARE, "WINDOW_ACTION_UNSUPPORTED", session_id)

    if action == "move_monitor" and (not isinstance(monitor_index, int) or monitor_index < 1):
        return _prep_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_PREPARE, "MONITOR_INDEX_REQUIRED", session_id)

    resolved = executor.find_window(str(title or "").strip())
    if not resolved.get("ok"):
        return _prep_rej(
            OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_PREPARE,
            str(resolved.get("error") or "WINDOW_NOT_FOUND"), session_id,
        )

    invocation_id = _g13_window_uuid.uuid4().hex
    hwnd = int(resolved["hwnd"])
    obs = executor.window_observe(hwnd)
    if not obs.get("ok"):
        return _prep_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_PREPARE, "WINDOW_PRE_STATE_READ_FAILED", session_id)

    desc = {
        "action": action,
        "title": title,
        "resolved_title": resolved.get("title") or title,
        "hwnd": hwnd,
        "monitor_index": monitor_index,
        "pre_state": obs,
        "session_id": session_id,
        "invocation_id": invocation_id,
        "operation_type": OP_WINDOW_CONTROL,
    }
    eah = _eah(OP_WINDOW_CONTROL, desc)
    child = _v2id("chd", eah + str(hwnd) + invocation_id)
    v2id = _v2id("v2x", eah + session_id + invocation_id)
    mh = _sha16(json.dumps(desc, sort_keys=True, default=str))
    dh = _persist_desc(v2id, OP_WINDOW_CONTROL, eah, desc, _stores(stores_base_dir)["v2exec"])

    return {
        "status": PREPARED_AWAITING_HUMAN_APPROVAL,
        "j5_phase": "PREPARE",
        "operation_type": OP_WINDOW_CONTROL,
        "jarvis_authority": JARVIS_AUTHORITY,
        "decision_authority": KX_DECISION_AUTHORITY,
        "execution_authority_hash": eah,
        "v2_exec_id": v2id,
        "child_id": child,
        "manifest_hash": mh,
        "desc_hash": dh,
        "action": action,
        "resolved_title": desc["resolved_title"],
        "hwnd": hwnd,
        "monitor_index": monitor_index,
        "receipt": _rcpt(
            _CAP_WINDOW_CONTROL_PREPARE, OP_WINDOW_CONTROL,
            PREPARED_AWAITING_HUMAN_APPROVAL, session_id,
            action=action, resolved_title=desc["resolved_title"], hwnd=hwnd,
            monitor_index=monitor_index,
        ),
    }


def pc_v2_window_control_execute(
        prepared_result, human_authorized_eah, human_authorization_reference,
        *, stores_base_dir, session_id="", executor=None):
    if prepared_result.get("status") != PREPARED_AWAITING_HUMAN_APPROVAL:
        return _exec_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_EXECUTE, "PREPARED_AWAITING_HUMAN_APPROVAL_REQUIRED", session_id)
    if prepared_result.get("j5_phase") != "PREPARE":
        return _exec_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_EXECUTE, "PREPARE_PHASE_REQUIRED", session_id)

    exp_eah = prepared_result.get("execution_authority_hash", "")
    if human_authorized_eah != exp_eah:
        return _exec_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_EXECUTE, EAH_MISMATCH, session_id)
    if not (human_authorization_reference or "").strip():
        return _exec_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_EXECUTE, "HUMAN_AUTHORIZATION_REFERENCE_REQUIRED", session_id)
    if executor is None:
        return _exec_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_EXECUTE, "EXECUTOR_REQUIRED", session_id)

    st = _stores(stores_base_dir)
    v2id = prepared_result.get("v2_exec_id", "")
    child = prepared_result.get("child_id", "")
    mh = prepared_result.get("manifest_hash", "")
    dh = prepared_result.get("desc_hash", "")
    rec = _load_desc(v2id, st["v2exec"])
    if not rec or rec.get("eah") != exp_eah:
        return _exec_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_EXECUTE, "DESCRIPTOR_EAH_MISMATCH", session_id)

    desc = rec["descriptor"]
    hwnd = int(desc["hwnd"])
    action = desc["action"]
    monitor_index = desc.get("monitor_index")

    pre_now = executor.window_observe(hwnd)
    if not pre_now.get("ok"):
        return _exec_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_EXECUTE, "WINDOW_PRE_STATE_DRIFT", session_id)

    apr = _approval(v2id, child, exp_eah, f"{action}:{hwnd}")
    apv_id = apr["approval_id"]
    ar = _E.store_approval_artifact(apr, st["approval"])
    if ar.get("status") not in ("STORED", "IDEMPOTENT_ALREADY_EXISTS"):
        return _exec_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_EXECUTE, "APPROVAL_STORE_FAILED", session_id)

    kx = _kx108_pre(
        v2id, child, exp_eah, apv_id, dh, "", mh,
        [f"OS_WINDOW:{action}"], OP_WINDOW_CONTROL, kxpre=st["kxpre"],
        physical_state_anchor=f"{hwnd}:{pre_now.get('is_iconic')}:{pre_now.get('is_zoomed')}:{pre_now.get('rect')}",
        state_anchor_kind="PHYSICAL_PRE_STATE",
    )
    if not kx.get("verify_ok"):
        return _exec_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_EXECUTE, "KX108_PRE_FAILED", session_id)
    gate = kx.get("x108_gate", "")
    if gate != "ALLOW":
        return _exec_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_EXECUTE, "KX108_PRE_GATE:" + gate, session_id)

    ex = executor.window_control_by_hwnd(hwnd, action, monitor_index)
    if not ex.get("ok"):
        return _exec_rej(
            OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_EXECUTE,
            "JARJAR_EXECUTOR_FAILED:" + str(ex.get("error") or ""),
            session_id,
        )

    post = executor.window_observe(hwnd)
    if not post.get("ok"):
        return _exec_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_EXECUTE, "POST_STATE_READ_FAILED", session_id)

    verified = False
    if action == "minimize":
        verified = post.get("is_iconic") is True
    elif action == "maximize":
        verified = post.get("is_zoomed") is True
    elif action == "restore":
        verified = post.get("is_iconic") is False and post.get("is_zoomed") is False
    elif action == "move_monitor":
        before_rect = tuple(desc.get("pre_state", {}).get("rect") or ())
        after_rect = tuple(post.get("rect") or ())
        verified = bool(before_rect and after_rect and before_rect != after_rect)

    if not verified:
        return _exec_rej(OP_WINDOW_CONTROL, _CAP_WINDOW_CONTROL_EXECUTE, "REALIZED_STATE_MISMATCH", session_id)

    return {
        "status": EXECUTED_OK,
        "j5_phase": "EXECUTE",
        "operation_type": OP_WINDOW_CONTROL,
        "jarvis_authority": JARVIS_AUTHORITY,
        "decision_authority": KX_DECISION_AUTHORITY,
        "kx108_pre_gate": gate,
        "human_authorization_consumed": True,
        "action": action,
        "resolved_title": desc.get("resolved_title"),
        "hwnd": hwnd,
        "monitor_index": monitor_index,
        "proof_strength": "STRONG",
        "realized_state_verified": True,
        "post_state": post,
        "receipt": _rcpt(
            _CAP_WINDOW_CONTROL_EXECUTE, OP_WINDOW_CONTROL, EXECUTED_OK, session_id,
            kx108_pre_gate=gate, action=action, hwnd=hwnd,
            monitor_index=monitor_index, realized_state_verified=True,
        ),
    }
'''
    PC2.write_text(text.rstrip() + "\n\n" + payload.strip() + "\n", encoding="utf-8")


def main() -> None:
    if not BRIDGE.exists() or not PC2.exists():
        raise SystemExit(f"Obsidia worktree not found under {ROOT}")
    patch_bridge()
    patch_pc2()
    print("G13 governed window-control Obsidia patch: PASS")
    print(f"bridge={BRIDGE}")
    print(f"pc2={PC2}")


if __name__ == "__main__":
    main()
