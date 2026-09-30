"""
periphery/agents/obsidure_repair_contract.py
============================================
CONTRAT DE RÉPARATION EXTERNE — vocabulaire partagé Obsidure ↔ Brody ↔ moteur externe.

Ce module est volontairement NEUTRE :
  - aucun import d'agent_obsidure (pas de cycle)
  - aucun import FastAPI / requests
  - aucune référence à un problème, un domaine ou un théorème particulier

Il définit uniquement les trois objets du cycle :

    ErrorContextRecord   ce qui a échoué, structuré (miroir sérialisable de
                         periphery.agents.agent_obsidure.ErrorContext)
    RepairRequest        Obsidure/Brody → moteur de raisonnement externe
    RepairProposal       moteur de raisonnement externe → Obsidure
    RepairVerdict        Obsidure après test sandbox de la proposition

FRONTIÈRES ABSOLUES (non négociables, vérifiées par assert_repair_boundary) :
    decision_authority = KX108_ONLY
    emits_act          = False
    kernel_mutation    = False
    memory_write       = False
    canonical_write    = False
    auto_apply         = False
    auto_commit        = False
    auto_push          = False

Le moteur externe PROPOSE. Obsidure TESTE en sandbox. L'humain (ROLE_005) APPLIQUE.
Aucune étape de ce module n'écrit hors sandbox ni n'émet ALLOW/HOLD/BLOCK.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "REPAIR_BOUNDARY",
    "PROTECTED_INFIXES_REPAIR",
    "ALLOWED_REPAIR_PREFIXES",
    "ALLOWED_REPAIR_EXTS",
    "FailureMode",
    "ErrorContextRecord",
    "RepairCandidateFile",
    "RepairRequest",
    "RepairProposal",
    "RepairVerdict",
    "assert_repair_boundary",
    "is_protected_repair_path",
    "validate_repair_proposal",
    "repair_request_to_json",
    "repair_proposal_from_dict",
]


# ===========================================================================
# 0.  FRONTIÈRES
# ===========================================================================

REPAIR_BOUNDARY: Dict[str, Any] = {
    "decision_authority": "KX108_ONLY",
    "emits_act": False,
    "emits_verdict": False,
    "kernel_mutation": False,
    "memory_write": False,
    "canonical_write": False,
    "auto_apply": False,
    "auto_commit": False,
    "auto_push": False,
    "sandbox_mode": "HUMAN_APPROVED_WRITE",
    "external_engine_role": "PROPOSE_ONLY",
}

# Miroir local des chemins protégés — dupliqué volontairement pour garder ce
# module sans dépendance. Toute divergence est détectée par le test de
# non-régression test_repair_contract.py::test_protected_infixes_in_sync.
PROTECTED_INFIXES_REPAIR: Tuple[str, ...] = (
    "server.kernel.sealed.cjs",
    "proofs/V18_",
    "proofs/lean/57_preuves",
    "merkle_seal.json",
    "rfc3161",
)

# Zones dans lesquelles un RepairProposal a le droit de proposer un fichier.
# Volontairement large (périphérie + apps + scripts + tests) mais jamais
# proofs/ canoniques, jamais kernel scellé.
ALLOWED_REPAIR_PREFIXES: Tuple[str, ...] = (
    "periphery/",
    "apps/obsidia_api/",
    "scripts/",
    "tests/",
    "connectors/",
    "domains/",
    "sigma/",
)

ALLOWED_REPAIR_EXTS: Tuple[str, ...] = (".py", ".json", ".md", ".yaml", ".yml", ".toml")


class FailureMode:
    """Modes d'échec généraux — indépendants du langage et du domaine."""

    NO_ARTIFACT_PRODUCED = "NO_ARTIFACT_PRODUCED"
    CONFORMITY_VIOLATION = "CONFORMITY_VIOLATION"
    BUILD_ERROR = "BUILD_ERROR"
    SEMANTIC_REPAIR_REQUIRED = "SEMANTIC_REPAIR_REQUIRED"
    MAX_ATTEMPTS_REACHED = "MAX_ATTEMPTS_REACHED"
    ROUTE_INCAPABLE = "ROUTE_INCAPABLE"
    UNKNOWN = "UNKNOWN"

    ALL: Tuple[str, ...] = (
        NO_ARTIFACT_PRODUCED,
        CONFORMITY_VIOLATION,
        BUILD_ERROR,
        SEMANTIC_REPAIR_REQUIRED,
        MAX_ATTEMPTS_REACHED,
        ROUTE_INCAPABLE,
        UNKNOWN,
    )


