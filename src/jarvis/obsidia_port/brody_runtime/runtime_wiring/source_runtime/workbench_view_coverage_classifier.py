"""
P46 — Workbench View Coverage Classifier.
Classifie chaque vue Workbench dans une catégorie de couverture.
NO ACT. NO write. NO mutation. KX108_ONLY. READONLY.
"""
from __future__ import annotations

from typing import Any

VALID_STATUSES = frozenset({
    "CONNECTED_TO_RUNTIME",
    "CONNECTED_TO_OS_MAP",
    "CONNECTED_TO_STATUS_ONLY",
    "CONNECTED_TO_WORKBENCH_ONLY",
    "BLOCKED_ACTION_VIEW",
    "INTERNAL_UI_ONLY",
    "ARCHIVE_ONLY",
    "DO_NOT_BIND_EXPLICIT",
})

_ACTION_KEYWORDS = {
    "blockchain", "gencoin", "wallet", "worldcall", "world_call",
    "mint", "trade", "deploy", "transaction", "egress", "sign",
    "action_gateway", "action_bus",
}

_STATUS_KEYWORDS = {"health", "status", "kernel", "x108", "readiness", "metrics"}

_OS_MAP_KEYWORDS = {"os_map", "osmap", "capability_path", "capability_router", "os-map"}

_RUNTIME_ENDPOINTS = {
    "/api/brody/chat",
    "/api/audit/events",
    "/api/memory/candidates",
    "/api/runtime-wiring/preview",
    "/api/runtime-wiring/source-runtime/preview",
    "/graph/v20/frozen/status",
    "/graph/v20/frozen/metrics",
    "/graph/v20/frozen/readiness",
    "/graph/v20/frozen/context",
}

_OS_MAP_ENDPOINTS = {"/api/runtime-wiring/os-map/query"}

_STATUS_ENDPOINTS = {"/health", "/api/health", "/api/kernel/status"}


def classify_workbench_view(view: dict[str, Any]) -> str:
    """
    Retourne le coverage_status d'une vue Workbench.
    Garantit qu'aucune vue ne reste UNCLASSIFIED.
    """
    file_lower = view.get("file", "").lower()
    endpoints = {e.lower() for e in view.get("backend_endpoints", [])}
    runtime_family = view.get("runtime_family", "").lower()
    status = view.get("status", "").lower()

    # 1. OS Map — priorité haute
    if (
        endpoints & {e.lower() for e in _OS_MAP_ENDPOINTS}
        or any(k in file_lower for k in _OS_MAP_KEYWORDS)
        or any(k in runtime_family for k in _OS_MAP_KEYWORDS)
    ):
        return "CONNECTED_TO_OS_MAP"

    # 2. Blocked action views
    is_action = any(k in file_lower for k in _ACTION_KEYWORDS) or any(
        k in runtime_family for k in _ACTION_KEYWORDS
    )
    has_no_real_endpoints = not endpoints
    if is_action and (has_no_real_endpoints or status in {"mock_only"}):
        return "BLOCKED_ACTION_VIEW"

    # 3. Status-only views
    if (
        endpoints & {e.lower() for e in _STATUS_ENDPOINTS}
        or any(k in file_lower for k in _STATUS_KEYWORDS)
        or any(k in runtime_family for k in _STATUS_KEYWORDS)
    ):
        return "CONNECTED_TO_STATUS_ONLY"

    # 4. Connected to runtime (real endpoints)
    if endpoints & {e.lower() for e in _RUNTIME_ENDPOINTS}:
        return "CONNECTED_TO_RUNTIME"

    # 5. Internal UI only (mock/internal, no endpoints, no action)
    if status in {"internal_mock", "internal_config"} or "proof" in runtime_family:
        return "INTERNAL_UI_ONLY"

    # 6. Workbench-only (local lib, config, no backend)
    if status in {"local_lib", "internal_config"} or not endpoints:
        return "CONNECTED_TO_WORKBENCH_ONLY"

    # 7. Do not bind explicit
    if "do_not_bind" in file_lower or "archive" in file_lower:
        return "DO_NOT_BIND_EXPLICIT"

    # 8. Archive only
    if "archive" in runtime_family:
        return "ARCHIVE_ONLY"

    # Fallback — should never reach production
    return "CONNECTED_TO_WORKBENCH_ONLY"


def classify_all_views(views: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Classifie toutes les vues et retourne la liste enrichie."""
    result = []
    for view in views:
        coverage_status = classify_workbench_view(view)
        result.append({**view, "coverage_status": coverage_status})
    return result


def get_coverage_summary(views: list[dict[str, Any]]) -> dict[str, Any]:
    """Retourne le résumé de couverture P46."""
    classified = classify_all_views(views)
    total = len(classified)
    counts: dict[str, int] = {s: 0 for s in VALID_STATUSES}
    unclassified = 0

    for v in classified:
        s = v.get("coverage_status", "UNCLASSIFIED")
        if s in counts:
            counts[s] += 1
        else:
            unclassified += 1

    covered = total - unclassified
    percent = (covered / total * 100.0) if total > 0 else 0.0

    return {
        "total_views": total,
        "coverage_percent": percent,
        "unclassified_views_count": unclassified,
        "coverage_counts": counts,
        "workbench_views_coverage_percent": percent,
        "workbench_views_total": total,
        "workbench_views_classified": covered,
    }
