"""Idempotent local patcher for G13 governed master-volume support in Obsidia.

Targets only:
- scripts/jarjar_executor_bridge_v0.py
- scripts/obsidia_pc_capabilities_v2.py

Fails closed when expected anchors are absent. Creates .g13_audio.bak backups once.
"""
from __future__ import annotations

from pathlib import Path
import re
import shutil


ROOT = Path(__file__).resolve().parents[2] / "obsidia-openjarvis-install-v0"
BRIDGE = ROOT / "scripts" / "jarjar_executor_bridge_v0.py"
PC2 = ROOT / "scripts" / "obsidia_pc_capabilities_v2.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def backup(path: Path) -> None:
    target = path.with_suffix(path.suffix + ".g13_audio.bak")
    if not target.exists():
        shutil.copy2(path, target)


def patch_bridge() -> None:
    text = BRIDGE.read_text(encoding="utf-8")
    backup(BRIDGE)

    anchor = '''    def find_window(self, title: str) -> dict:
'''
    addition = '''    def audio_status(self) -> dict:
        """Read-only physical master-volume observation."""
        result = self._backend.execute(self._req("audio.status"))
        if not result.ok:
            return {"ok": False, "error": "AUDIO_STATUS_FAILED:" + result.message,
                    "executor": self.EXECUTOR_BACKEND, "capability": "audio.status"}
        volume = result.data.get("volume_percent")
        muted = result.data.get("muted")
        if not isinstance(volume, int):
            return {"ok": False, "error": "AUDIO_STATUS_INVALID",
                    "executor": self.EXECUTOR_BACKEND, "capability": "audio.status"}
        return {"ok": True, "volume_percent": volume, "muted": bool(muted),
                "executor": self.EXECUTOR_BACKEND, "capability": "audio.status"}

    def set_volume(self, percent: int) -> dict:
        """Physical mutation only. Authorization is external and KX108-only."""
        if not isinstance(percent, int) or isinstance(percent, bool) or not 0 <= percent <= 100:
            return {"ok": False, "error": "VOLUME_PERCENT_INVALID",
                    "executor": self.EXECUTOR_BACKEND, "capability": "audio.set_volume"}
        result = self._backend.execute(self._req("audio.set_volume", percent=percent))
        if not result.ok:
            return {"ok": False, "error": result.message,
                    "executor": self.EXECUTOR_BACKEND, "capability": "audio.set_volume"}
        observed = result.data.get("volume_percent")
        return {"ok": True, "requested_percent": percent, "volume_percent": observed,
                "muted": result.data.get("muted"),
                "executor": self.EXECUTOR_BACKEND, "capability": "audio.set_volume"}

    def find_window(self, title: str) -> dict:
'''
    text = replace_once(text, anchor, addition, "bridge audio methods")

    old_ops = '"operations": ["MOVE_FILE", "CREATE_DIR", "ROLLBACK_MOVE_FILE", "APP_OPEN_RESOLVE", "APP_OPEN_BY_TARGET", "UIA_LIST_CONTROLS_BY_IDENTITY", "UIA_FIND_BY_IDENTITY", "UIA_READ_VALUE_BY_IDENTITY", "UIA_SET_TEXT_BY_IDENTITY", "UIA_LIST_CONTROLS_UIA", "UIA_READ_CHECKED", "UIA_SET_CHECKED"],'
    new_ops = '"operations": ["MOVE_FILE", "CREATE_DIR", "ROLLBACK_MOVE_FILE", "APP_OPEN_RESOLVE", "APP_OPEN_BY_TARGET", "AUDIO_STATUS", "AUDIO_SET_VOLUME", "UIA_LIST_CONTROLS_BY_IDENTITY", "UIA_FIND_BY_IDENTITY", "UIA_READ_VALUE_BY_IDENTITY", "UIA_SET_TEXT_BY_IDENTITY", "UIA_LIST_CONTROLS_UIA", "UIA_READ_CHECKED", "UIA_SET_CHECKED"],'
    if old_ops in text:
        text = text.replace(old_ops, new_ops, 1)

    BRIDGE.write_text(text, encoding="utf-8")