def assert_repair_boundary(payload: Dict[str, Any]) -> None:
    """
    Vérifie qu'un payload (request / proposal / verdict) n'a pas relâché une
    frontière. Lève ValueError au premier écart — fail-closed.
    """
    for key, expected in REPAIR_BOUNDARY.items():
        if key in payload and payload[key] != expected:
            raise ValueError(
                f"Frontière violée : {key}={payload[key]!r} (attendu {expected!r})"
            )


# ===========================================================================
# 1.  STRUCTURES
# ===========================================================================


@dataclass
class ErrorContextRecord:
    """
    Miroir sérialisable d'un ErrorContext Obsidure.

    Le champ `error_type` reste libre : Obsidure évolue plus vite que ce contrat,
    et un type inconnu doit traverser le pont sans être perdu.
    """

    attempt: int = 0
    error_type: str = "UNKNOWN"
    raw_details: str = ""
    target_path: str = ""
    build_stderr: str = ""
    first_error_line: str = ""
    violated_keywords: List[str] = field(default_factory=list)
    mutation_directive: str = ""
    recommended_strategy: str = ""

    @classmethod
    def from_obj(cls, obj: Any) -> "ErrorContextRecord":
        """Construit depuis un ErrorContext Obsidure (duck-typing, fail-soft)."""
        def _g(name: str, default: Any) -> Any:
            return getattr(obj, name, default)

        return cls(
            attempt=int(_g("attempt", 0) or 0),
            error_type=str(_g("error_type", "UNKNOWN") or "UNKNOWN"),
            raw_details=str(_g("raw_details", "") or "")[:2000],
            # target_hint (chemin repo concerné) prime sur protected_path :
            # sans lui, le provider de raisonnement perd la cible du défaut.
            target_path=str(_g("target_hint", "") or _g("protected_path", "") or ""),
            build_stderr=str(_g("lean_stderr", "") or "")[:4000],
            first_error_line=str(_g("lean_error_line", "") or "")[:400],
            violated_keywords=[str(k) for k in (_g("violated_keywords", []) or [])],
            mutation_directive=str(_g("mutation_directive", "") or ""),
            recommended_strategy=str(_g("recommended_strategy", "") or ""),
        )


@dataclass
class RepairCandidateFile:
    """
    Un fichier candidat proposé par le moteur externe.

    `full_content` est le contenu COMPLET du fichier après réparation.
    On n'accepte pas de diff partiel : le test sandbox doit pouvoir écrire le
    fichier tel quel et le compiler. `base_sha256` permet à Obsidure de détecter
    que le fichier de référence a bougé depuis l'émission du RepairRequest.
    """

    path: str
    full_content: str
    change_kind: str = "MODIFY"  # MODIFY | CREATE
    base_sha256: str = ""
    rationale: str = ""


