"""Governed CREATE_FILE and APPLY_PATCH command seams for Jarjar."""
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
class GovernedFileOpsConfig:
    execution_worktree_path: Path
    main_worktree_path: Path
    branch_name: str
    base_sha: str
    stores_base_dir: Path
    obsidia_root: Path | None = None


def _load_obsidia(config: GovernedFileOpsConfig):
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
    pc2 = importlib.import_module("obsidia_pc_capabilities_v2")
    bridge = importlib.import_module("jarjar_executor_bridge_v0")
    return pc2, bridge


@dataclass
class GovernedCreateFileCoordinator:
    config: GovernedFileOpsConfig
    prepare_fn: Callable[..., dict[str, Any]]
    execute_fn: Callable[..., dict[str, Any]]
    executor_factory: Callable[[Path], Any]
    pending: dict[str, Any] | None = field(default=None, init=False)

    @classmethod
    def from_obsidia(cls, config: GovernedFileOpsConfig) -> "GovernedCreateFileCoordinator":
        pc2, bridge = _load_obsidia(config)
        return cls(
            config,
            pc2.pc_v2_create_file_prepare,
            pc2.pc_v2_create_file_execute,
            bridge.make_executor,
        )

    def prepare(self, target_path: str, content: bytes, *, session_id: str) -> str:
        if self.pending is not None:
            return "Une création de fichier gouvernée est déjà en attente. Confirme-la ou annule-la."
        result = self.prepare_fn(
            target_path,
            content,
            execution_worktree_path=self.config.execution_worktree_path,
            main_worktree_path=self.config.main_worktree_path,
            branch_name=self.config.branch_name,
            base_sha=self.config.base_sha,
            stores_base_dir=self.config.stores_base_dir,
            session_id=session_id,
        )
        if result.get("status") != _PREPARED_STATUS:
            reason = result.get("reason") or result.get("status") or "PREPARE_REJECTED"
            return f"Création de fichier refusée à la préparation : {reason}"
        self.pending = result
        eah = str(result.get("execution_authority_hash", ""))
        return (
            f"Création de fichier préparée : {target_path}. EAH {eah[:12] if eah else 'UNKNOWN'}. "
            "Dis « confirme la creation du fichier » pour autoriser l'exécution."
        )

    def approve(self, *, session_id: str) -> str:
        prepared = self.pending
        if prepared is None:
            return "Aucune création de fichier gouvernée n'est en attente."
        eah = str(prepared.get("execution_authority_hash", ""))
        if not eah:
            self.pending = None
            return "Création de fichier annulée : EAH manquant."
        executor = self.executor_factory(Path(self.config.execution_worktree_path).resolve())
        result = self.execute_fn(
            prepared,
            eah,
            f"JARJAR_HUD_CONFIRM_CREATE_FILE:{session_id}",
            stores_base_dir=self.config.stores_base_dir,
            repo_root=self.config.execution_worktree_path,
            session_id=session_id,
            executor=executor,
        )
        if result.get("status") == _EXECUTED_STATUS:
            self.pending = None
            return f"Fichier créé et prouvé : {result.get('target_path', '')}."
        reason = result.get("reason") or result.get("status") or "EXECUTE_REJECTED"
        return f"Fichier non créé : {reason}"

    def cancel(self) -> str:
        if self.pending is None:
            return "Aucune création de fichier gouvernée n'est en attente."
        self.pending = None
        return "Création de fichier gouvernée annulée avant exécution."