def patch_pc2() -> None:
    text = PC2.read_text(encoding="utf-8")
    backup(PC2)

    text = replace_once(
        text,
        'OP_APP_OPEN                 = "V2_APP_OPEN"\n',
        'OP_APP_OPEN                 = "V2_APP_OPEN"\nOP_AUDIO_VOLUME             = "V2_AUDIO_VOLUME"\n',
        "pc2 audio op",
    )
    text = replace_once(
        text,
        '_CAP_AOPEN_EXECUTE  = "PC_V2_APP_OPEN_EXECUTE"\n',
        '_CAP_AOPEN_EXECUTE  = "PC_V2_APP_OPEN_EXECUTE"\n'
        '_CAP_AVOL_PREPARE   = "PC_V2_AUDIO_VOLUME_PREPARE"\n'
        '_CAP_AVOL_EXECUTE   = "PC_V2_AUDIO_VOLUME_EXECUTE"\n',
        "pc2 audio caps",
    )

    old_tuple = '_CAP_AOPEN_PREPARE, _CAP_AOPEN_EXECUTE, _CAP_UTEXT_PREPARE, _CAP_UTEXT_EXECUTE, _CAP_SCHK_PREPARE, _CAP_SCHK_EXECUTE)'
    new_tuple = '_CAP_AOPEN_PREPARE, _CAP_AOPEN_EXECUTE, _CAP_AVOL_PREPARE, _CAP_AVOL_EXECUTE, _CAP_UTEXT_PREPARE, _CAP_UTEXT_EXECUTE, _CAP_SCHK_PREPARE, _CAP_SCHK_EXECUTE)'
    text = replace_once(text, old_tuple, new_tuple, "pc2 capability tuple")

    marker = '''# ============================
# Dispatcher + self-check
# ============================
'''
    block = r'''# ============================
# GOVERNED_AUDIO_VOLUME
# ============================
def _audio_state_anchor(volume_percent: int, muted: bool) -> str:
    raw = json.dumps(
        {
            "anchor_schema": "AUDIO_MASTER_VOLUME_PRE_STATE_V0",
            "scope_id": "OS_AUDIO:MASTER_VOLUME",
            "volume_percent": int(volume_percent),
            "muted": bool(muted),
        },
        sort_keys=True,
    ).encode()
    return _sha256(raw)


def pc_v2_audio_volume_prepare(
        delta=None, percent=None, *, stores_base_dir, session_id="", executor=None):
    if executor is None:
        return _prep_rej(OP_AUDIO_VOLUME, _CAP_AVOL_PREPARE, "EXECUTOR_REQUIRED", session_id)
    has_delta = isinstance(delta, int) and not isinstance(delta, bool)
    has_percent = isinstance(percent, int) and not isinstance(percent, bool)
    if has_delta == has_percent:
        return _prep_rej(OP_AUDIO_VOLUME, _CAP_AVOL_PREPARE, "EXACTLY_ONE_VOLUME_TARGET_REQUIRED", session_id)

    pre = executor.audio_status()
    if not pre.get("ok"):
        return _prep_rej(
            OP_AUDIO_VOLUME, _CAP_AVOL_PREPARE,
            "PRE_STATE_READ_FAILED:" + str(pre.get("error", "")), session_id,
        )
    before = pre.get("volume_percent")
    muted = pre.get("muted")
    if not isinstance(before, int) or not 0 <= before <= 100:
        return _prep_rej(OP_AUDIO_VOLUME, _CAP_AVOL_PREPARE, "PRE_STATE_INVALID", session_id)

    if has_delta:
        target = max(0, min(100, before + int(delta)))
        request_kind = "DELTA"
        request_value = int(delta)
    else:
        if not 0 <= int(percent) <= 100:
            return _prep_rej(OP_AUDIO_VOLUME, _CAP_AVOL_PREPARE, "TARGET_OUT_OF_RANGE", session_id)
        target = int(percent)
        request_kind = "ABSOLUTE"
        request_value = int(percent)

    scope_id = "OS_AUDIO:MASTER_VOLUME"
    psa = _audio_state_anchor(before, bool(muted))
    desc = {
        "scope_id": scope_id,
        "pre_volume_percent": before,
        "pre_muted": bool(muted),
        "target_volume_percent": target,
        "request_kind": request_kind,
        "request_value": request_value,
        "physical_state_anchor": psa,
        "session_id": session_id,
        "operation_type": OP_AUDIO_VOLUME,
    }
    st = _stores(stores_base_dir)
    eah = _eah(OP_AUDIO_VOLUME, desc)
    child = _v2id("chd", eah + scope_id)
    v2id = _v2id("v2x", eah + session_id)
    mh = _sha16(json.dumps(desc, sort_keys=True))
    dh = _persist_desc(v2id, OP_AUDIO_VOLUME, eah, desc, st["v2exec"])
    return {
        "status": PREPARED_AWAITING_HUMAN_APPROVAL,
        "j5_phase": "PREPARE",
        "operation_type": OP_AUDIO_VOLUME,
        "jarvis_authority": JARVIS_AUTHORITY,
        "decision_authority": KX_DECISION_AUTHORITY,
        "execution_authority_hash": eah,
        "v2_exec_id": v2id,
        "child_id": child,
        "manifest_hash": mh,
        "desc_hash": dh,
        "scope_id": scope_id,
        "pre_volume_percent": before,
        "target_volume_percent": target,
        "physical_state_anchor": psa,
        "_stores_base_dir": str(stores_base_dir),
        "receipt": _rcpt(
            _CAP_AVOL_PREPARE, OP_AUDIO_VOLUME,
            PREPARED_AWAITING_HUMAN_APPROVAL, session_id,
            execution_authority_hash=eah,
            scope_id=scope_id,
            pre_volume_percent=before,
            target_volume_percent=target,
            physical_state_anchor=psa,
        ),
    }


def pc_v2_audio_volume_execute(
        prepared_result, human_authorized_eah, human_authorization_reference,
        *, stores_base_dir, session_id="", executor=None):
    if prepared_result.get("j5_phase") != "PREPARE":
        return _exec_rej(OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE, "PREPARE_PHASE_REQUIRED", session_id)
    if prepared_result.get("status") != PREPARED_AWAITING_HUMAN_APPROVAL:
        return _exec_rej(OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE, "PREPARED_AWAITING_HUMAN_APPROVAL_REQUIRED", session_id)
    exp_eah = prepared_result.get("execution_authority_hash", "")
    if not exp_eah or human_authorized_eah != exp_eah:
        return _exec_rej(OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE, EAH_MISMATCH, session_id)
    if not (human_authorization_reference or "").strip():
        return _exec_rej(OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE, "HUMAN_AUTHORIZATION_REFERENCE_REQUIRED", session_id)
    if executor is None:
        return _exec_rej(OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE, "EXECUTOR_REQUIRED", session_id)

    st = _stores(stores_base_dir)
    v2id = prepared_result.get("v2_exec_id", "")
    child = prepared_result.get("child_id", "")
    mh = prepared_result.get("manifest_hash", "")
    dh = prepared_result.get("desc_hash", "")
    desc_rec = _load_desc(v2id, st["v2exec"])
    if not desc_rec or desc_rec.get("eah") != exp_eah:
        return _exec_rej(OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE, "DESCRIPTOR_EAH_MISMATCH", session_id)
    desc = desc_rec.get("descriptor", {})
    if _eah(OP_AUDIO_VOLUME, desc) != exp_eah:
        return _exec_rej(OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE, "DESCRIPTOR_EAH_RECOMPUTE_MISMATCH", session_id)

    scope_id = desc.get("scope_id", "")
    target = desc.get("target_volume_percent")
    before = desc.get("pre_volume_percent")
    stored_psa = desc.get("physical_state_anchor", "")
    if scope_id != "OS_AUDIO:MASTER_VOLUME" or not isinstance(target, int) or not 0 <= target <= 100:
        return _exec_rej(OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE, "DESCRIPTOR_INVALID", session_id)

    current = executor.audio_status()
    if not current.get("ok"):
        return _exec_rej(
            OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE,
            "PRE_STATE_READ_FAILED:" + str(current.get("error", "")), session_id,
        )
    current_volume = current.get("volume_percent")
    current_muted = bool(current.get("muted"))
    if not isinstance(current_volume, int):
        return _exec_rej(OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE, "PRE_STATE_INVALID", session_id)
    current_psa = _audio_state_anchor(current_volume, current_muted)
    if current_psa != stored_psa:
        return _exec_rej(OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE, "PRE_STATE_DRIFT", session_id)

    apr = _approval(v2id, child, exp_eah, scope_id + ":" + str(target))
    apv_id = apr["approval_id"]
    ar = _E.store_approval_artifact(apr, st["approval"])
    if ar.get("status") not in ("STORED", "IDEMPOTENT_ALREADY_EXISTS"):
        return _exec_rej(OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE, "APPROVAL_STORE_FAILED", session_id)

    kx = _kx108_pre(
        v2id, child, exp_eah, apv_id, dh, "", mh, [scope_id], OP_AUDIO_VOLUME,
        kxpre=st["kxpre"],
        physical_state_anchor=stored_psa,
        state_anchor_kind="PHYSICAL_PRE_STATE",
    )
    if not kx.get("verify_ok"):
        return _exec_rej(OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE, "KX108_PRE_FAILED", session_id)
    gate = kx.get("x108_gate", "")
    if gate != "ALLOW":
        return _exec_rej(OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE, "KX108_PRE_GATE:" + gate, session_id)

    ex = executor.set_volume(target)
    if not ex.get("ok"):
        return _exec_rej(
            OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE,
            "JARJAR_EXECUTOR_FAILED:" + str(ex.get("error", "")), session_id,
        )

    post = executor.audio_status()
    if not post.get("ok"):
        return _exec_rej(OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE, "POST_STATE_READ_FAILED", session_id)
    after = post.get("volume_percent")
    if after != target:
        return _exec_rej(
            OP_AUDIO_VOLUME, _CAP_AVOL_EXECUTE,
            "REALIZED_STATE_MISMATCH:expected=%s,got=%s" % (target, after),
            session_id,
        )

    return {
        "status": EXECUTED_OK,
        "j5_phase": "EXECUTE",
        "operation_type": OP_AUDIO_VOLUME,
        "jarvis_authority": JARVIS_AUTHORITY,
        "decision_authority": KX_DECISION_AUTHORITY,
        "kx108_pre_gate": gate,
        "human_authorization_consumed": True,
        "scope_id": scope_id,
        "pre_volume_percent": before,
        "post_volume_percent": after,
        "target_volume_percent": target,
        "rollback_volume_percent": before,
        "proof_strength": "STRONG",
        "realized_state_verified": True,
        "executor_provider": executor.EXECUTOR_PROVIDER,
        "executor_backend": executor.EXECUTOR_BACKEND,
        "executor_capability": "audio.set_volume",
        "receipt": _rcpt(
            _CAP_AVOL_EXECUTE, OP_AUDIO_VOLUME, EXECUTED_OK, session_id,
            kx108_pre_gate=gate,
            scope_id=scope_id,
            pre_volume_percent=before,
            post_volume_percent=after,
            target_volume_percent=target,
            rollback_volume_percent=before,
            proof_strength="STRONG",
            realized_state_verified=True,
        ),
    }


# ============================
# Dispatcher + self-check
# ============================
'''
    text = replace_once(text, marker, block, "pc2 governed audio block")

    if "_CAP_AVOL_PREPARE: pc_v2_audio_volume_prepare" not in text:
        pattern = r"(?m)^(\\s*)_CAP_AOPEN_EXECUTE\\s*:\\s*pc_v2_app_open_execute,\\s*$"
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1:
            raise RuntimeError(
                f"pc2 audio dispatch: expected exactly one APP_OPEN execute entry, found {len(matches)}"
            )
        m = matches[0]
        indent = m.group(1)
        replacement = (
            m.group(0)
            + "\\n"
            + indent + "_CAP_AVOL_PREPARE: pc_v2_audio_volume_prepare,"
            + "\\n"
            + indent + "_CAP_AVOL_EXECUTE: pc_v2_audio_volume_execute,"
        )
        text = text[:m.start()] + replacement + text[m.end():]

    # Keep self-check truthful when exact operations list is present.
    old_ops = '"operations": [OP_CREATE_FILE, OP_MOVE_FILE, OP_APPLY_PATCH, OP_CREATE_DIR, OP_WINDOW_FOCUS, OP_APP_OPEN, OP_UIA_SET_TEXT, OP_UIA_SET_CHECKED],'
    new_ops = '"operations": [OP_CREATE_FILE, OP_MOVE_FILE, OP_APPLY_PATCH, OP_CREATE_DIR, OP_WINDOW_FOCUS, OP_APP_OPEN, OP_AUDIO_VOLUME, OP_UIA_SET_TEXT, OP_UIA_SET_CHECKED],'
    if old_ops in text:
        text = text.replace(old_ops, new_ops, 1)

    PC2.write_text(text, encoding="utf-8")


def main() -> None:
    if not BRIDGE.exists() or not PC2.exists():
        raise SystemExit(f"Obsidia target files not found under {ROOT}")
    patch_bridge()
    patch_pc2()
    print("G13 governed audio Obsidia patch: PASS")
    print(BRIDGE)
    print(PC2)


if __name__ == "__main__":
    main()
