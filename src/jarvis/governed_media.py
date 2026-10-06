"""Governed media-control seam between Jarjar and Obsidia/KX108."""
from __future__ import annotations

from dataclasses import dataclass
import importlib
import os
from pathlib import Path
import sys


_MEDIA = {
    "media.play_pause": "play_pause",
    "media.next": "next",
    "media.previous": "previous",
}


@dataclass
class GovernedMediaCommandHandler:
    obsidia_root: Path
    stores_base_dir: Path

    @classmethod
    def from_environment(cls) -> "GovernedMediaCommandHandler | None":
        enabled = os.getenv("JARJAR_GOVERNED_MEDIA", "1").strip().lower()
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
        action = _MEDIA.get(request.capability)
        if action is None:
            return None

        pc2, bridge = self._load()
        executor = bridge.make_windows_executor()

        prepared = pc2.pc_v2_media_control_prepare(
            action,
            stores_base_dir=self.stores_base_dir,
            session_id=session_id,
            executor=executor,
        )
        if prepared.get("status") != pc2.PREPARED_AWAITING_HUMAN_APPROVAL:
            reason = prepared.get("reason") or prepared.get("status") or "PREPARE_REJECTED"
            return f"Commande média non exécutée : {reason}."

        eah = str(prepared.get("execution_authority_hash", ""))
        if not eah:
            return "Commande média non exécutée : autorité d'exécution manquante."

        result = pc2.pc_v2_media_control_execute(
            prepared,
            eah,
            f"JARJAR_EXPLICIT_VOICE_COMMAND:{session_id}:{original_text}",
            stores_base_dir=self.stores_base_dir,
            session_id=session_id,
            executor=executor,
        )
        if result.get("status") != pc2.EXECUTED_OK:
            reason = result.get("reason") or result.get("status") or "EXECUTE_REJECTED"
            return f"Commande média non exécutée : {reason}."

        gate = result.get("kx108_pre_gate", "UNKNOWN")
        labels = {
            "play_pause": "Lecture/pause exécutée",
            "next": "Piste suivante exécutée",
            "previous": "Piste précédente exécutée",
        }
        return f"{labels[action]}. KX108_PRE={gate}."


def governed_media_from_environment() -> GovernedMediaCommandHandler | None:
    return GovernedMediaCommandHandler.from_environment()