@dataclass
class RepairRequest:
    """
    Émis par Obsidure (cycle en échec) ou par Brody (intent code_debug).

    C'est une DEMANDE D'ANALYSE, pas un ordre. Elle ne contient aucun droit
    d'écriture et ne préjuge d'aucune solution.
    """

    request_id: str = field(default_factory=lambda: f"rr_{uuid.uuid4().hex[:12]}")
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    origin: str = "OBSIDURE"  # OBSIDURE | BRODY
    objective: str = ""
    failure_mode: str = FailureMode.UNKNOWN
    summary: str = ""
    error_contexts: List[ErrorContextRecord] = field(default_factory=list)
    repo_targets: List[str] = field(default_factory=list)
    target_excerpts: Dict[str, str] = field(default_factory=dict)
    attempts_spent: int = 0
    sandbox_dir: str = ""
    tests_hint: List[str] = field(default_factory=list)
    boundary: Dict[str, Any] = field(default_factory=lambda: dict(REPAIR_BOUNDARY))

    def __post_init__(self) -> None:
        if self.failure_mode not in FailureMode.ALL:
            self.failure_mode = FailureMode.UNKNOWN
        assert_repair_boundary(self.boundary)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairProposal:
    """
    Retourné par un moteur de raisonnement externe (Claude, autre agent, humain).

    Aucune autorité : Obsidure la teste, l'humain l'applique.
    """

    proposal_id: str = field(default_factory=lambda: f"rp_{uuid.uuid4().hex[:12]}")
    request_id: str = ""
    engine: str = "EXTERNAL_REASONING_ENGINE"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rationale: str = ""
    candidate_files: List[RepairCandidateFile] = field(default_factory=list)
    tests_to_run: List[str] = field(default_factory=list)
    confidence: str = "UNKNOWN"  # LOW | MEDIUM | HIGH | UNKNOWN
    boundary: Dict[str, Any] = field(default_factory=lambda: dict(REPAIR_BOUNDARY))

    def __post_init__(self) -> None:
        assert_repair_boundary(self.boundary)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairVerdict:
    """
    Résultat du test sandbox d'un RepairProposal par Obsidure.

    status :
        PASS               tous les candidats compilent, conformes, tests OK
        PARTIAL            compile/conforme mais tests non concluants ou absents
        BLOCKED            frontière violée / chemin protégé / compile KO
        NO_CANDIDATE       proposition vide — jamais un succès
    """

    verdict_id: str = field(default_factory=lambda: f"rv_{uuid.uuid4().hex[:12]}")
    request_id: str = ""
    proposal_id: str = ""
    status: str = "BLOCKED"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    errors: List[Dict[str, Any]] = field(default_factory=list)
    compiled_files: List[str] = field(default_factory=list)
    sandbox_dir: str = ""
    tests_executed: List[Dict[str, Any]] = field(default_factory=list)
    resume_objective: str = ""
    tested_artifacts: List[Dict[str, Any]] = field(default_factory=list)
    boundary: Dict[str, Any] = field(default_factory=lambda: dict(REPAIR_BOUNDARY))

    def __post_init__(self) -> None:
        assert_repair_boundary(self.boundary)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ===========================================================================
# 2.  VALIDATION
# ===========================================================================


def is_protected_repair_path(path_str: str) -> bool:
    """True si le chemin touche une zone scellée / canonique."""
    norm = str(path_str).replace("\\", "/").lower()
    return any(infx.lower() in norm for infx in PROTECTED_INFIXES_REPAIR)


