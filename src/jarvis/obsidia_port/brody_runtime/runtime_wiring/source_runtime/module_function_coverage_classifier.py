"""
P47 — Module & Function Coverage Classifier.
Classifie chaque module et chaque fonction Python dans une catégorie de couverture.
NO ACT. NO write. NO mutation. KX108_ONLY. READONLY.
"""
from __future__ import annotations

import pathlib
from typing import Any

VALID_MODULE_STATUSES = frozenset({
    "CONNECTED_RUNTIME",
    "CONNECTED_ROUTE_HANDLER",
    "CONNECTED_ADAPTER",
    "CONNECTED_CAPABILITY",
    "CONNECTED_STATUS_ONLY",
    "CONNECTED_TEST_ONLY",
    "CONNECTED_WORKBENCH_SUPPORT",
    "BLOCKED_ACTION_RUNTIME",
    "INTERNAL_HELPER",
    "ARCHIVE_ONLY",
    "DO_NOT_BIND_EXPLICIT",
})

_ACTION_MODULE_KEYWORDS = frozenset({
    "blockchain", "gencoin", "worldcall", "world_call", "memory_promotion_guard",
})
_ACTION_FN_KEYWORDS = frozenset({
    "blockchain", "gencoin", "worldcall", "world_call",
    "memory_write", "memory_promote", "wallet", "sign_tx", "mint",
})
_STATUS_MODULE_KEYWORDS = frozenset({
    "status", "x108", "os3", "freeze", "monitoring", "source_runtime_status",
    "freeze_metrics", "auth",
})
_ADAPTER_KEYWORDS = frozenset({
    "adapter", "bridge", "hydrat", "family_selector", "pack_resolver",
    "runtime_cache", "context_hydrat", "source_adapters",
})
_CAPABILITY_KEYWORDS = frozenset({
    "capability", "inventory_builder", "inventory_graph",
    "route_capability", "route_coverage",
})
_RUNTIME_MODULE_KEYWORDS = frozenset({
    "dry_run_packet", "source_runtime_query", "os_trad_reverse",
    "reverse_os", "audit_middleware", "orchestrator", "reconnect",
    "real_response_pipeline",
})
_ARCHIVE_KEYWORDS = frozenset({"demo", "p8b", "p9c"})


def classify_module(module_entry: dict[str, Any]) -> str:
    """
    Classifie un module à partir de son dictionnaire d'inventaire.
    Garantit qu'aucun module ne reste UNCLASSIFIED.
    """
    path: str = module_entry.get("module_path", "")
    risk_flags: list = module_entry.get("risk_flags", [])
    return _classify_by_path(path, risk_flags)


def _classify_by_path(path: str, risk_flags: list) -> str:
    p = path.lower().replace("\\", "/")
    stem = pathlib.Path(path).stem.lower()

    # Init files — internal
    if stem == "__init__":
        return "INTERNAL_HELPER"

    # Test modules
    if p.startswith("tests/") or "/tests/" in p or stem.startswith("test_"):
        return "CONNECTED_TEST_ONLY"

    # Route handlers
    if "/routes/" in p:
        if any(k in stem for k in _ACTION_MODULE_KEYWORDS):
            return "BLOCKED_ACTION_RUNTIME"
        if any(k in stem for k in _STATUS_MODULE_KEYWORDS):
            return "CONNECTED_STATUS_ONLY"
        return "CONNECTED_ROUTE_HANDLER"

    # Workbench support — BEFORE capability (workbench_view_capability_map matches both)
    if "workbench_view" in stem:
        return "CONNECTED_WORKBENCH_SUPPORT"

    # Capability router / inventory
    if any(k in stem for k in _CAPABILITY_KEYWORDS):
        return "CONNECTED_CAPABILITY"

    # Adapters
    if any(k in stem for k in _ADAPTER_KEYWORDS):
        return "CONNECTED_ADAPTER"
    if "registry" in stem or "adapter_target" in stem:
        return "CONNECTED_ADAPTER"

    # Blocked action
    if any(k in stem for k in _ACTION_MODULE_KEYWORDS):
        return "BLOCKED_ACTION_RUNTIME"

    # Archive / demo
    if any(k in stem for k in _ARCHIVE_KEYWORDS):
        return "ARCHIVE_ONLY"

    # Runtime core
    if any(k in stem for k in _RUNTIME_MODULE_KEYWORDS):
        return "CONNECTED_RUNTIME"

    # main FastAPI app
    if stem == "main":
        return "CONNECTED_ROUTE_HANDLER"

    # Status/metrics
    if any(k in stem for k in _STATUS_MODULE_KEYWORDS):
        return "CONNECTED_STATUS_ONLY"

    # Fallback — internal helper
    return "INTERNAL_HELPER"


def classify_function(function_entry: dict[str, Any]) -> str:
    """
    Classifie une fonction à partir de son dictionnaire d'inventaire.
    Hérite par défaut de la classification du module parent.
    """
    module_path: str = function_entry.get("module_path", "")
    fn_name: str = function_entry.get("function_name", "").lower()
    decorators: list = [d.lower() for d in function_entry.get("decorators", [])]
    risk_flags: list = function_entry.get("risk_flags", [])

    # Test functions
    if fn_name.startswith("test_"):
        return "CONNECTED_TEST_ONLY"

    # Route handlers (FastAPI decorator)
    if any("router." in d or "app." in d or "@get" in d or "@post" in d for d in decorators):
        return "CONNECTED_ROUTE_HANDLER"

    # Blocked action functions
    if any(k in fn_name for k in _ACTION_FN_KEYWORDS):
        return "BLOCKED_ACTION_RUNTIME"

    # Inherit module classification
    module_status = _classify_by_path(module_path, risk_flags)
    return module_status


def classify_all_modules(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Classifie tous les modules et retourne la liste enrichie."""
    return [{**m, "coverage_status": classify_module(m)} for m in modules]


def get_module_coverage_summary(modules: list[dict[str, Any]]) -> dict[str, Any]:
    """Résumé couverture P47 — modules + fonctions."""
    classified = classify_all_modules(modules)
    total_mods = len(classified)
    mod_counts: dict[str, int] = {}
    fn_counts: dict[str, int] = {}
    unclassified_mods = 0
    unclassified_fns = 0
    total_fns = 0

    for m in classified:
        status = m.get("coverage_status", "UNCLASSIFIED")
        fn_count = m.get("function_count", 0)
        total_fns += fn_count

        if status == "UNCLASSIFIED":
            unclassified_mods += 1
            unclassified_fns += fn_count
        mod_counts[status] = mod_counts.get(status, 0) + 1
        fn_counts[status] = fn_counts.get(status, 0) + fn_count

    covered_mods = total_mods - unclassified_mods
    covered_fns = total_fns - unclassified_fns
    mod_pct = (covered_mods / total_mods * 100.0) if total_mods > 0 else 0.0
    fn_pct = (covered_fns / total_fns * 100.0) if total_fns > 0 else 0.0

    return {
        "modules_total": total_mods,
        "modules_classified": covered_mods,
        "modules_unclassified_count": unclassified_mods,
        "module_coverage_percent": mod_pct,
        "functions_total": total_fns,
        "functions_classified": covered_fns,
        "functions_unclassified_count": unclassified_fns,
        "function_coverage_percent": fn_pct,
        "module_coverage_counts": mod_counts,
        "function_coverage_counts": fn_counts,
        "module_function_coverage_status": (
            "FULL_COVERAGE"
            if mod_pct >= 100.0 and fn_pct >= 100.0
            else "PARTIAL_COVERAGE"
        ),
    }
