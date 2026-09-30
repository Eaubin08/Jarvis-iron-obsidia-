# runtime_wiring/source_runtime/route_capability_map.py
# P45 — Route Capability Map.
# Construit et retourne la couverture complète de toutes les routes API.
# KX108_ONLY. No ACT. No write. Readonly. Module-level cache.

from __future__ import annotations
from typing import Any, Dict, List, Optional

from runtime_wiring.source_runtime.route_coverage_classifier import classify_route_coverage

# ── Cache module-level ────────────────────────────────────────────────────────
_MAP_CACHE: Optional[Dict[str, Any]] = None


def build_route_capability_map(force_rebuild: bool = False) -> Dict[str, Any]:
    """
    Construit la carte de couverture de toutes les routes détectées par P37.

    Returns:
        Dict avec :
        - route_map: {path → classification_result}
        - coverage_counts: comptage par catégorie
        - coverage_percent: % de routes classifiées (non-UNCLASSIFIED)
        - unclassified_routes: liste des routes UNCLASSIFIED
        Toujours readonly=True, emits_act=False, decision_authority=KX108_ONLY.
    """
    global _MAP_CACHE
    if _MAP_CACHE is not None and not force_rebuild:
        return _MAP_CACHE

    from runtime_wiring.source_runtime.runtime_inventory_graph import build_runtime_inventory_graph

    graph = build_runtime_inventory_graph()
    routes = graph.get("routes", [])

    route_map: Dict[str, Any] = {}
    counts: Dict[str, int] = {
        "CONNECTED_READONLY": 0,
        "CONNECTED_BLOCKED_ACTION": 0,
        "STATUS_ONLY": 0,
        "WORKBENCH_ONLY": 0,
        "INTERNAL_ONLY": 0,
        "ARCHIVE_ONLY": 0,
        "DO_NOT_BIND_EXPLICIT": 0,
        "UNCLASSIFIED": 0,
    }
    unclassified: List[str] = []

    for route in routes:
        path = route.get("path", "")
        method = route.get("method", "GET")
        classification = classify_route_coverage(path, method)
        status = classification.get("coverage_status", "UNCLASSIFIED")

        route_map[path] = {
            **classification,
            "method": method,
            "function": route.get("function", ""),
            "module_path": route.get("module_path", ""),
        }

        if status in counts:
            counts[status] += 1
        else:
            counts["UNCLASSIFIED"] += 1
            unclassified.append(path)

    total = len(routes)
    classified = total - counts["UNCLASSIFIED"]
    coverage_pct = round(100.0 * classified / total, 1) if total > 0 else 0.0

    result = {
        "map_status": "READY",
        "total_routes": total,
        "route_map": route_map,
        "coverage_counts": counts,
        "coverage_percent": coverage_pct,
        "unclassified_routes": unclassified,
        "unclassified_count": len(unclassified),
        # Safety invariants
        "readonly": True,
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "source": "P45_ROUTE_CAPABILITY_MAP",
    }
    _MAP_CACHE = result
    return result


def get_route_classification(path: str) -> Dict[str, Any]:
    """
    Retourne la classification d'une route spécifique.
    Utilise le cache si disponible, sinon build fresh.
    """
    coverage = build_route_capability_map()
    route_map = coverage.get("route_map", {})
    if path in route_map:
        return route_map[path]
    # Route not in inventory — classify on-the-fly
    return classify_route_coverage(path)


def get_coverage_summary() -> Dict[str, Any]:
    """Retourne un résumé de la couverture sans le détail par route."""
    coverage = build_route_capability_map()
    return {
        "total_routes": coverage["total_routes"],
        "coverage_percent": coverage["coverage_percent"],
        "coverage_counts": coverage["coverage_counts"],
        "unclassified_count": coverage["unclassified_count"],
        "unclassified_routes": coverage["unclassified_routes"],
        "readonly": True,
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
    }


def clear_map_cache() -> None:
    """Vide le cache de la carte. Pour tests et refresh forcé."""
    global _MAP_CACHE
    _MAP_CACHE = None
