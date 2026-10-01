"""Governed rollback of the last successfully executed MOVE_FILE."""
from __future__ import annotations

from dataclasses import dataclass, field
import importlib
from pathlib import Path
import re
import sys
from typing import Any

from .governed_move import GovernedMoveCoordinator


_PREPARED_STATUS = "PREPARED_AWAITING_HUMAN_APPROVAL"
_EXECUTED_STATUS = "ROLLBACK_EXECUTED_OK"


@dataclass(frozen=True)
class GovernedRollbackConfig:
    execution_worktree_path: Path
    stores_base_dir: Path
    obsidia_root: Path | None = None


@dataclass
class GovernedMoveRollbackCoordinator:
    config: GovernedRollbackConfig
    move_coordinator: GovernedMoveCoordinator
    prepare_fn: Any
    execute_fn: Any
    executor_factory: Any
    pending: dict[str, Any] | None = field(default=None, init=False)

    @classmethod
    def from_obsidia(
        cls,
        config: GovernedRollbackConfig,
        move_coordinator: GovernedMoveCoordinator,
    ) -> "GovernedMoveRollbackCoordinator":
        root = (
            Path(config.obsidia_root).resolve()
            if config.obsidia_root is not None
            else Path(__file__).resolve().parents[2].parent / "obsidia-openjarvis-install-v0"
        )
        scripts = root / "scripts"
        if not scripts.is_dir():
            raise RuntimeError(f"Obsidia scripts directory not found: {scripts}")

        for entry in (root, scripts):
            value = str(entry)
            if value not in sys.path:
                sys.path.insert(0, value)

        bridge = importlib.import_module("jarjar_governed_rollback_bridge_v0")
        executor_bridge = importlib.import_module("jarjar_executor_bridge_v0")
        return cls(
            config=config,
            move_coordinator=move_coordinator,
            prepare_fn=bridge.governed_rollback_move_prepare,
            execute_fn=bridge.governed_rollback_move_execute,
            executor_factory=executor_bridge.make_executor,
        )

    def prepare_last_move(self, *, session_id: str) -> str:
        if self.pending is not None:
            return "Un rollback gouverné est déjà en attente. Confirme-le ou annule-le."

        last = self.move_coordinator.last_execution_result
        if not last:
            return "Aucun déplacement gouverné exécuté n'est disponible pour rollback."

        sre_id = str(last.get("sealed_rollback_evidence_id", ""))
        if not sre_id:
            return "Rollback indisponible : preuve scellée absente du dernier déplacement."

        stores = Path(self.config.stores_base_dir)
        result = self.prepare_fn(
            sre_id,
            sre_dir=stores / "sre",
            v2exec_dir=stores / "v2exec",
            repo_root=self.config.execution_worktree_path,
            session_id=session_id,
        )
        if result.get("status") != _PREPARED_STATUS:
            reason = result.get("reason") or result.get("status") or "ROLLBACK_PREPARE_REJECTED"
            return f"Rollback refusé à la préparation : {reason}"

        self.pending = result
        rah = str(result.get("rollback_authority_hash", ""))
        return (
            f"Rollback préparé : {result.get('dest_path', '')} → {result.get('source_path', '')}. "
            f"RAH {rah[:12] if rah else 'UNKNOWN'}. "
            "Dis « confirme le rollback » pour restaurer le déplacement."
        )

    def approve(self, *, session_id: str) -> str:
        prepared = self.pending
        if prepared is None:
            return "Aucun rollback gouverné n'est en attente."

        rah = str(prepared.get("rollback_authority_hash", ""))
        if not rah:
            self.pending = None
            return "Rollback annulé : hash d'autorité de récupération manquant."

        executor = self.executor_factory(Path(self.config.execution_worktree_path).resolve())
        stores = Path(self.config.stores_base_dir)
        result = self.execute_fn(
            prepared,
            rah,
            f"JARJAR_HUD_CONFIRM_ROLLBACK:{session_id}",
            sre_dir=stores / "sre",
            v2exec_dir=stores / "v2exec",
            executor=executor,
            repo_root=self.config.execution_worktree_path,
            session_id=session_id,
        )
        if result.get("status") == _EXECUTED_STATUS:
            self.pending = None
            self.move_coordinator.last_execution_result = None
            return (
                f"Rollback exécuté et prouvé : "
                f"{result.get('dest_path', '')} → {result.get('source_path', '')}."
            )

        reason = result.get("reason") or result.get("status") or "ROLLBACK_EXECUTE_REJECTED"
        return f"Rollback non exécuté : {reason}"

    def cancel(self) -> str:
        if self.pending is None:
            return "Aucun rollback gouverné n'est en attente."
        self.pending = None
        return "Rollback gouverné annulé avant exécution."


@dataclass
class GovernedMoveRollbackCommandHandler:
    coordinator: GovernedMoveRollbackCoordinator

    def handle(self, text: str, *, session_id: str) -> str | None:
        normalized = _normalize(text)
        if normalized in {
            "annule le dernier deplacement",
            "rollback dernier deplacement",
            "prepare rollback dernier deplacement",
        }:
            return self.coordinator.prepare_last_move(session_id=session_id)
        if normalized in {"confirme le rollback", "confirme rollback"}:
            return self.coordinator.approve(session_id=session_id)
        if normalized in {"annule le rollback", "annule rollback"}:
            return self.coordinator.cancel()
        return None


def _normalize(text: str) -> str:
    import unicodedata

    value = unicodedata.normalize("NFKD", text.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return " ".join(value.split())
