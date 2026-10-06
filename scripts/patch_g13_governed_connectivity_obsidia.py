from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path.home() / "Desktop" / "obsidia-openjarvis-install-v0"
BRIDGE = ROOT / "scripts" / "jarjar_executor_bridge_v0.py"
PC2 = ROOT / "scripts" / "obsidia_pc_capabilities_v2.py"


def _backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".g13_connectivity.bak")
    if not bak.exists():
        shutil.copy2(path, bak)


def patch_bridge() -> None:
    text = BRIDGE.read_text(encoding="utf-8")
    _backup(BRIDGE)
    marker = "# === G13 governed connectivity ==="
    if marker in text:
        text = text.split(marker, 1)[0].rstrip()

    payload = r'''
# === G13 governed connectivity ===
def _g13_connectivity_status(self, family: str) -> dict:
    capability = {"wifi": "wifi.status", "bluetooth": "bluetooth.status"}.get(family)
    if capability is None:
        return {"ok": False, "error": "CONNECTIVITY_FAMILY_UNSUPPORTED"}
    result = self._backend.execute(self._req(capability))
    return {
        "ok": bool(result.ok),
        "message": result.message,
        "data": dict(result.data or {}),
        "executor": self.EXECUTOR_BACKEND,
        "capability": capability,
    }


def _g13_connectivity_set(self, family: str, enabled: bool) -> dict:
    table = {
        ("wifi", True): "wifi.enable",
        ("wifi", False): "wifi.disable",
        ("bluetooth", True): "bluetooth.enable",
        ("bluetooth", False): "bluetooth.disable",
    }
    capability = table.get((family, bool(enabled)))
    if capability is None:
        return {"ok": False, "error": "CONNECTIVITY_MUTATION_UNSUPPORTED"}
    result = self._backend.execute(self._req(capability))
    return {
        "ok": bool(result.ok),
        "message": result.message,
        "data": dict(result.data or {}),
        "executor": self.EXECUTOR_BACKEND,
        "capability": capability,
    }


if not hasattr(JarJarWindowsExecutor, "connectivity_status"):
    JarJarWindowsExecutor.connectivity_status = _g13_connectivity_status
if not hasattr(JarJarWindowsExecutor, "connectivity_set"):
    JarJarWindowsExecutor.connectivity_set = _g13_connectivity_set
'''
    BRIDGE.write_text(text.rstrip() + "\n\n" + payload.strip() + "\n", encoding="utf-8")


