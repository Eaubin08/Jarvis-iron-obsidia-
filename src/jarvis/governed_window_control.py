"""Governed window-state/move seam between Jarjar and Obsidia/KX108."""
from __future__ import annotations

from dataclasses import dataclass
import importlib
import os
from pathlib import Path
import sys


_CAPS = {
    "window.minimize": "minimize",
    "window.maximize": "maximize",
    "window.restore": "restore",
    "window.move_monitor": "move_monitor",
}


class _WindowResolvingExecutor:
    def __init__(self, base):
        self._base = base
        self.EXECUTOR_PROVIDER = base.EXECUTOR_PROVIDER
        self.EXECUTOR_BACKEND = base.EXECUTOR_BACKEND

    @staticmethod
    def _variants(title: str) -> list[str]:
        raw = " ".join(title.casefold().split())
        variants = [raw]
        compact = raw.replace(" ", "").replace("-", "")
        aliases = {
            "blocnote": ("bloc note", "bloc-notes", "bloc notes", "notepad"),
            "bloquenote": ("bloc note", "bloc-notes", "bloc notes", "notepad"),
            "blocnotes": ("bloc note", "bloc-notes", "bloc notes", "notepad"),
        }
        variants.extend(aliases.get(compact, ()))
        if " " in raw:
            variants.append(raw.replace(" ", "-"))
        if "-" in raw:
            variants.append(raw.replace("-", " "))
        return list(dict.fromkeys(v for v in variants if v))

    def find_window(self, title: str) -> dict:
        for candidate in self._variants(title):
            result = self._base.find_window(candidate)
            if result.get("ok"):
                return result
        return self._base.find_window(title)

    def __getattr__(self, name):
        return getattr(self._base, name)


@dataclass
class GovernedWindowControlCommandHandler:
    obsidia_root: Path
    stores_base_dir: Path

    @classmethod
    def from_environment(cls) -> "GovernedWindowControlCommandHandler | None":
        enabled = os.getenv("JARJAR_GOVERNED_WINDOW_CONTROL", "1").strip().lower()
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
        action = _CAPS.get(request.capability)
        if action is None:
            return None

        title = str(request.arguments.get("title") or "").strip()
        if not title:
            return "Fenêtre non modifiée : titre absent."
        monitor_index = request.arguments.get("monitor_index")

        pc2, bridge = self._load()
        executor = _WindowResolvingExecutor(bridge.make_windows_executor())

        prepared = pc2.pc_v2_window_control_prepare(
            action,
            title,
            stores_base_dir=self.stores_base_dir,
            session_id=session_id,
            monitor_index=monitor_index,
            executor=executor,
        )
        if prepared.get("status") != pc2.PREPARED_AWAITING_HUMAN_APPROVAL:
            reason = prepared.get("reason") or prepared.get("status") or "PREPARE_REJECTED"
            return f"Fenêtre non modifiée : {reason}."

        eah = str(prepared.get("execution_authority_hash", ""))
        if not eah:
            return "Fenêtre non modifiée : autorité d'exécution manquante."

        result = pc2.pc_v2_window_control_execute(
            prepared,
            eah,
            f"JARJAR_EXPLICIT_VOICE_COMMAND:{session_id}:{original_text}",
            stores_base_dir=self.stores_base_dir,
            session_id=session_id,
            executor=executor,
        )
        if result.get("status") != pc2.EXECUTED_OK:
            reason = result.get("reason") or result.get("status") or "EXECUTE_REJECTED"
            return f"Fenêtre non modifiée : {reason}."

        gate = result.get("kx108_pre_gate", "UNKNOWN")
        labels = {
            "minimize": "Fenêtre minimisée",
            "maximize": "Fenêtre maximisée",
            "restore": "Fenêtre restaurée",
            "move_monitor": "Fenêtre déplacée",
        }
        return f"{labels[action]} : {result.get('resolved_title') or title}. KX108_PRE={gate}. État réel vérifié."


def governed_window_control_from_environment() -> GovernedWindowControlCommandHandler | None:
    return GovernedWindowControlCommandHandler.from_environment()
