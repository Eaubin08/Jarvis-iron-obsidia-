# runtime_wiring/source_runtime/source_hydration_planner.py
# P36 — Hydration Planner étendu : construit le plan depuis un selected_path complet.
# Sélectionne fichiers preuves, manifests, specs, registry — jamais d'exécutables.
# KX108_ONLY. No ACT. No write. No extraction. Advisory / readonly.
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Extensions autorisées à l'hydratation
_ALLOWED_EXTENSIONS = frozenset({
    ".md", ".yaml", ".yml", ".json", ".txt", ".csv",
})

# Extensions exécutables — jamais sélectionnées
_FORBIDDEN_EXTENSIONS = frozenset({
    ".py", ".pyc", ".ps1", ".bat", ".sh", ".exe",
    ".dll", ".so", ".bin", ".cmd",
})

# Priorité par type de fichier (nom) — plus le score est haut, plus le fichier est préféré
_FILE_PRIORITY_PATTERNS: List[tuple] = [
    # (pattern_in_filename, bonus_score)
    ("manifest", 10),
    ("index", 9),
    ("registry", 8),
    ("canon", 7),
    ("spec", 6),
    ("schema", 5),
    ("evidence", 4),
    ("proof", 3),
    ("law", 3),
    ("protocol", 3),
    ("agent", 2),
    ("arbre", 2),
    ("tree", 2),
]


def _score_file(file_ref: str) -> int:
    """Calcule un score de priorité pour un fichier candidat selon son nom."""
    fname = file_ref.lower().replace("\\", "/").split("/")[-1]
    score = 0
    for pattern, bonus in _FILE_PRIORITY_PATTERNS:
        if pattern in fname:
            score += bonus
    # Pénalise les exécutables (ne devrait pas arriver, mais sécurité défensive)
    ext = "." + fname.rsplit(".", 1)[-1] if "." in fname else ""
    if ext in _FORBIDDEN_EXTENSIONS:
        score -= 100
    return score


def _is_allowed(file_ref: str) -> bool:
    """Vérifie qu'un fichier candidat n'est pas un exécutable."""
    fname = file_ref.lower().replace("\\", "/").split("/")[-1]
    if "." not in fname:
        return True
    ext = "." + fname.rsplit(".", 1)[-1]
    return ext not in _FORBIDDEN_EXTENSIONS


def _collect_file_candidates(selected_path: Dict[str, Any]) -> List[str]:
    """Collecte tous les fichiers candidats depuis un selected_path."""
    candidates: List[str] = []
    # evidence_packs → noms symboliques, pas de fichiers directs
    # selected_files
    for f in selected_path.get("selected_files", []):
        if isinstance(f, str) and f:
            candidates.append(f)
    # source_subfamilies comme hints
    for sub in selected_path.get("source_subfamilies", []):
        if isinstance(sub, str) and sub:
            candidates.append(sub)
    return candidates


def build_hydration_plan_from_path(
    selected_path: Dict[str, Any],
    max_files: int = 8,
    max_bytes: int = 50_000,
) -> Dict[str, Any]:
    """
    Construit un plan d'hydratation depuis un selected_path (P36).

    Sélectionne au maximum max_files fichiers preuves/manifests/specs/registry.
    Exclut tout fichier exécutable (.py, .ps1, .bat, .sh, .exe).
    Pas d'hydratation massive.

    Args:
        selected_path: Le chemin sélectionné par route_capability_path.
        max_files: Maximum de fichiers à hydrater (défaut 8).
        max_bytes: Budget total en octets (défaut 50 000).

    Returns:
        Dict décrivant le plan d'hydratation.
        Toujours readonly=True, no_act=True.
    """
    capability_chain = selected_path.get("capability_chain", [])
    source_families = selected_path.get("source_families", [])
    source_subfamilies = selected_path.get("source_subfamilies", [])
    evidence_packs = selected_path.get("evidence_packs", [])
    adapters = selected_path.get("adapters", [])
    modules = selected_path.get("modules", [])

    # Fichiers candidats depuis le chemin
    raw_candidates = _collect_file_candidates(selected_path)

    # Filtrer exécutables et dédupliquer
    allowed: List[str] = []
    seen: set = set()
    for f in raw_candidates:
        if f not in seen and _is_allowed(f):
            seen.add(f)
            allowed.append(f)

    # Trier par priorité
    allowed.sort(key=lambda f: _score_file(f), reverse=True)

    # Limiter au max_files
    selected = allowed[:max_files]

    # Estimation budget bytes (conservateur — sans lire les fichiers)
    estimated_bytes = min(max_bytes, len(selected) * 6_000)

    return {
        "capability_chain": capability_chain,
        "source_families": source_families,
        "source_subfamilies": source_subfamilies,
        "evidence_packs": evidence_packs,
        "selected_adapters": adapters,
        "selected_modules": modules,
        "planned_files": selected,
        "planned_files_count": len(selected),
        "max_files": max_files,
        "estimated_bytes": estimated_bytes,
        "max_bytes": max_bytes,
        "forbidden_extensions_excluded": list(_FORBIDDEN_EXTENSIONS),
        "readonly": True,
        "no_act": True,
        "no_zip_extraction": True,
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "status": "HYDRATION_PLAN_READY",
    }