def patch_pc2() -> None:
    text = PC2.read_text(encoding="utf-8")
    _backup(PC2)
    marker = "# === G13 governed connectivity ==="
    if marker in text:
        text = text.split(marker, 1)[0].rstrip()

    payload = r'''
# === G13 governed connectivity ===
import uuid as _g13_conn_uuid
import time as _g13_conn_time

OP_CONNECTIVITY_CONTROL = "V2_CONNECTIVITY_CONTROL"
_CAP_CONN_PREPARE = "PC_V2_CONNECTIVITY_CONTROL_PREPARE"
_CAP_CONN_EXECUTE = "PC_V2_CONNECTIVITY_CONTROL_EXECUTE"


def _g13_conn_observed_enabled(family, status):
    data = status.get("data") or {}
    if family == "wifi":
        adapters = data.get("adapters") or []
        if not adapters:
            return None
        states = [str(a.get("Status") or "").strip().casefold() for a in adapters]
        if any(s == "disabled" for s in states):
            return False
        if any(s in {"up", "disconnected", "connected"} for s in states):
            return True
        return None

    devices = data.get("devices") or []

    def _bt_radio_candidate(d):
        name = d.get("FriendlyName")
        instance_id = d.get("InstanceId")
        if not isinstance(name, str) or not isinstance(instance_id, str):
            return False
        folded = name.casefold()
        if instance_id.upper().startswith("BTHENUM"):
            return False
        if any(tok in folded for tok in ("enumerator", "rfcomm", "protocol", "service", "avrcp", "gatt")):
            return False
        return (
            any(tok in folded for tok in ("adapter", "radio", "bluetooth"))
            or instance_id.upper().startswith(("USB\\\\", "PCI\\\\"))
        )

    radios = [d for d in devices if _bt_radio_candidate(d)]
    if not radios:
        return None
    states = [str(d.get("Status") or "").strip().casefold() for d in radios]
    if any(s == "ok" for s in states):
        return True
    if all(s and s != "ok" for s in states):
        return False
    return None


def pc_v2_connectivity_prepare(family, enabled, *, stores_base_dir, session_id="", executor=None):
    family = str(family or "").strip().lower()
    if family not in {"wifi", "bluetooth"}:
        return _prep_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_PREPARE, "CONNECTIVITY_FAMILY_UNSUPPORTED", session_id)
    if not isinstance(enabled, bool):
        return _prep_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_PREPARE, "ENABLED_BOOL_REQUIRED", session_id)
    if executor is None:
        return _prep_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_PREPARE, "EXECUTOR_REQUIRED", session_id)

    pre = executor.connectivity_status(family)
    if not pre.get("ok"):
        return _prep_rej(
            OP_CONNECTIVITY_CONTROL, _CAP_CONN_PREPARE,
            "PRE_STATE_READ_FAILED:" + str(pre.get("error") or pre.get("message") or ""),
            session_id,
        )

    invocation_id = _g13_conn_uuid.uuid4().hex
    pre_enabled = _g13_conn_observed_enabled(family, pre)
    desc = {
        "family": family,
        "enabled": enabled,
        "pre_enabled": pre_enabled,
        "session_id": session_id,
        "invocation_id": invocation_id,
        "operation_type": OP_CONNECTIVITY_CONTROL,
    }
    eah = _eah(OP_CONNECTIVITY_CONTROL, desc)
    child = _v2id("chd", eah + family + invocation_id)
    v2id = _v2id("v2x", eah + session_id + invocation_id)
    mh = _sha16(json.dumps(desc, sort_keys=True))
    dh = _persist_desc(v2id, OP_CONNECTIVITY_CONTROL, eah, desc, _stores(stores_base_dir)["v2exec"])

    return {
        "status": PREPARED_AWAITING_HUMAN_APPROVAL,
        "j5_phase": "PREPARE",
        "operation_type": OP_CONNECTIVITY_CONTROL,
        "jarvis_authority": JARVIS_AUTHORITY,
        "decision_authority": KX_DECISION_AUTHORITY,
        "execution_authority_hash": eah,
        "v2_exec_id": v2id,
        "child_id": child,
        "manifest_hash": mh,
        "desc_hash": dh,
        "family": family,
        "enabled": enabled,
        "pre_enabled": pre_enabled,
        "_stores_base_dir": str(stores_base_dir),
        "receipt": _rcpt(
            _CAP_CONN_PREPARE, OP_CONNECTIVITY_CONTROL,
            PREPARED_AWAITING_HUMAN_APPROVAL, session_id,
            execution_authority_hash=eah, family=family, enabled=enabled,
            pre_enabled=pre_enabled,
        ),
    }


def pc_v2_connectivity_execute(
        prepared_result, human_authorized_eah, human_authorization_reference,
        *, stores_base_dir, session_id="", executor=None):
    if prepared_result.get("j5_phase") != "PREPARE":
        return _exec_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_EXECUTE, "PREPARE_PHASE_REQUIRED", session_id)
    if prepared_result.get("status") != PREPARED_AWAITING_HUMAN_APPROVAL:
        return _exec_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_EXECUTE, "PREPARED_AWAITING_HUMAN_APPROVAL_REQUIRED", session_id)

    exp_eah = prepared_result.get("execution_authority_hash", "")
    if not exp_eah or human_authorized_eah != exp_eah:
        return _exec_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_EXECUTE, EAH_MISMATCH, session_id)
    if not (human_authorization_reference or "").strip():
        return _exec_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_EXECUTE, "HUMAN_AUTHORIZATION_REFERENCE_REQUIRED", session_id)
    if executor is None:
        return _exec_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_EXECUTE, "EXECUTOR_REQUIRED", session_id)

    st = _stores(stores_base_dir)
    v2id = prepared_result.get("v2_exec_id", "")
    child = prepared_result.get("child_id", "")
    mh = prepared_result.get("manifest_hash", "")
    dh = prepared_result.get("desc_hash", "")
    rec = _load_desc(v2id, st["v2exec"])
    if not rec or rec.get("eah") != exp_eah:
        return _exec_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_EXECUTE, "DESCRIPTOR_EAH_MISMATCH", session_id)

    desc = rec["descriptor"]
    family = desc["family"]
    enabled = bool(desc["enabled"])

    pre_now = executor.connectivity_status(family)
    if not pre_now.get("ok"):
        return _exec_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_EXECUTE, "PRE_STATE_RECHECK_FAILED", session_id)
    pre_now_enabled = _g13_conn_observed_enabled(family, pre_now)
    if desc.get("pre_enabled") is not None and pre_now_enabled != desc.get("pre_enabled"):
        return _exec_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_EXECUTE, "PRE_STATE_DRIFT", session_id)

    apr = _approval(v2id, child, exp_eah, f"{family}:{enabled}")
    apv_id = apr["approval_id"]
    ar = _E.store_approval_artifact(apr, st["approval"])
    if ar.get("status") not in ("STORED", "IDEMPOTENT_ALREADY_EXISTS"):
        return _exec_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_EXECUTE, "APPROVAL_STORE_FAILED", session_id)

    kx = _kx108_pre(
        v2id, child, exp_eah, apv_id, dh, "", mh,
        [f"OS_CONNECTIVITY:{family}"], OP_CONNECTIVITY_CONTROL, kxpre=st["kxpre"],
        physical_state_anchor=f"{family}:{pre_now_enabled}",
        state_anchor_kind="PHYSICAL_PRE_STATE",
    )
    if not kx.get("verify_ok"):
        return _exec_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_EXECUTE, "KX108_PRE_FAILED", session_id)
    gate = kx.get("x108_gate", "")
    if gate != "ALLOW":
        return _exec_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_EXECUTE, "KX108_PRE_GATE:" + gate, session_id)

    ex = executor.connectivity_set(family, enabled)
    if not ex.get("ok"):
        return _exec_rej(
            OP_CONNECTIVITY_CONTROL, _CAP_CONN_EXECUTE,
            "JARJAR_EXECUTOR_FAILED:" + str(ex.get("error") or ex.get("message") or ""),
            session_id,
        )

    post = None
    post_enabled = None
    # Windows network/PnP state can settle asynchronously after the mutation.
    # Re-read a bounded number of times; never convert an unresolved state into PASS.
    for _attempt in range(6):
        post = executor.connectivity_status(family)
        if not post.get("ok"):
            return _exec_rej(OP_CONNECTIVITY_CONTROL, _CAP_CONN_EXECUTE, "POST_STATE_READ_FAILED", session_id)
        post_enabled = _g13_conn_observed_enabled(family, post)
        if post_enabled is enabled:
            break
        _g13_conn_time.sleep(0.5)

    if post_enabled is not enabled:
        return _exec_rej(
            OP_CONNECTIVITY_CONTROL, _CAP_CONN_EXECUTE,
            "REALIZED_STATE_MISMATCH:" + str(post_enabled),
            session_id,
        )

    return {
        "status": EXECUTED_OK,
        "j5_phase": "EXECUTE",
        "operation_type": OP_CONNECTIVITY_CONTROL,
        "jarvis_authority": JARVIS_AUTHORITY,
        "decision_authority": KX_DECISION_AUTHORITY,
        "kx108_pre_gate": gate,
        "human_authorization_consumed": True,
        "family": family,
        "pre_enabled": pre_now_enabled,
        "post_enabled": post_enabled,
        "proof_strength": "STRONG",
        "realized_state_verified": True,
        "executor_provider": executor.EXECUTOR_PROVIDER,
        "executor_backend": executor.EXECUTOR_BACKEND,
        "receipt": _rcpt(
            _CAP_CONN_EXECUTE, OP_CONNECTIVITY_CONTROL, EXECUTED_OK, session_id,
            kx108_pre_gate=gate, family=family, enabled=enabled,
            pre_enabled=pre_now_enabled, post_enabled=post_enabled,
        ),
    }
'''
    PC2.write_text(text.rstrip() + "\n\n" + payload.strip() + "\n", encoding="utf-8")


def main() -> None:
    if not BRIDGE.exists() or not PC2.exists():
        raise SystemExit(f"Obsidia worktree not found under {ROOT}")
    patch_bridge()
    patch_pc2()
    print("G13 governed connectivity Obsidia patch: PASS")
    print(f"bridge={BRIDGE}")
    print(f"pc2={PC2}")


if __name__ == "__main__":
    main()