def validate_repair_proposal(proposal: RepairProposal) -> List[Dict[str, Any]]:
    """
    Contrôle statique d'un RepairProposal AVANT tout écriture sandbox.

    Retourne la liste des violations (vide = acceptable pour test sandbox).
    Une proposition sans candidat est une violation : zéro erreur n'est pas
    un succès quand un artefact est attendu.
    """
    errors: List[Dict[str, Any]] = []

    try:
        assert_repair_boundary(proposal.boundary)
    except ValueError as exc:
        errors.append({"type": "REPAIR_BOUNDARY_VIOLATION", "path": "", "details": str(exc)})

    if not proposal.candidate_files:
        errors.append({
            "type": "REPAIR_NO_CANDIDATE",
            "path": "",
            "details": "RepairProposal sans candidate_files — aucun artefact proposé.",
        })

    seen: set = set()
    for cand in proposal.candidate_files:
        raw = str(getattr(cand, "path", "") or "")
        norm = raw.replace("\\", "/").lstrip("./")

        if not norm:
            errors.append({"type": "REPAIR_EMPTY_PATH", "path": raw, "details": "Chemin vide."})
            continue

        if norm in seen:
            errors.append({
                "type": "REPAIR_DUPLICATE_PATH",
                "path": norm,
                "details": "Le même chemin est proposé deux fois.",
            })
        seen.add(norm)

        if ".." in Path(norm).parts or Path(norm).is_absolute() or re.match(r"^[A-Za-z]:", norm):
            errors.append({
                "type": "REPAIR_PATH_ESCAPE",
                "path": norm,
                "details": "Chemin absolu ou remontant hors du repo.",
            })
            continue

        if is_protected_repair_path(norm):
            errors.append({
                "type": "REPAIR_PROTECTED_PATH",
                "path": norm,
                "details": "Zone scellée / canonique — lecture seule.",
            })
            continue

        if not norm.startswith(ALLOWED_REPAIR_PREFIXES):
            errors.append({
                "type": "REPAIR_PATH_OUT_OF_SCOPE",
                "path": norm,
                "details": f"Hors zones autorisées {ALLOWED_REPAIR_PREFIXES}.",
            })
            continue

        if Path(norm).suffix.lower() not in ALLOWED_REPAIR_EXTS:
            errors.append({
                "type": "REPAIR_INVALID_EXTENSION",
                "path": norm,
                "details": f"Extension refusée. Autorisées : {ALLOWED_REPAIR_EXTS}.",
            })
            continue

        if not str(getattr(cand, "full_content", "") or "").strip():
            errors.append({
                "type": "REPAIR_EMPTY_CONTENT",
                "path": norm,
                "details": "full_content vide — un fichier vide n'est pas une réparation.",
            })

        if str(getattr(cand, "change_kind", "")) not in ("MODIFY", "CREATE"):
            errors.append({
                "type": "REPAIR_INVALID_CHANGE_KIND",
                "path": norm,
                "details": "change_kind doit valoir MODIFY ou CREATE.",
            })

    return errors


# ===========================================================================
# 3.  SÉRIALISATION
# ===========================================================================


def repair_request_to_json(request: RepairRequest) -> str:
    return json.dumps(request.to_dict(), indent=2, ensure_ascii=False)


def repair_proposal_from_dict(data: Dict[str, Any]) -> RepairProposal:
    """
    Reconstruit un RepairProposal depuis un dict (fichier JSON déposé par le
    moteur externe). Fail-closed : les champs inconnus sont ignorés, les
    candidats mal formés produiront une violation à la validation.
    """
    cands: List[RepairCandidateFile] = []
    for raw in data.get("candidate_files", []) or []:
        if not isinstance(raw, dict):
            continue
        cands.append(RepairCandidateFile(
            path=str(raw.get("path", "")),
            full_content=str(raw.get("full_content", "")),
            change_kind=str(raw.get("change_kind", "MODIFY")),
            base_sha256=str(raw.get("base_sha256", "")),
            rationale=str(raw.get("rationale", "")),
        ))

    # La frontière n'est JAMAIS lue depuis la source externe : elle est imposée.
    # Un moteur externe qui tenterait de poser auto_apply=True voit sa valeur
    # ignorée sans faire échouer le parsing — le relâchement est structurellement
    # impossible, pas seulement refusé.
    boundary = dict(REPAIR_BOUNDARY)

    proposal = RepairProposal(
        request_id=str(data.get("request_id", "")),
        engine=str(data.get("engine", "EXTERNAL_REASONING_ENGINE")),
        rationale=str(data.get("rationale", "")),
        candidate_files=cands,
        tests_to_run=[str(t) for t in (data.get("tests_to_run") or [])],
        confidence=str(data.get("confidence", "UNKNOWN")),
        boundary=boundary,
    )
    if data.get("proposal_id"):
        proposal.proposal_id = str(data["proposal_id"])
    return proposal
