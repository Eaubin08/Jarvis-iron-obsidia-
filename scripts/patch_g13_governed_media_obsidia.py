from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path.home() / "Desktop" / "obsidia-openjarvis-install-v0"
BRIDGE = ROOT / "scripts" / "jarjar_executor_bridge_v0.py"
PC2 = ROOT / "scripts" / "obsidia_pc_capabilities_v2.py"


def _backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".g13_media.bak")
    if not bak.exists():
        shutil.copy2(path, bak)


def _insert_before(text: str, marker: str, payload: str) -> str:
    if payload.strip() in text:
        return text
    if marker not in text:
        raise RuntimeError(f"anchor missing: {marker}")
    return text.replace(marker, payload + "\n\n" + marker, 1)


def patch_bridge() -> None:
    text = BRIDGE.read_text(encoding="utf-8")
    _backup(BRIDGE)

    marker = "def make_windows_executor("
    payload = r'''
# === G13 governed media ===
def _g13_media_execute(self, capability: str) -> dict:
    if capability not in {"media.play_pause", "media.next", "media.previous"}:
        return {"ok": False, "error": "MEDIA_CAPABILITY_UNSUPPORTED"}
    result = self._backend.execute(self._req(capability))
    return {
        "ok": bool(result.ok),
        "message": result.message,
        "data": dict(result.data or {}),
        "executor": self.EXECUTOR_BACKEND,
        "capability": capability,
    }

if not hasattr(JarJarWindowsExecutor, "media_execute"):
    JarJarWindowsExecutor.media_execute = _g13_media_execute
'''
    text = _insert_before(text, marker, payload)
    BRIDGE.write_text(text, encoding="utf-8")


