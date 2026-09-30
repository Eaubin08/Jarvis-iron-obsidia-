# runtime_wiring/source_runtime/runtime_inventory_graph.py
# P37 — Inventory Graph : inventaire + arêtes de relation entre modules/fonctions/routes/tests.
# Appelle runtime_inventory_builder pour la découverte statique AST.
# KX108_ONLY. No ACT. No write. Readonly. Module-level cache.
from __future__ import annotations

from typing import Any, Dict, List, Optional

from runtime_wiring.source_runtime.runtime_inventory_builder import build_static_inventory

# ── Cache module-level ────────────────────────────────────────────────────────
_GRAPH_CACHE: Optional[Dict[str, Any]] = None


# ── Relations statiques connues (P26–P36) ─────────────────────────────────────
# Ces arêtes capturent les liaisons architecturales que l'AST seul ne peut pas déduire.

_STATIC_EDGES: List[Dict[str, str]] = [
    # Capability → Module
    {"from": "capability:IR_ALPHABET_MAPPING", "to": "module:runtime_wiring/source_runtime/reverse_os_interlanguage_index.py", "type": "USES"},
    {"from": "capability:REVERSE_OS_INTERLANGUAGE", "to": "module:runtime_wiring/source_runtime/reverse_os_interlanguage_index.py", "type": "USES"},
    {"from": "capability:AGENT_TREE_LOOKUP", "to": "module:runtime_wiring/source_runtime/os_trad_reverse_index.py", "type": "USES"},
    {"from": "capability:LAW_PROTOCOL_LOOKUP", "to": "module:runtime_wiring/source_runtime/os_trad_reverse_index.py", "type": "USES"},
    {"from": "capability:OS_TRAD_TRANSLATION", "to": "module:runtime_wiring/source_runtime/os_trad_reverse_index.py", "type": "USES"},
    {"from": "capability:RSSI_SECURITY_CONTEXT", "to": "module:runtime_wiring/source_adapters.py", "type": "USES"},
    {"from": "capability:MEMORY_REINTEGRATION_CONTEXT", "to": "module:runtime_wiring/source_runtime/brody_source_context_bridge.py", "type": "USES"},
    {"from": "capability:GRAPHITI_READONLY_CONTEXT", "to": "module:runtime_wiring/source_runtime/brody_source_context_bridge.py", "type": "USES"},
    # Capability → Function
    {"from": "capability:IR_ALPHABET_MAPPING", "to": "function:classify_entry_layer", "type": "USES"},
    {"from": "capability:REVERSE_OS_INTERLANGUAGE", "to": "function:build_reverse_os_interlanguage_index", "type": "USES"},
    {"from": "capability:AGENT_TREE_LOOKUP", "to": "function:build_os_trad_deep_concept_index", "type": "USES"},
    {"from": "capability:ACTION_REQUEST_BLOCKED", "to": "function:route_capability_path", "type": "GUARDS"},
    # Adapter → Source pack
    {"from": "adapter:reverse_os_interlanguage_to_context_packet", "to": "source_pack:REVERSE_OS_INTERLANGUAGE_CANON_V1", "type": "READS"},
    {"from": "adapter:os_trad_reverse_to_context_packet", "to": "source_pack:OS_TRAD_REVERSE_OS", "type": "READS"},
    {"from": "adapter:cognitive_to_context_packet", "to": "source_pack:COGNITIVE_REINTEGRATION", "type": "READS"},
    {"from": "adapter:npl_to_context_packet", "to": "source_pack:NARRATIVE_PROVENANCE_LAYER", "type": "READS"},
    {"from": "adapter:rssi_security_to_context_packet", "to": "source_pack:RSSI_SECURITY_PRESENTATION", "type": "READS"},
    {"from": "adapter:rssi_rgpd_to_context_packet", "to": "source_pack:RSSI_RGPD", "type": "READS"},
    {"from": "adapter:compliance_to_context_packet", "to": "source_pack:COMPLIANCE_DATA_GOVERNANCE", "type": "READS"},
    {"from": "adapter:atlas_to_context_packet", "to": "source_pack:ATLAS", "type": "READS"},
    {"from": "adapter:external_signals_to_context_packet", "to": "source_pack:EXTERNAL_SIGNALS", "type": "READS"},
    # Route → Function
    {"from": "route:/api/runtime-wiring/source-runtime/preview", "to": "function:source_runtime_preview", "type": "EXPOSES"},
    {"from": "route:/api/runtime-wiring/source-runtime/status", "to": "function:source_runtime_status", "type": "EXPOSES"},
    {"from": "route:/api/runtime-wiring/source-runtime/preview", "to": "function:build_brody_context_from_source_packs", "type": "CALLS"},
    {"from": "route:/api/runtime-wiring/source-runtime/preview", "to": "function:route_capability_path", "type": "CALLS"},
    # Module → Module (P36 imports)
    {"from": "module:runtime_wiring/source_runtime/brody_source_context_bridge.py", "to": "module:runtime_wiring/source_runtime/capability_path_router.py", "type": "IMPORTS"},
    {"from": "module:runtime_wiring/source_runtime/brody_source_context_bridge.py", "to": "module:runtime_wiring/source_runtime/source_hydration_planner.py", "type": "IMPORTS"},
    {"from": "module:apps/obsidia_api/routes/source_runtime_status.py", "to": "module:runtime_wiring/source_runtime/capability_path_router.py", "type": "IMPORTS"},
    # Tests → Modules
    {"from": "test:tests/test_capability_path_router_p36.py", "to": "module:runtime_wiring/source_runtime/capability_path_router.py", "type": "TESTS"},
    {"from": "test:tests/api/test_capability_path_preview_p36.py", "to": "module:apps/obsidia_api/routes/source_runtime_status.py", "type": "TESTS"},
    {"from": "test:tests/test_runtime_inventory_graph_p37.py", "to": "module:runtime_wiring/source_runtime/runtime_inventory_graph.py", "type": "TESTS"},
    {"from": "test:tests/api/test_runtime_inventory_preview_p37.py", "to": "module:apps/obsidia_api/routes/source_runtime_status.py", "type": "TESTS"},
    # Docs → Modules
    {"from": "doc:docs/real_engine/P36_GLOBAL_CAPABILITY_PATH_ROUTER_REPORT.md", "to": "module:runtime_wiring/source_runtime/capability_path_router.py", "type": "DOCUMENTS"},
    {"from": "doc:docs/real_engine/P37_RUNTIME_FUNCTION_INVENTORY_GRAPH_REPORT.md", "to": "module:runtime_wiring/source_runtime/runtime_inventory_graph.py", "type": "DOCUMENTS"},
]


