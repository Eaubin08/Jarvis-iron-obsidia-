"""Governed Wi-Fi/Bluetooth seam between Jarjar and Obsidia/KX108."""
from __future__ import annotations

from dataclasses import dataclass
import importlib
import os
from pathlib import Path
import sys


_CAPS = {
    "wifi.enable": ("wifi", True),
    "wifi.disable": ("wifi", False),
    "bluetooth.enable": ("bluetooth", True),
    "bluetooth.disable": ("bluetooth", False),
}


@dataclass
class GovernedConnectivityCommandHandler:
    obsidia_root: Path
    stores_base_dir: Path

    @classmethod
    def from_environment(cls) -> "GovernedConnectivityCommandHandler | None":
        enabled = os.getenv("JARJAR_GOVERNED_CONNECTIVITY", "1").strip().lower()
        if enabled in {"0", "false", "no", "off"}:
            return None
        root_raw = os.getenv("OBSIDIA_OPENJARVIS_ROOT", "").strip()
        root = (
            Path(root_raw).resolve()
            if root_raw
            else Path(__file__).resolve().parents[2].parent / "obsidia-openjarvis-install-v0"
        )
        stores_raw = os.getenv("OBSIDIA_STORES_BASE", "").strip()
        if not stores_raw:
            return None
        return cls(root, Path(stores_raw).resolve())

    def _load(self):
        scripts = self.obsidia_root / "scripts"
        if not scripts.is_dir():
            raise RuntimeError(f"Obsidia scripts directory not found: {scripts}")
        for entry in (self.obsidia_root, scripts):
            value = str(entry)
            if value not in sys.path:
                sys.path.insert(0, value)
        pc2 = importlib.import_module("obsidia_pc_capabilities_v2")
        bridge = importlib.import_module("jarjar_executor_bridge_v0")
        return pc2, bridge

    def handle_request(self, request, *, session_id: str, original_text: str) -> str | None:
        spec = _CAPS.get(request.capability)
        if spec is None:
            return None
        family, enabled = spec

        pc2, bridge = self._load()
        executor = bridge.make_windows_executor()

        prepared = pc2.pc_v2_connectivity_prepare(
            family,
            enabled,
            stores_base_dir=self.stores_base_dir,
            session_id=session_id,
            executor=executor,
        )
        if prepared.get("status") != pc2.PREPARED_AWAITING_HUMAN_APPROVAL:
            reason = prepared.get("reason") or prepared.get("status") or "PREPARE_REJECTED"
            return f"{family.upper()} non modifié : {reason}."

        eah = str(prepared.get("execution_authority_hash", ""))
        if not eah:
            return f"{family.upper()} non modifié : autorité d'exécution manquante."

        result = pc2.pc_v2_connectivity_execute(
            prepared,
            eah,
            f"JARJAR_EXPLICIT_VOICE_COMMAND:{session_id}:{original_text}",
            stores_base_dir=self.stores_base_dir,
            session_id=session_id,
            executor=executor,
        )
        if result.get("status") != pc2.EXECUTED_OK:
            reason = result.get("reason") or result.get("status") or "EXECUTE_REJECTED"
            folded = str(reason).casefold()
            if "requiert une" in folded and "levation" in folded or "administrator privileges" in folded or "administrateur" in folded:
                return (
                    f"{family.upper()} non modifié : HOLD_PRIVILEGE_REQUIRED. "
                    "Windows exige une élévation administrateur pour cette action."
                )
            return f"{family.upper()} non modifié : {reason}."

        gate = result.get("kx108_pre_gate", "UNKNOWN")
        after = "activé" if result.get("post_enabled") is True else "désactivé"
        return f"{family.upper()} {after}. KX108_PRE={gate}. État réel vérifié."


def governed_connectivity_from_environment() -> GovernedConnectivityCommandHandler | None:
    return GovernedConnectivityCommandHandler.from_environment()