@dataclass
class GovernedApplyPatchCoordinator:
    config: GovernedFileOpsConfig
    prepare_fn: Callable[..., dict[str, Any]]
    execute_fn: Callable[..., dict[str, Any]]
    executor_factory: Callable[[Path], Any]
    pending: dict[str, Any] | None = field(default=None, init=False)

    @classmethod
    def from_obsidia(cls, config: GovernedFileOpsConfig) -> "GovernedApplyPatchCoordinator":
        pc2, bridge = _load_obsidia(config)
        return cls(
            config,
            pc2.pc_v2_apply_patch_prepare,
            pc2.pc_v2_apply_patch_execute,
            bridge.make_executor,
        )

    def prepare(self, patch_content: str, *, session_id: str) -> str:
        if self.pending is not None:
            return "Un patch gouverné est déjà en attente. Confirme-le ou annule-le."
        result = self.prepare_fn(
            patch_content,
            execution_worktree_path=self.config.execution_worktree_path,
            main_worktree_path=self.config.main_worktree_path,
            branch_name=self.config.branch_name,
            base_sha=self.config.base_sha,
            stores_base_dir=self.config.stores_base_dir,
            session_id=session_id,
        )
        if result.get("status") != _PREPARED_STATUS:
            reason = result.get("reason") or result.get("status") or "PREPARE_REJECTED"
            return f"Patch refusé à la préparation : {reason}"
        self.pending = result
        targets = ", ".join(result.get("target_paths", []))
        eah = str(result.get("execution_authority_hash", ""))
        return (
            f"Patch préparé pour : {targets}. EAH {eah[:12] if eah else 'UNKNOWN'}. "
            "Dis « confirme le patch » pour autoriser l'exécution."
        )

    def approve(self, *, session_id: str) -> str:
        prepared = self.pending
        if prepared is None:
            return "Aucun patch gouverné n'est en attente."
        eah = str(prepared.get("execution_authority_hash", ""))
        if not eah:
            self.pending = None
            return "Patch annulé : EAH manquant."
        executor = self.executor_factory(Path(self.config.execution_worktree_path).resolve())
        result = self.execute_fn(
            prepared,
            eah,
            f"JARJAR_HUD_CONFIRM_PATCH:{session_id}",
            stores_base_dir=self.config.stores_base_dir,
            repo_root=self.config.execution_worktree_path,
            session_id=session_id,
            executor=executor,
        )
        if result.get("status") == _EXECUTED_STATUS:
            self.pending = None
            return "Patch appliqué et prouvé : " + ", ".join(result.get("target_paths", [])) + "."
        reason = result.get("reason") or result.get("status") or "EXECUTE_REJECTED"
        return f"Patch non appliqué : {reason}"

    def cancel(self) -> str:
        if self.pending is None:
            return "Aucun patch gouverné n'est en attente."
        self.pending = None
        return "Patch gouverné annulé avant exécution."


@dataclass
class GovernedFileOpsCommandHandler:
    create_file: GovernedCreateFileCoordinator
    apply_patch: GovernedApplyPatchCoordinator

    _create_re = re.compile(
        r"^(?:cree|crée)\s+(?:le\s+)?fichier\s+(.+?)\s+avec\s+contenu\s+(.+)$",
        re.IGNORECASE | re.DOTALL,
    )

    def handle(self, text: str, *, session_id: str) -> str | None:
        clean = text.strip()
        if not clean:
            return None
        normalized = _normalize(clean)

        if normalized in {"confirme creation fichier", "confirme la creation du fichier"}:
            return self.create_file.approve(session_id=session_id)
        if normalized in {"annule creation fichier", "annule la creation du fichier"}:
            return self.create_file.cancel()
        if normalized == "confirme le patch":
            return self.apply_patch.approve(session_id=session_id)
        if normalized == "annule le patch":
            return self.apply_patch.cancel()

        create = self._create_re.match(clean)
        if create is not None:
            target = _strip_quotes(create.group(1).strip())
            content = create.group(2)
            if not target:
                return "Commande de création de fichier incomplète."
            return self.create_file.prepare(target, content.encode("utf-8"), session_id=session_id)

        lowered = clean.casefold()
        for prefix in ("applique le patch\n", "prepare le patch\n", "prépare le patch\n"):
            if lowered.startswith(prefix):
                patch = clean[len(prefix):]
                if not patch.strip():
                    return "Patch vide."
                return self.apply_patch.prepare(patch, session_id=session_id)
        return None


def governed_file_ops_from_environment() -> GovernedFileOpsCommandHandler | None:
    enabled = os.getenv("JARJAR_GOVERNED_FILE_OPS", "0").strip().lower()
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
        raise RuntimeError("Missing governed-file-ops environment: " + ", ".join(missing))

    root_raw = os.getenv("OBSIDIA_OPENJARVIS_ROOT", "").strip()
    config = GovernedFileOpsConfig(
        execution_worktree_path=Path(required["OBSIDIA_EXECUTION_WORKTREE"]).resolve(),
        main_worktree_path=Path(required["OBSIDIA_MAIN_WORKTREE"]).resolve(),
        branch_name=required["OBSIDIA_BRANCH_NAME"],
        base_sha=required["OBSIDIA_BASE_SHA"],
        stores_base_dir=Path(required["OBSIDIA_STORES_BASE"]).resolve(),
        obsidia_root=Path(root_raw).resolve() if root_raw else None,
    )
    return GovernedFileOpsCommandHandler(
        GovernedCreateFileCoordinator.from_obsidia(config),
        GovernedApplyPatchCoordinator.from_obsidia(config),
    )


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1].strip()
    return value


def _normalize(text: str) -> str:
    import unicodedata
    value = unicodedata.normalize("NFKD", text.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return " ".join(value.split())
