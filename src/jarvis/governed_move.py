"""Two-phase governed file-move seam between Jarjar and Obsidia.

Jarjar never decides whether a move is authorized.  This coordinator only:
1. asks Obsidia to PREPARE the operation,
2. keeps the prepared envelope pending,
3. consumes an explicit human confirmation,
4. asks Obsidia/KX108 to EXECUTE using Jarjar as the physical executor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import base64
import hashlib
import json
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
            f"EAH {short_eah}. Dis « je confirme » ou « confirme le déplacement » pour autoriser l'étape d'exécution."
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

    def restore_last_execution_from_stores(self) -> dict[str, Any] | None:
        """Restore the latest governed MOVE from persisted canonical artifacts.

        This is a readonly recovery/indexing path for audit/history after a
        Jarjar restart. It never invokes KX108 and never calls an executor.
        """
        if self.last_execution_result is not None:
            return self.last_execution_result

        try:
            stores = Path(self.config.stores_base_dir)
            sar_dir = stores / "sar"
            if not sar_dir.is_dir():
                return None

            candidates = [p for p in sar_dir.glob("sar-*.json") if p.is_file()]
            if not candidates:
                return None
            latest_path = max(candidates, key=lambda p: p.stat().st_mtime_ns)

            import json
            sar = json.loads(latest_path.read_text(encoding="utf-8"))
            if sar.get("operation_type") != "V2_MOVE_FILE":
                return None

            v2id = str(sar.get("batch_execution_id", ""))
            descriptor = {}
            if v2id:
                dp = stores / "v2exec" / f"{v2id}.json"
                if dp.is_file():
                    descriptor = json.loads(dp.read_text(encoding="utf-8")).get("descriptor") or {}

            kx_id = str(sar.get("kx108_pre_decision_record_id", ""))
            gate = "UNKNOWN"
            if kx_id:
                kp = stores / "kxpre" / f"{kx_id}.json"
                if kp.is_file():
                    kx = json.loads(kp.read_text(encoding="utf-8"))
                    gate = str(kx.get("x108_gate", "UNKNOWN"))

            result = {
                "status": "EXECUTED_OK",
                "j5_phase": "EXECUTE",
                "operation_type": "V2_MOVE_FILE",
                "decision_authority": "KX108_ONLY",
                "kx108_pre_gate": gate,
                "source_path": str(descriptor.get("source_path", "")),
                "dest_path": str(descriptor.get("dest_path", sar.get("target_path", ""))),
                "sealed_apply_receipt_id": str(sar.get("sealed_apply_receipt_id", "")),
                "sealed_rollback_evidence_id": str(sar.get("sealed_rollback_evidence_id", "")),
                "receipt": {},
                "_restored_from_persisted_proofs": True,
            }
            self.last_execution_result = result
            return result
        except Exception:
            return None

    def audit_last_execution(self) -> dict[str, Any]:
        result = self.last_execution_result or self.restore_last_execution_from_stores()
        if result is None:
            return {"ok": False, "reason": "NO_LAST_EXECUTION"}

        try:
            root = (
                Path(self.config.obsidia_root).resolve()
                if self.config.obsidia_root is not None
                else _default_obsidia_root()
            )
            scripts = root / "scripts"
            for entry in (str(root), str(scripts)):
                if entry not in sys.path:
                    sys.path.insert(0, entry)

            sev = importlib.import_module("obsidia_sealed_evidence_v0")
            ds = importlib.import_module("obsidia_kx108_decision_store")
            be = importlib.import_module("obsidia_batch_execution")

            stores = Path(self.config.stores_base_dir)
            sar_id = str(result.get("sealed_apply_receipt_id", ""))
            sre_id = str(result.get("sealed_rollback_evidence_id", ""))
            if not sar_id or not sre_id:
                return {"ok": False, "reason": "PROOF_IDS_MISSING"}

            sar = sev.load_sealed_apply_receipt(sar_id, stores / "sar")
            sre = sev.load_sealed_rollback_evidence(sre_id, stores / "sre")
            sar_ok, sar_reason = _verify_v2_move_sar(sar)
            sre_ok, sre_reason = _verify_v2_move_sre(sre)

            kx_id = str((sar or {}).get("kx108_pre_decision_record_id", ""))
            approval_id = str((sar or {}).get("approval_id", ""))
            kx = ds.load_kx108_decision_record(kx_id, stores / "kxpre") if kx_id else None
            approval = be.load_approval_artifact(approval_id, stores / "approval") if approval_id else None
            kx_ok, kx_reason = ds.verify_kx108_decision_record(kx)
            approval_ok, approval_reason = be.verify_approval_artifact(approval)

            sre_canonical_hash = (
                hashlib.sha256(
                    json.dumps(sre, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest()
                if sre
                else ""
            )
            links_ok = bool(
                sar
                and sre
                and kx
                and approval
                and sar.get("sealed_rollback_evidence_id") == sre_id
                and sar.get("sealed_rollback_evidence_hash") == sre_canonical_hash
                and sar.get("kx108_pre_decision_record_id") == sre.get("kx108_pre_decision_record_id")
                and sar.get("kx108_pre_decision_record_hash") == sre.get("kx108_pre_decision_record_hash")
                and sar.get("kx108_pre_decision_record_hash") == kx.get("decision_record_hash")
                and sar.get("approval_id") == sre.get("approval_id") == approval_id
                and sar.get("execution_authority_hash") == sre.get("execution_authority_hash")
            )
            ok = bool(sar_ok and sre_ok and kx_ok and approval_ok and links_ok)
            return {
                "ok": ok,
                "sar_ok": sar_ok,
                "sar_reason": sar_reason,
                "sre_ok": sre_ok,
                "sre_reason": sre_reason,
                "kx_ok": kx_ok,
                "kx_reason": kx_reason,
                "approval_ok": approval_ok,
                "approval_reason": approval_reason,
                "links_ok": links_ok,
                "kx_record": kx,
                "approval_id": approval_id,
                "kx108_pre_decision_record_id": kx_id,
                "sealed_apply_receipt_id": sar_id,
                "sealed_rollback_evidence_id": sre_id,
            }
        except Exception as exc:
            return {"ok": False, "reason": f"AUDIT_ERROR:{type(exc).__name__}"}

    def replay_last_decision(self) -> dict[str, Any]:
        audit = self.audit_last_execution()
        if not audit.get("ok"):
            return {"ok": False, "reason": audit.get("reason") or "AUDIT_FAILED", "audit": audit}

        record = audit.get("kx_record") or {}
        envelope = record.get("canonical_envelope") or {}
        return {
            "ok": True,
            "decision_record_id": audit.get("kx108_pre_decision_record_id", ""),
            "x108_gate": record.get("x108_gate", envelope.get("x108_gate", "UNKNOWN")),
            "reason_code": record.get("reason_code", envelope.get("reason_code", "UNKNOWN")),
            "decision_record_hash": record.get("decision_record_hash", ""),
            "replay_mode": "READ_ONLY_PERSISTED_DECISION",
        }

    def cancel(self) -> str:
        if self.pending is None:
            return "Aucun déplacement gouverné n'est en attente."
        self.pending = None
        return "Déplacement gouverné annulé avant exécution."


@dataclass
class GovernedMoveCommandHandler:
    coordinator: GovernedMoveCoordinator

    _move_re = re.compile(
        r"\b(?:deplace|déplace|deplaces|déplaces|deplacer|déplacer)\b\s+"
        r"(?:le\s+fichier\s+)?(.+?)\s+vers\s+(.+)$",
        re.IGNORECASE,
    )

    def handle(self, text: str, *, session_id: str) -> str | None:
        clean = text.strip()
        if not clean:
            return None

        normalized = _normalize_confirmation(clean)

        replay_reply = self._replay_follow_up(normalized)
        if replay_reply is not None:
            return replay_reply

        audit_reply = self._audit_follow_up(normalized)
        if audit_reply is not None:
            return audit_reply

        history_reply = self._history_follow_up(normalized)
        if history_reply is not None:
            return history_reply

        proof_reply = self._proof_follow_up(normalized)
        if proof_reply is not None:
            return proof_reply

        if normalized in {"annule deplacement", "annule le deplacement"}:
            return self.coordinator.cancel()

        if self.coordinator.pending is not None and _is_positive_pending_confirmation(normalized):
            return self.coordinator.approve(session_id=session_id)

        if self.coordinator.pending is not None and _is_execute_pending_move_request(normalized):
            return self.coordinator.approve(session_id=session_id)

        if self.coordinator.pending is not None and _looks_like_move_confirmation_attempt(normalized):
            return (
                "Confirmation non reconnue. "
                "Dis « je confirme » ou « confirme le déplacement » pour autoriser l'étape d'exécution."
            )

        if self.coordinator.pending is None and (
            _is_positive_pending_confirmation(normalized)
            or _is_execute_pending_move_request(normalized)
        ):
            return self.coordinator.approve(session_id=session_id)

        match = self._move_re.search(clean)
        if match is None:
            if _looks_like_governed_move_intent(normalized):
                if self.coordinator.pending is not None:
                    return (
                        "Un déplacement gouverné est déjà préparé. "
                        "Dis « je confirme », « fais le déplacement » ou annule-le."
                    )
                return (
                    "J'ai détecté une demande de déplacement, mais pas deux chemins complets. "
                    "Indique le fichier source puis la destination."
                )
            return None

        source = _normalize_spoken_path(_clean_move_operand(_strip_quotes(match.group(1).strip())))
        dest = _normalize_spoken_path(_clean_move_operand(_strip_quotes(match.group(2).strip())))
        if not source or not dest:
            return "Commande de déplacement incomplète."
        return self.coordinator.prepare(source, dest, session_id=session_id)

    def _history_follow_up(self, normalized: str) -> str | None:
        if not _looks_like_history_question(normalized):
            return None
        result = (
            self.coordinator.last_execution_result
            or self.coordinator.restore_last_execution_from_stores()
        )
        if result is None:
            return "Aucune action gouvernée persistée n'a été retrouvée."
        source = str(result.get("source_path", ""))
        dest = str(result.get("dest_path", ""))
        status = str(result.get("status", "UNKNOWN"))
        return f"Dernière action gouvernée : déplacement {source} → {dest}. Statut={status}."

    def _audit_follow_up(self, normalized: str) -> str | None:
        if not _looks_like_audit_question(normalized):
            return None
        audit = self.coordinator.audit_last_execution()
        if not audit.get("ok"):
            reason = audit.get("reason") or "PROOF_CHAIN_INVALID"
            return f"Audit readonly du dernier déplacement : FAIL ({reason})."
        return (
            "Audit readonly du dernier déplacement : PASS. "
            f"Approval={audit.get('approval_id')}. "
            f"KX108={audit.get('kx108_pre_decision_record_id')}. "
            f"SRE={audit.get('sealed_rollback_evidence_id')}. "
            f"SAR={audit.get('sealed_apply_receipt_id')}. "
            "Chaîne de liaison vérifiée ; aucune action réexécutée."
        )

    def _replay_follow_up(self, normalized: str) -> str | None:
        if not _looks_like_replay_question(normalized):
            return None
        replay = self.coordinator.replay_last_decision()
        if not replay.get("ok"):
            return f"Replay readonly impossible : {replay.get('reason', 'AUDIT_FAILED')}."
        return (
            "Replay readonly de la dernière décision KX108 : "
            f"Decision={replay.get('decision_record_id')}. "
            f"Gate={replay.get('x108_gate')}. "
            f"Reason={replay.get('reason_code')}. "
            f"Hash={replay.get('decision_record_hash')}. "
            "Mode=READ_ONLY_PERSISTED_DECISION ; aucune exécution déclenchée."
        )

    def _proof_follow_up(self, normalized: str) -> str | None:
        if not _looks_like_proof_question(normalized):
            return None
        result = (
            self.coordinator.last_execution_result
            or self.coordinator.restore_last_execution_from_stores()
        )
        if result is None:
            return None

        source = str(result.get("source_path", ""))
        dest = str(result.get("dest_path", ""))
        gate = str(result.get("kx108_pre_gate", "UNKNOWN"))
        sre = str(result.get("sealed_rollback_evidence_id", "UNKNOWN"))
        sar = str(result.get("sealed_apply_receipt_id", "UNKNOWN"))
        receipt = result.get("receipt") or {}
        receipt_id = str(
            receipt.get("receipt_id")
            or ("NOT_PERSISTED_IN_V2" if result.get("_restored_from_persisted_proofs") else "UNKNOWN")
        )
        return (
            f"Preuves du dernier déplacement gouverné : {source} → {dest}. "
            f"KX108_PRE={gate}. Receipt={receipt_id}. SRE={sre}. SAR={sar}. "
            "État réalisé vérifié par l'exécuteur gouverné."
        )


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


def _is_positive_pending_confirmation(normalized: str) -> bool:
    """Accept natural confirmation only for the already-pending MOVE.

    This never authorizes anything without pending state, and obvious
    negations or references to another governed capability remain excluded.
    """
    if not normalized:
        return False
    if re.search(r"\b(?:ne|pas|non|annule|annuler|refuse|refuser)\b", normalized):
        return False
    other_capability_markers = (
        "creation",
        "cree",
        "creer",
        "dossier",
        "repertoire",
        "patch",
        "rollback",
        "retour arriere",
    )
    if any(marker in normalized for marker in other_capability_markers):
        return False

    exact = {
        "confirme",
        "je confirme",
        "oui je confirme",
        "ok je confirme",
        "d accord je confirme",
        "vas y je confirme",
        "confirme deplacement",
        "confirme le deplacement",
        "je confirme deplacement",
        "je confirme le deplacement",
    }
    if normalized in exact:
        return True

    # Natural emphatic confirmations remain bounded to explicit "je confirme".
    return bool(re.search(r"\bje confirme\b", normalized))


def _is_execute_pending_move_request(normalized: str) -> bool:
    """Treat a bounded natural execute phrase as confirmation of the sole pending MOVE."""
    if not normalized:
        return False
    if re.search(r"\b(?:ne|pas|non|annule|annuler|refuse|refuser)\b", normalized):
        return False
    phrases = (
        "fais le deplacement",
        "fait le deplacement",
        "effectue le deplacement",
        "execute le deplacement",
        "vas y",
        "ok vas y",
        "d accord vas y",
    )
    return any(phrase in normalized for phrase in phrases)


def _looks_like_governed_move_intent(normalized: str) -> bool:
    if not normalized:
        return False
    return bool(
        re.search(
            r"\b(?:deplace|deplaces|deplacer|deplacement|bouge|bouger)\b",
            normalized,
        )
    )


def _clean_move_operand(value: str) -> str:
    return re.sub(r"^(?:le\s+fichier\s+)", "", value.strip(), flags=re.IGNORECASE)


def _looks_like_move_confirmation_attempt(normalized: str) -> bool:
    if not normalized:
        return False
    if not re.search(r"\b(?:confirme|confirmer|confirmation)\b", normalized):
        return False
    other_capability_markers = (
        "creation",
        "cree",
        "creer",
        "dossier",
        "repertoire",
        "patch",
        "rollback",
        "retour arriere",
    )
    return not any(marker in normalized for marker in other_capability_markers)


def _looks_like_proof_question(normalized: str) -> bool:
    if not normalized:
        return False
    proof_terms = ("preuve", "preuves", "receipt", "recu", "trace", "traces")
    if not any(term in normalized for term in proof_terms):
        return False
    return any(
        marker in normalized
        for marker in (
            "quel",
            "quels",
            "quelle",
            "quelles",
            "montre",
            "donne",
            "en sont",
            "du dernier",
            "derniere execution",
        )
    )


def _is_sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value.casefold())
    )


def _verify_v2_move_sre(record: dict[str, Any] | None) -> tuple[bool, str | None]:
    if not isinstance(record, dict):
        return False, "V2_SRE_MISSING"
    required = (
        "sealed_rollback_evidence_id",
        "execution_authority_hash",
        "approval_id",
        "kx108_pre_decision_record_id",
        "kx108_pre_decision_record_hash",
        "target_path",
        "pre_write_sha256",
        "pre_write_size",
        "pre_write_bytes_b64",
        "source_content_sha256",
        "source_kind",
        "operation_type",
        "decision_authority",
    )
    for field_name in required:
        if field_name not in record:
            return False, f"V2_SRE_FIELD_MISSING:{field_name}"
    if record.get("sealed") is not True:
        return False, "V2_SRE_NOT_SEALED"
    if record.get("decision_authority") != "KX108_ONLY":
        return False, "V2_SRE_AUTHORITY_INVALID"
    if record.get("source_kind") != "V2_OPERATION":
        return False, "V2_SRE_SOURCE_KIND_INVALID"
    if record.get("operation_type") != "V2_MOVE_FILE":
        return False, "V2_SRE_OPERATION_INVALID"
    for field_name in (
        "execution_authority_hash",
        "kx108_pre_decision_record_hash",
        "pre_write_sha256",
        "source_content_sha256",
    ):
        if not _is_sha256_hex(record.get(field_name)):
            return False, f"V2_SRE_HASH_INVALID:{field_name}"
    try:
        preimage = base64.b64decode(record.get("pre_write_bytes_b64"), validate=True)
    except Exception:
        return False, "V2_SRE_PREIMAGE_INVALID"
    if hashlib.sha256(preimage).hexdigest() != record.get("pre_write_sha256"):
        return False, "V2_SRE_PREIMAGE_HASH_MISMATCH"
    if len(preimage) != record.get("pre_write_size"):
        return False, "V2_SRE_PREIMAGE_SIZE_MISMATCH"
    return True, None


def _verify_v2_move_sar(record: dict[str, Any] | None) -> tuple[bool, str | None]:
    if not isinstance(record, dict):
        return False, "V2_SAR_MISSING"
    required = (
        "sealed_apply_receipt_id",
        "execution_authority_hash",
        "approval_id",
        "kx108_pre_decision_record_id",
        "kx108_pre_decision_record_hash",
        "sealed_rollback_evidence_id",
        "sealed_rollback_evidence_hash",
        "target_path",
        "target_pre_sha256",
        "target_post_sha256",
        "source_content_sha256",
        "source_kind",
        "operation_type",
        "status",
        "decision_authority",
    )
    for field_name in required:
        if field_name not in record:
            return False, f"V2_SAR_FIELD_MISSING:{field_name}"
    if record.get("sealed") is not True:
        return False, "V2_SAR_NOT_SEALED"
    if record.get("decision_authority") != "KX108_ONLY":
        return False, "V2_SAR_AUTHORITY_INVALID"
    if record.get("source_kind") != "V2_OPERATION":
        return False, "V2_SAR_SOURCE_KIND_INVALID"
    if record.get("operation_type") != "V2_MOVE_FILE":
        return False, "V2_SAR_OPERATION_INVALID"
    if record.get("status") != "APPLIED":
        return False, "V2_SAR_STATUS_INVALID"
    for field_name in (
        "execution_authority_hash",
        "kx108_pre_decision_record_hash",
        "sealed_rollback_evidence_hash",
        "target_pre_sha256",
        "target_post_sha256",
        "source_content_sha256",
    ):
        if not _is_sha256_hex(record.get(field_name)):
            return False, f"V2_SAR_HASH_INVALID:{field_name}"
    if record.get("target_post_sha256") != record.get("source_content_sha256"):
        return False, "V2_SAR_REALIZED_CONTENT_MISMATCH"
    return True, None


def _looks_like_history_question(normalized: str) -> bool:
    return any(
        phrase in normalized
        for phrase in (
            "qu as tu fait",
            "qu est ce que tu as fait",
            "derniere action",
            "derniere operation",
        )
    )


def _looks_like_audit_question(normalized: str) -> bool:
    audit_word = bool(
        re.search(r"\b(?:audit|audite|auditer|verifie|verifier)\b", normalized)
        or re.search(r"\baudi[a-z]{1,5}\b", normalized)
    )
    return bool(
        audit_word
        and any(term in normalized for term in ("action", "operation", "deplacement", "preuve", "dernier"))
    )


def _looks_like_replay_question(normalized: str) -> bool:
    return bool(
        re.search(r"\b(?:rejoue|rejouer|replay)\b", normalized)
        and any(term in normalized for term in ("decision", "kx108", "derniere", "dernier"))
    )


def _normalize_spoken_path(value: str) -> str:
    """Normalize explicit spoken path syntax without fuzzy path guessing."""
    raw = value.strip()
    if not raw:
        return raw

    # If the transcript already contains path punctuation, preserve it except
    # for harmless whitespace around separators.
    if "/" in raw or "\\" in raw:
        raw = re.sub(r"\s*[/\\]+\s*", "/", raw)
        raw = re.sub(r"\s*\.\s*", ".", raw)
        return raw.rstrip(" .")

    import unicodedata

    folded = unicodedata.normalize("NFKD", raw.casefold())
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = re.sub(r"[,:;!?]+", " ", folded)
    folded = re.sub(r"\bbarre\s+oblique\b", " slash ", folded)
    folded = re.sub(r"\banti\s*slash\b", " slash ", folded)
    folded = re.sub(r"\bread\s+me\b", "README", folded, flags=re.IGNORECASE)
    folded = re.sub(r"\bpoint\b", ".", folded)
    folded = re.sub(r"\bslash\b", "/", folded)
    folded = re.sub(r"\btiret\b", "-", folded)
    folded = re.sub(r"\s*/\s*", "/", folded)
    folded = re.sub(r"\s*\.\s*", ".", folded)
    folded = re.sub(r"\s*-\s*", "-", folded)
    folded = re.sub(r"\s+", "", folded)
    return folded.rstrip(".")
