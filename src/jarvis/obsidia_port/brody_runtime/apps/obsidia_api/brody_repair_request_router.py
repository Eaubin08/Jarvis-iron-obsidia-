"""
apps/obsidia_api/brody_repair_request_router.py
===============================================
ROUTE MANQUANTE — intent `code_debug` → RepairRequest structuré.

Aujourd'hui `code_debug` est produit par :
    apps/obsidia_api/routes/os_trad_ir_reverse.py::_intent
    apps/obsidia_api/brody_machination_composer.py
…mais aucun consommateur ne le convertit en quoi que ce soit d'actionnable.
Brody se contente de retrieval + hydratation + synthèse.

Ce module comble exactement ce trou, et rien de plus :

    message utilisateur  →  RepairRequest(origin="BRODY")

Il ne produit AUCUN patch, AUCUN correctif, AUCUNE décision. Il structure une
demande d'analyse que le moteur de raisonnement externe pourra traiter et
qu'Obsidure pourra tester en sandbox.

Réutilise les détecteurs existants (`has_code_debug_request`) plutôt que d'en
réécrire un.

FRONTIÈRES : decision_authority=KX108_ONLY, emits_act=False,
kernel_mutation=False, memory_write=False, auto_apply=False.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Le contrat vit côté périphérie ; on l'importe sans dupliquer les structures.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from periphery.agents.obsidure_repair_contract import (  # noqa: E402
    REPAIR_BOUNDARY,
    ErrorContextRecord,
    FailureMode,
    RepairRequest,
    is_protected_repair_path,
)

__all__ = [
    "REPAIR_ROUTER_BOUNDARY",
    "is_repair_intent",
    "extract_repo_targets",
    "extract_error_signals",
    "build_repair_request_from_message",
    "attach_repair_request",
]

REPAIR_ROUTER_BOUNDARY: Dict[str, Any] = dict(REPAIR_BOUNDARY)

_EXCERPT_MAX_CHARS = 20000

# Preserve long user objectives for downstream semantic continuity.
#
# 4k was too small for real debugging / repair requests containing
# instructions + code + traceback + contextual constraints.
_OBJECTIVE_MAX_CHARS = 65536

# Intentions backend qui doivent ouvrir la route de réparation.
_REPAIR_INTENTS = frozenset({"code_debug"})
_REPAIR_RISK_FLAGS = frozenset({"code_debug"})

# Signaux d'erreur concrets — servent à distinguer « il y a un échec observé »
# de « on parle de debug en général ».
_ERROR_SIGNAL_PATTERNS: List[tuple[str, str]] = [
    ("TRACEBACK", r"Traceback \(most recent call last\):[\s\S]{0,1500}"),
    ("PY_EXCEPTION", r"\b[A-Z]\w*(?:Error|Exception)\b(?:\s*:\s*[^\n]{0,200})?"),
    ("PYTEST_FAILURE", r"\b(?:FAILED|ERROR)\s+[\w/\\.]+::[\w\[\]\-]+[^\n]{0,200}"),
    ("HTTP_STATUS", r"\b(?:HTTP\s*)?(?:404|409|422|500|502|503)\b[^\n]{0,120}"),
    ("LEAN_ERROR", r"\berror:\s*[^\n]{0,200}"),
    ("ASSERTION", r"\bAssertionError\b[^\n]{0,200}"),
]

_PATH_PATTERN = re.compile(
    r"(?<![\w/\\.])((?:[\w\-\.]+[/\\])+[\w\-\.]+\.(?:py|lean|json|md|yaml|yml|toml))"
)


def is_repair_intent(
    message: str,
    ir_intent: str = "",
    risk_flags: Optional[List[str]] = None,
) -> bool:
    """
    True si le message doit ouvrir une route de réparation.

    Priorité au verdict backend (`ir_intent` / `risk_flags`) — c'est lui qui
    fait autorité. Le détecteur textuel n'est qu'un repli.
    """
    if str(ir_intent or "").strip().lower() in _REPAIR_INTENTS:
        return True
    if set(str(f).lower() for f in (risk_flags or [])) & _REPAIR_RISK_FLAGS:
        return True

    try:
        from apps.obsidia_api.brody_domain_raccord_adapter import has_code_debug_request
        return bool(has_code_debug_request(message))
    except Exception:
        return False


def extract_repo_targets(message: str, repo_root: Optional[Path] = None) -> List[str]:
    """
    Extrait les chemins de fichiers cités qui EXISTENT réellement dans le repo.

    On n'invente pas de cible : un chemin qui n'existe pas n'est pas retenu,
    sauf s'il est explicitement présenté comme à créer — ce que ce module ne
    présume pas. Les zones scellées sont exclues.
    """
    root = repo_root or _REPO_ROOT
    targets: List[str] = []
    for raw in _PATH_PATTERN.findall(message or ""):
        norm = raw.replace("\\", "/").lstrip("./")
        if norm in targets or is_protected_repair_path(norm):
            continue
        if (root / norm).is_file():
            targets.append(norm)
    return targets[:20]


def extract_error_signals(message: str) -> List[ErrorContextRecord]:
    """
    Convertit les traces d'erreur présentes dans le message en ErrorContext.

    Aucune erreur n'est fabriquée : si le message ne contient aucun signal
    concret, la liste est vide et le failure_mode restera ROUTE_INCAPABLE.
    """
    records: List[ErrorContextRecord] = []
    text = message or ""
    seen: set = set()

    for kind, pattern in _ERROR_SIGNAL_PATTERNS:
        for match in re.finditer(pattern, text):
            snippet = match.group(0).strip()
            key = (kind, snippet[:120])
            if key in seen:
                continue
            seen.add(key)
            records.append(ErrorContextRecord(
                attempt=0,
                error_type=f"BRODY_OBSERVED_{kind}",
                raw_details=snippet[:2000],
                first_error_line=snippet.splitlines()[0][:400] if snippet else "",
                mutation_directive="ESCALATE_TO_EXTERNAL_REPAIR",
                recommended_strategy="EXTERNAL_REASONING",
            ))
            if len(records) >= 12:
                return records
    return records


def build_repair_request_from_message(
    message: str,
    ir_intent: str = "",
    risk_flags: Optional[List[str]] = None,
    repo_root: Optional[Path] = None,
    include_excerpts: bool = True,
) -> Optional[RepairRequest]:
    """
    Convertit un message `code_debug` en RepairRequest.

    Retourne None si le message ne relève pas de la route de réparation —
    aucun RepairRequest vide n'est émis.
    """
    if not is_repair_intent(message, ir_intent, risk_flags):
        return None

    root = repo_root or _REPO_ROOT
    targets = extract_repo_targets(message, root)
    signals = extract_error_signals(message)

    if signals:
        failure_mode = FailureMode.BUILD_ERROR
    elif targets:
        failure_mode = FailureMode.SEMANTIC_REPAIR_REQUIRED
    else:
        # Intent de debug reconnu mais ni trace ni cible : on le dit tel quel.
        failure_mode = FailureMode.ROUTE_INCAPABLE

    excerpts: Dict[str, str] = {}
    if include_excerpts:
        for rel in targets:
            f = root / rel
            try:
                excerpts[rel] = f.read_text(encoding="utf-8", errors="replace")[:_EXCERPT_MAX_CHARS]
            except Exception:
                continue

    summary = " | ".join([
        f"failure_mode={failure_mode}",
        f"repo_targets={len(targets)}",
        f"error_signals={len(signals)}",
        "origin=BRODY (retrieval seul insuffisant — diagnostic de code requis)",
    ])

    return RepairRequest(
        origin="BRODY",
        objective=(
            str(message or "")[
                :_OBJECTIVE_MAX_CHARS
            ]
        ),
        failure_mode=failure_mode,
        summary=summary,
        error_contexts=signals,
        repo_targets=targets,
        target_excerpts=excerpts,
        attempts_spent=0,
        sandbox_dir="",
        tests_hint=[],
    )


def attach_repair_request(
    response: Dict[str, Any],
    message: str,
    ir_intent: str = "",
    risk_flags: Optional[List[str]] = None,
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Enrichit une réponse Brody avec `repair_request` quand la route s'applique.

    Ne modifie ni `response`/`response_md`, ni aucune frontière. Purement
    additif : un consommateur qui ignore la clé garde le comportement actuel.
    """
    try:
        request = build_repair_request_from_message(
            message, ir_intent, risk_flags, repo_root
        )
    except Exception as exc:
        response["repair_request"] = None
        response["repair_route_status"] = f"REPAIR_ROUTE_ERROR: {type(exc).__name__}"
        return response

    if request is None:
        response["repair_request"] = None
        response["repair_route_status"] = "NOT_A_REPAIR_INTENT"
        return response

    response["repair_request"] = request.to_dict()
    response["repair_route_status"] = "REPAIR_REQUEST_EMITTED"
    response["repair_boundary"] = dict(REPAIR_ROUTER_BOUNDARY)
    return response
