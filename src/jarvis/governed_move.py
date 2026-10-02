"""Two-phase governed file-move seam between Jarjar and Obsidia.

Jarjar never decides whether a move is authorized.  This coordinator only:
1. asks Obsidia to PREPARE the operation,
2. keeps the prepared envelope pending,
3. consumes an explicit human confirmation,
4. asks Obsidia/KX108 to EXECUTE using Jarjar as the physical executor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable


_PREPARED_STATUS = "PREPARED_AWAITING_HUMAN_APPROVAL"
_EXECUTED_STATUS = "EXECUTED_OK"


@dataclass(frozen=True)
class GovernedMoveConfig:
    execution_worktree_path: Path
    main_worktree_path: Path
    branch_name: str
    base_sha: str
    stores_base_dir: Path
    obsidia_root: Path | None = None


@dataclass
class GovernedMoveCoordinator:
    config: GovernedMoveConfig
    prepare_fn: Callable[..., dict[str, Any]]
    execute_fn: Callable[..., dict[str, Any]]
    executor_factory: Callable[[Path], Any]
    pending: dict[str, Any] | None = field(default=None, init=False)
    last_execution_result: dict[str, Any] | None = field(default=None, init=False)

    @classmethod
    def from_obsidia(cls, config: GovernedMoveConfig) -> "GovernedMoveCoordinator":
        root = (
            Path(config.obsidia_root).resolve()
            if config.obsidia_root is not None
            else _default_obsidia_root()
        )
        scripts = root / "scripts"
        if not scripts.is_dir():
            raise RuntimeError(f"Obsidia scripts directory not found: {scripts}")

        # Obsidia modules import both top-level packages (for example sigma)
        # and legacy modules from scripts/.  Expose both roots explicitly.
        root_str = str(root)
        scripts_str = str(scripts)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)
        if scripts_str not in sys.path:
            sys.path.insert(0, scripts_str)

        pc2 = importlib.import_module("obsidia_pc_capabilities_v2")
        bridge = importlib.import_module("jarjar_executor_bridge_v0")
        return cls(
            config=config,
            prepare_fn=pc2.pc_v2_move_file_prepare,
            execute_fn=pc2.pc_v2_move_file_execute,
            executor_factory=bridge.make_executor,
        )

    def prepare(self, source_path: str, dest_path: str, *, session_id: str) -> str:
        if self.pending is not None:
            return "Un déplacement gouverné est déjà en attente. Confirme-le ou annule-le."

        result = self.prepare_fn(
            source_path,
            dest_path,
            execution_worktree_path=self.config.execution_worktree_path,
            main_worktree_path=self.config.main_worktree_path,
            branch_name=self.config.branch_name,
            base_sha=self.config.base_sha,
            stores_base_dir=self.config.stores_base_dir,
            session_id=session_id,
        )
        if result.get("status") != _PREPARED_STATUS:
            reason = result.get("reason") or result.get("status") or "PREPARE_REJECTED"
            return f"Déplacement refusé à la préparation : {reason}"

        self.pending = result
        eah = str(result.get("execution_authority_hash", ""))
        short_eah = eah[:12] if eah else "UNKNOWN"
        return (
            f"Déplacement préparé : {source_path} → {dest_path}. "
            f"EAH {short_eah}. Dis « confirme le déplacement » pour autoriser l'étape d'exécution."
        )

    def approve(self, *, session_id: str) -> str:
        prepared = self.pending
        if prepared is None:
            return "Aucun déplacement gouverné n'est en attente."

        eah = str(prepared.get("execution_authority_hash", ""))
        if not eah:
            self.pending = None
            return "Déplacement annulé : EAH manquant dans la préparation."

        executor = self.executor_factory(Path(self.config.execution_worktree_path).resolve())
        reference = f"JARJAR_HUD_CONFIRM:{session_id}"
        result = self.execute_fn(
            prepared,
            eah,
            reference,
            stores_base_dir=self.config.stores_base_dir,
            repo_root=self.config.execution_worktree_path,
            session_id=session_id,
            executor=executor,
        )
        if result.get("status") == _EXECUTED_STATUS:
            self.pending = None
            self.last_execution_result = result
            return (
                f"Déplacement exécuté et prouvé : "
                f"{result.get('source_path', '')} → {result.get('dest_path', '')}."
            )

        reason = result.get("reason") or result.get("status") or "EXECUTE_REJECTED"
        return f"Déplacement non exécuté : {reason}"

    def cancel(self) -> str:
        if self.pending is None:
            return "Aucun déplacement gouverné n'est en attente."
        self.pending = None
        return "Déplacement gouverné annulé avant exécution."


@dataclass
class GovernedMoveCommandHandler:
    coordinator: GovernedMoveCoordinator

    _move_re = re.compile(
        r"^(?:deplace|déplace)\s+(?:le\s+fichier\s+)?(.+?)\s+vers\s+(.+)$",
        re.IGNORECASE,
    )

    def handle(self, text: str, *, session_id: str) -> str | None:
        clean = text.strip()
        if not clean:
            return None

        normalized = _normalize_confirmation(clean)
        if normalized in {"confirme deplacement", "confirme le deplacement"}:
            return self.coordinator.approve(session_id=session_id)
        if normalized in {"annule deplacement", "annule le deplacement"}:
            return self.coordinator.cancel()

        match = self._move_re.match(clean)
        if match is None:
            return None

        source = _strip_quotes(match.group(1).strip())
        dest = _strip_quotes(match.group(2).strip())
        if not source or not dest:
            return "Commande de déplacement incomplète."
        return self.coordinator.prepare(source, dest, session_id=session_id)


def governed_move_from_environment() -> GovernedMoveCommandHandler | None:
    enabled = os.getenv("JARJAR_GOVERNED_MOVE", "0").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return None

    required = {
        "OBSIDIA_EXECUTION_WORKTREE": os.getenv("OBSIDIA_EXECUTION_WORKTREE", "").strip(),
        "OBSIDIA_MAIN_WORKTREE": os.getenv("OBSIDIA_MAIN_WORKTREE", "").strip(),
        "OBSIDIA_BRANCH_NAME": os.getenv("OBSIDIA_BRANCH_NAME", "").strip(),
        "OBSIDIA_BASE_SHA": os.getenv("OBSIDIA_BASE_SHA", "").strip(),
        "OBSIDIA_STORES_BASE": os.getenv("OBSIDIA_STORES_BASE", "").strip(),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError("Missing governed-move environment: " + ", ".join(missing))

    root_raw = os.getenv("OBSIDIA_OPENJARVIS_ROOT", "").strip()
    config = GovernedMoveConfig(
        execution_worktree_path=Path(required["OBSIDIA_EXECUTION_WORKTREE"]).resolve(),
        main_worktree_path=Path(required["OBSIDIA_MAIN_WORKTREE"]).resolve(),
        branch_name=required["OBSIDIA_BRANCH_NAME"],
        base_sha=required["OBSIDIA_BASE_SHA"],
        stores_base_dir=Path(required["OBSIDIA_STORES_BASE"]).resolve(),
        obsidia_root=Path(root_raw).resolve() if root_raw else None,
    )
    return GovernedMoveCommandHandler(GovernedMoveCoordinator.from_obsidia(config))


def _default_obsidia_root() -> Path:
    # src/jarvis/governed_move.py -> repo root -> Desktop sibling worktree
    return Path(__file__).resolve().parents[2].parent / "obsidia-openjarvis-install-v0"


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1].strip()
    return value


def _normalize_confirmation(text: str) -> str:
    import unicodedata

    value = unicodedata.normalize("NFKD", text.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return " ".join(value.split())