def _build_graph() -> Dict[str, Any]:
    """Construit le graphe d'inventaire complet."""
    inventory = build_static_inventory()

    # Enrichit les arêtes avec les données dynamiques découvertes par l'AST
    dynamic_edges: List[Dict[str, str]] = []

    # Route → Capability (depuis les routes découvertes)
    for route in inventory["routes"]:
        path = route.get("path", "")
        if "source-runtime/preview" in path:
            dynamic_edges.append({
                "from": f"route:{path}",
                "to": "capability:SOURCE_CONTEXT",
                "type": "EXPOSES",
            })

    # Adapter → Module (depuis les adapters découverts)
    for adapter in inventory["adapters"]:
        dynamic_edges.append({
            "from": f"adapter:{adapter['adapter_name']}",
            "to": f"module:{adapter['module_path']}",
            "type": "DEFINED_IN",
        })

    # Test → Module (depuis les hints de test)
    for test in inventory["tests"]:
        hint = test.get("covered_module_hint", "")
        if hint:
            dynamic_edges.append({
                "from": f"test:{test['test_path']}",
                "to": f"module:{hint}",
                "type": "TESTS",
            })

    all_edges = _STATIC_EDGES + dynamic_edges

    summary = {
        "module_count": inventory["module_count"],
        "function_count": inventory["function_count"],
        "class_count": inventory["class_count"],
        "route_count": inventory["route_count"],
        "adapter_count": inventory["adapter_count"],
        "test_file_count": inventory["test_file_count"],
        "doc_file_count": inventory["doc_file_count"],
        "static_edge_count": len(_STATIC_EDGES),
        "dynamic_edge_count": len(dynamic_edges),
        "total_edge_count": len(all_edges),
    }

    return {
        "inventory_status": "READY",
        "modules": inventory["modules"],
        "functions": inventory["functions"],
        "classes": inventory["classes"],
        "routes": inventory["routes"],
        "adapters": inventory["adapters"],
        "tests": inventory["tests"],
        "docs": inventory["docs"],
        "edges": all_edges,
        "summary": summary,
        # Counts also at top level for convenient access
        "module_count": inventory["module_count"],
        "function_count": inventory["function_count"],
        "class_count": inventory["class_count"],
        "route_count": inventory["route_count"],
        "adapter_count": inventory["adapter_count"],
        "test_file_count": inventory["test_file_count"],
        "doc_file_count": inventory["doc_file_count"],
        "readonly": True,
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
    }


def build_runtime_inventory_graph(force_rebuild: bool = False) -> Dict[str, Any]:
    """
    Retourne le graphe d'inventaire runtime (avec cache module-level).

    Args:
        force_rebuild: Si True, recompute même si le cache est chaud.

    Returns:
        Dict avec modules, functions, classes, routes, adapters, tests, docs, edges.
        Toujours readonly=True, runtime_allowed_now=False, emits_act=False.
    """
    global _GRAPH_CACHE
    if _GRAPH_CACHE is not None and not force_rebuild:
        return _GRAPH_CACHE
    _GRAPH_CACHE = _build_graph()
    return _GRAPH_CACHE


def get_functions_for_module(inventory_graph: Dict[str, Any], module_stem: str) -> List[str]:
    """Retourne les noms de fonctions d'un module par son stem (nom sans .py)."""
    result = []
    for fn in inventory_graph.get("functions", []):
        mp = fn.get("module_path", "")
        if module_stem in mp:
            result.append(fn["name"])
    return result


def get_routes_by_path_fragment(inventory_graph: Dict[str, Any], fragment: str) -> List[str]:
    """Retourne les routes dont le path contient le fragment."""
    return [
        r["path"]
        for r in inventory_graph.get("routes", [])
        if fragment in r.get("path", "")
    ]


def get_tests_for_module(inventory_graph: Dict[str, Any], module_stem: str) -> List[str]:
    """Retourne les fichiers test couvrant un module par son stem."""
    result = []
    for test in inventory_graph.get("tests", []):
        hint = test.get("covered_module_hint", "")
        if module_stem in hint or module_stem in test.get("stem", ""):
            result.append(test["test_path"])
    return result
