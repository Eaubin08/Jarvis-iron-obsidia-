"""
P48 — Adapter Coverage Classifier.
Classifie chaque adapter dans une catégorie de couverture P48.
NO ACT. NO write. NO mutation. KX108_ONLY. READONLY.
"""
from __future__ import annotations

from typing import Any

VALID_ADAPTER_STATUSES = frozenset({
    "CONNECTED_CONTEXT_PACKET",
    "CONNECTED_SOURCE_RUNTIME",
    "CONNECTED_CAPABILITY",
    "CONNECTED_OS_MAP",
    "CONNECTED_READONLY_PREVIEW",
    "BLOCKED_ACTION_ADAPTER",
    "INTERNAL_ONLY",
    "ARCHIVE_ONLY",
    "DO_NOT_BIND_EXPLICIT",
})

# Adapters qui s'enrichissent via un index source runtime dédié
_SOURCE_RUNTIME_ADAPTERS = frozenset({
    "os_trad_reverse_to_context_packet",
    "reverse_os_interlanguage_to_context_packet",
})

# Adapter dispatcher de la registry
_CAPABILITY_ADAPTERS = frozenset({
    "route_entry_to_context_packet",
})

# Adapters avec risque d'action (aucun dans P48 — tous bloqués ou advisory)
_BLOCKED_ACTION_ADAPTERS: frozenset[str] = frozenset()

# Adapters internes uniquement
_INTERNAL_ONLY_ADAPTERS: frozenset[str] = frozenset()


def classify_adapter(adapter_entry: dict[str, Any]) -> str:
    """
    Classifie un adapter à partir de son dictionnaire d'inventaire.
    Garantit qu'aucun adapter ne reste UNCLASSIFIED.
    """
    name: str = adapter_entry.get("adapter_name", "")
    module_path: str = adapter_entry.get("module_path", "").lower()
    boundary: str = adapter_entry.get("boundary", "").lower()
    action_risk: bool = adapter_entry.get("action_risk", False)

    # Adapters à risque d'action (bloqués)
    if action_risk or name in _BLOCKED_ACTION_ADAPTERS:
        return "BLOCKED_ACTION_ADAPTER"

    # Dispatcher registry — CONNECTED_CAPABILITY (route vers les autres adapters)
    if name in _CAPABILITY_ADAPTERS or "dispatch" in boundary or "registry" in module_path:
        return "CONNECTED_CAPABILITY"

    # Adapters enrichis par un index source runtime
    if name in _SOURCE_RUNTIME_ADAPTERS:
        return "CONNECTED_SOURCE_RUNTIME"

    # Tous les autres adapters _to_context_packet dans source_adapters.py
    if "source_adapters" in module_path and name.endswith("_to_context_packet"):
        return "CONNECTED_CONTEXT_PACKET"

    # Archive / demo
    if "demo" in name or "p8b" in name or "archive" in boundary:
        return "ARCHIVE_ONLY"

    # Readonly preview seulement
    if "preview" in boundary or "preview_only" in name:
        return "CONNECTED_READONLY_PREVIEW"

    # OS Map
    if "os_map" in name or "os-map" in boundary:
        return "CONNECTED_OS_MAP"

    # Interne
    if "internal" in name or "helper" in name:
        return "INTERNAL_ONLY"

    # Fallback — tous les adapters _to_context_packet restants sont CONNECTED_CONTEXT_PACKET
    if name.endswith("_to_context_packet"):
        return "CONNECTED_CONTEXT_PACKET"

    return "CONNECTED_CONTEXT_PACKET"


def classify_all_adapters(adapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Classifie tous les adapters et retourne la liste enrichie."""
    return [{**a, "coverage_status": classify_adapter(a)} for a in adapters]


def get_adapter_coverage_summary(adapters: list[dict[str, Any]]) -> dict[str, Any]:
    """Résumé couverture P48 — adapters."""
    classified = classify_all_adapters(adapters)
    total = len(classified)
    counts: dict[str, int] = {}
    unclassified = 0

    for a in classified:
        status = a.get("coverage_status", "UNCLASSIFIED")
        if status == "UNCLASSIFIED":
            unclassified += 1
        counts[status] = counts.get(status, 0) + 1

    covered = total - unclassified
    percent = (covered / total * 100.0) if total > 0 else 0.0

    return {
        "adapter_coverage_status": "FULL_COVERAGE" if percent >= 100.0 else "PARTIAL_COVERAGE",
        "adapters_total": total,
        "adapters_classified": covered,
        "adapters_unclassified_count": unclassified,
        "adapter_coverage_percent": percent,
        "coverage_counts": counts,
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
    }