def patch_pc2() -> None:
    text = PC2.read_text(encoding="utf-8")
    _backup(PC2)

    marker = None
    payload = r'''
# === G13 governed media ===
import uuid as _g13_uuid

OP_MEDIA_CONTROL = "V2_MEDIA_CONTROL"
_CAP_MEDIA_PREPARE = "PC_V2_MEDIA_CONTROL_PREPARE"
_CAP_MEDIA_EXECUTE = "PC_V2_MEDIA_CONTROL_EXECUTE"

def pc_v2_media_control_prepare(action, *, stores_base_dir, session_id="", executor=None):
    if executor is None:
        return _prep_rej(OP_MEDIA_CONTROL, _CAP_MEDIA_PREPARE, "EXECUTOR_REQUIRED", session_id)
    allowed = {
        "play_pause": "media.play_pause",
        "next": "media.next",
        "previous": "media.previous",
    }
    capability = allowed.get(str(action or "").strip().lower())
    if capability is None:
        return _prep_rej(OP_MEDIA_CONTROL, _CAP_MEDIA_PREPARE, "MEDIA_ACTION_UNSUPPORTED", session_id)

    st = _stores(stores_base_dir)
    invocation_id = _g13_uuid.uuid4().hex
    desc = {
        "action": action,
        "capability": capability,
        "session_id": session_id,
        "invocation_id": invocation_id,
        "operation_type": OP_MEDIA_CONTROL,
    }
    eah = _eah(OP_MEDIA_CONTROL, desc)
    child = _v2id("chd", eah + capability + invocation_id)
    v2id = _v2id("v2x", eah + session_id + invocation_id)
    mh = _sha16(json.dumps(desc, sort_keys=True))
    dh = _persist_desc(v2id, OP_MEDIA_CONTROL, eah, desc, st["v2exec"])
    return {
        "status": PREPARED_AWAITING_HUMAN_APPROVAL,
        "j5_phase": "PREPARE",
        "operation_type": OP_MEDIA_CONTROL,
        "jarvis_authority": JARVIS_AUTHORITY,
        "decision_authority": KX_DECISION_AUTHORITY,
        "execution_authority_hash": eah,
        "v2_exec_id": v2id,
        "child_id": child,
        "manifest_hash": mh,
        "desc_hash": dh,
        "capability": capability,
        "_stores_base_dir": str(stores_base_dir),
        "receipt": _rcpt(
            _CAP_MEDIA_PREPARE,
            OP_MEDIA_CONTROL,
            PREPARED_AWAITING_HUMAN_APPROVAL,
            session_id,
            execution_authority_hash=eah,
            capability=capability,
        ),
    }


def pc_v2_media_control_execute(
        prepared_result, human_authorized_eah, human_authorization_reference,
        *, stores_base_dir, session_id="", executor=None):
    if prepared_result.get("j5_phase") != "PREPARE":
        return _exec_rej(OP_MEDIA_CONTROL, _CAP_MEDIA_EXECUTE, "PREPARE_PHASE_REQUIRED", session_id)
    if prepared_result.get("status") != PREPARED_AWAITING_HUMAN_APPROVAL:
        return _exec_rej(OP_MEDIA_CONTROL, _CAP_MEDIA_EXECUTE, "PREPARED_AWAITING_HUMAN_APPROVAL_REQUIRED", session_id)

    exp_eah = prepared_result.get("execution_authority_hash", "")
    if not exp_eah or human_authorized_eah != exp_eah:
        return _exec_rej(OP_MEDIA_CONTROL, _CAP_MEDIA_EXECUTE, EAH_MISMATCH, session_id)
    if not (human_authorization_reference or "").strip():
        return _exec_rej(OP_MEDIA_CONTROL, _CAP_MEDIA_EXECUTE, "HUMAN_AUTHORIZATION_REFERENCE_REQUIRED", session_id)
    if executor is None:
        return _exec_rej(OP_MEDIA_CONTROL, _CAP_MEDIA_EXECUTE, "EXECUTOR_REQUIRED", session_id)

    st = _stores(stores_base_dir)
    v2id = prepared_result.get("v2_exec_id", "")
    child = prepared_result.get("child_id", "")
    mh = prepared_result.get("manifest_hash", "")
    dh = prepared_result.get("desc_hash", "")
    desc_rec = _load_desc(v2id, st["v2exec"])
    if not desc_rec or desc_rec.get("eah") != exp_eah:
        return _exec_rej(OP_MEDIA_CONTROL, _CAP_MEDIA_EXECUTE, "DESCRIPTOR_EAH_MISMATCH", session_id)

    desc = desc_rec["descriptor"]
    capability = desc["capability"]

    apr = _approval(v2id, child, exp_eah, capability)
    apv_id = apr["approval_id"]
    ar = _E.store_approval_artifact(apr, st["approval"])
    if ar.get("status") not in ("STORED", "IDEMPOTENT_ALREADY_EXISTS"):
        return _exec_rej(OP_MEDIA_CONTROL, _CAP_MEDIA_EXECUTE, "APPROVAL_STORE_FAILED", session_id)

    kx = _kx108_pre(
        v2id, child, exp_eah, apv_id, dh, "", mh,
        [f"OS_MEDIA:{capability}"], OP_MEDIA_CONTROL, kxpre=st["kxpre"],
        physical_state_anchor="MEDIA_COMMAND",
        state_anchor_kind="PHYSICAL_PRE_STATE",
    )
    if not kx.get("verify_ok"):
        return _exec_rej(OP_MEDIA_CONTROL, _CAP_MEDIA_EXECUTE, "KX108_PRE_FAILED", session_id)
    gate = kx.get("x108_gate", "")
    if gate != "ALLOW":
        return _exec_rej(OP_MEDIA_CONTROL, _CAP_MEDIA_EXECUTE, "KX108_PRE_GATE:" + gate, session_id)

    ex = executor.media_execute(capability)
    if not ex.get("ok"):
        return _exec_rej(
            OP_MEDIA_CONTROL, _CAP_MEDIA_EXECUTE,
            "JARJAR_EXECUTOR_FAILED:" + str(ex.get("error") or ex.get("message") or ""),
            session_id,
        )

    return {
        "status": EXECUTED_OK,
        "j5_phase": "EXECUTE",
        "operation_type": OP_MEDIA_CONTROL,
        "jarvis_authority": JARVIS_AUTHORITY,
        "decision_authority": KX_DECISION_AUTHORITY,
        "kx108_pre_gate": gate,
        "human_authorization_consumed": True,
        "capability": capability,
        "executor_provider": executor.EXECUTOR_PROVIDER,
        "executor_backend": executor.EXECUTOR_BACKEND,
        "receipt": _rcpt(
            _CAP_MEDIA_EXECUTE,
            OP_MEDIA_CONTROL,
            EXECUTED_OK,
            session_id,
            kx108_pre_gate=gate,
            capability=capability,
        ),
    }
'''
    section_marker = "# === G13 governed media ==="
    if section_marker in text:
        text = text.split(section_marker, 1)[0].rstrip()
    text = text.rstrip() + "\n\n" + payload.strip() + "\n"
    PC2.write_text(text, encoding="utf-8")


def main() -> None:
    if not BRIDGE.exists() or not PC2.exists():
        raise SystemExit(f"Obsidia worktree not found under {ROOT}")
    patch_bridge()
    patch_pc2()
    print("G13 governed media Obsidia patch: PASS")
    print(f"bridge={BRIDGE}")
    print(f"pc2={PC2}")


if __name__ == "__main__":
    main()
