# runtime_wiring/source_runtime/capability_inventory_linker.py
# P37 — Linker : relie les capability paths P36 à l'inventaire réel du repo.
# Enrichit selected_path avec: selected_functions, selected_classes, selected_routes,
#   selected_tests, selected_docs, inventory_linked, coverage_status.
# KX108_ONLY. No ACT. No write. Readonly.
from __future__ import annotations

from typing import Any, Dict, List, Optional

from runtime_wiring.source_runtime.capability_taxonomy import CAPABILITY_TAXONOMY

# ── Mapping capability → modules principaux (stems) ──────────────────────────
# Ces stems permettent de retrouver fonctions/tests dans l'inventaire.

_CAPABILITY_MODULE_STEMS: Dict[str, List[str]] = {
    "IR_ALPHABET_MAPPING": [
        "reverse_os_interlanguage_index",
        "capability_path_router",
        "source_runtime_query",
    ],
    "REVERSE_OS_INTERLANGUAGE": [
        "reverse_os_interlanguage_index",
        "brody_source_context_bridge",
        "source_context_hydrator",
    ],
    "OS_TRAD_TRANSLATION": [
        "os_trad_reverse_index",
        "source_runtime_query",
        "brody_source_context_bridge",
    ],
    "AGENT_TREE_LOOKUP": [
        "os_trad_reverse_index",
        "source_runtime_query",
    ],
    "LAW_PROTOCOL_LOOKUP": [
        "os_trad_reverse_index",
        "source_runtime_query",
    ],
    "RSSI_SECURITY_CONTEXT": [
        "source_adapters",
        "brody_source_context_bridge",
    ],
    "PROOF_AUDIT_CONTEXT": [
        "source_adapters",
        "brody_source_context_bridge",
    ],
    "MEMORY_REINTEGRATION_CONTEXT": [
        "source_adapters",
        "brody_source_context_bridge",
    ],
    "GRAPHITI_READONLY_CONTEXT": [
        "source_adapters",
        "brody_source_context_bridge",
        "graphiti_v20_readonly_client",  # P44: wired
    ],
    "NPL_NARRATIVE_PROVENANCE": [
        "source_adapters",
        "brody_source_context_bridge",
    ],
    "PROVENANCE_TRACE": [
        "brody_source_context_bridge",
        "source_runtime_query",
    ],
    "SOURCE_CONTEXT": [
        "source_runtime_query",
        "brody_source_context_bridge",
        "source_context_hydrator",
    ],
    "ACTION_REQUEST_BLOCKED": [],
    "WORKBENCH_PREVIEW": [
        "source_runtime_status",
    ],
    "OS4_ENGINE_STATUS": [
        "source_runtime_cache",
    ],
    "ANSWER_ONLY": [],
    # P44
    "ATLAS_CONTEXT_LOOKUP": [
        "source_runtime_query",
        "brody_source_context_bridge",
    ],
    "EXTERNAL_SIGNALS_CONTEXT": [
        "source_runtime_query",
        "brody_source_context_bridge",
    ],
    "BRODY_CHAT_ENTRYPOINT": [
        "routes/brody",
        "brody_real_response_pipeline",
        "brody_source_context_bridge",
    ],
    "OS_TRAD_ROUTE_CONTEXT": [
        "os_trad_ir_reverse",
        "os_trad_reverse_index",
        "source_runtime_query",
    ],
}

# ── Mapping capability → route fragments ─────────────────────────────────────

_CAPABILITY_ROUTE_FRAGMENTS: Dict[str, List[str]] = {
    "IR_ALPHABET_MAPPING": ["source-runtime/preview"],
    "REVERSE_OS_INTERLANGUAGE": ["source-runtime/preview"],
    "OS_TRAD_TRANSLATION": ["source-runtime/preview"],
    "AGENT_TREE_LOOKUP": ["source-runtime/preview"],
    "LAW_PROTOCOL_LOOKUP": ["source-runtime/preview"],
    "RSSI_SECURITY_CONTEXT": ["source-runtime/preview"],
    "PROOF_AUDIT_CONTEXT": ["source-runtime/preview"],
    "MEMORY_REINTEGRATION_CONTEXT": ["source-runtime/preview"],
    "GRAPHITI_READONLY_CONTEXT": ["source-runtime/preview", "graphiti"],  # P44: graphiti routes
    "NPL_NARRATIVE_PROVENANCE": ["source-runtime/preview"],
    "PROVENANCE_TRACE": ["source-runtime/preview"],
    "SOURCE_CONTEXT": ["source-runtime/preview"],
    "OS4_ENGINE_STATUS": ["source-runtime/status"],
    "WORKBENCH_PREVIEW": ["source-runtime/preview"],
    "ACTION_REQUEST_BLOCKED": [],
    "ANSWER_ONLY": [],
    # P44
    "ATLAS_CONTEXT_LOOKUP": ["source-runtime/preview"],
    "EXTERNAL_SIGNALS_CONTEXT": ["source-runtime/preview"],
    "BRODY_CHAT_ENTRYPOINT": ["brody/chat"],
    "OS_TRAD_ROUTE_CONTEXT": ["os-trad/api"],
}

# ── Mapping capability → test stems ──────────────────────────────────────────

_CAPABILITY_TEST_STEMS: Dict[str, List[str]] = {
    "IR_ALPHABET_MAPPING": [
        "test_capability_path_router_p36",
        "test_capability_path_preview_p36",
        "test_reverse_os_interlanguage_runtime_extension_p35",
        "test_reverse_os_interlanguage_preview_p35",
    ],
    "REVERSE_OS_INTERLANGUAGE": [
        "test_reverse_os_interlanguage_runtime_extension_p35",
        "test_reverse_os_interlanguage_preview_p35",
        "test_capability_path_router_p36",
    ],
    "AGENT_TREE_LOOKUP": [
        "test_capability_path_router_p36",
    ],
    "LAW_PROTOCOL_LOOKUP": [
        "test_capability_path_router_p36",
    ],
    "ACTION_REQUEST_BLOCKED": [
        "test_capability_path_router_p36",
        "test_capability_path_preview_p36",
    ],
    "SOURCE_CONTEXT": [
        "test_source_runtime_status_p29",
        "test_brody_source_pack_context_p26",
    ],
    "OS4_ENGINE_STATUS": [
        "test_source_runtime_status_p29",
    ],
    # P44
    "ATLAS_CONTEXT_LOOKUP": [
        "test_source_runtime_family_discovery_ci_p42b",
        "test_critical_capability_binding_p44",
    ],
    "EXTERNAL_SIGNALS_CONTEXT": [
        "test_source_runtime_family_discovery_ci_p42b",
        "test_critical_capability_binding_p44",
    ],
    "BRODY_CHAT_ENTRYPOINT": [
        "test_critical_capability_binding_p44",
    ],
    "OS_TRAD_ROUTE_CONTEXT": [
        "test_reverse_os_interlanguage_runtime_extension_p35",
        "test_critical_capability_binding_p44",
    ],
    "GRAPHITI_READONLY_CONTEXT": [
        "test_critical_capability_binding_p44",
    ],
}

# ── Mapping capability → doc stems ───────────────────────────────────────────

_CAPABILITY_DOC_STEMS: Dict[str, List[str]] = {
    "IR_ALPHABET_MAPPING": [
        "P35_REVERSE_OS_INTERLANGUAGE_RUNTIME_EXTENSION_REPORT",
        "P36_GLOBAL_CAPABILITY_PATH_ROUTER_REPORT",
    ],
    "REVERSE_OS_INTERLANGUAGE": [
        "P34_REVERSE_OS_INTERLANGUAGE_CANONIZATION_REPORT",
        "P35_REVERSE_OS_INTERLANGUAGE_RUNTIME_EXTENSION_REPORT",
    ],
    "SOURCE_CONTEXT": [
        "P26_SOURCE_PACK_RUNTIME_BRIDGE_REPORT",
        "P29_WORKBENCH_SOURCE_RUNTIME_SURFACE_REPORT",
    ],
    "OS4_ENGINE_STATUS": [
        "P28_SOURCE_RUNTIME_CACHE_SELECTOR_REPORT",
        "P29_WORKBENCH_SOURCE_RUNTIME_SURFACE_REPORT",
    ],
    # P44
    "ATLAS_CONTEXT_LOOKUP": [
        "P43_UNCONNECTED_RUNTIME_SURFACE_AUDIT_REPORT",
        "P44_CRITICAL_CAPABILITY_BINDING_REPORT",
    ],
    "EXTERNAL_SIGNALS_CONTEXT": [
        "P43_UNCONNECTED_RUNTIME_SURFACE_AUDIT_REPORT",
        "P44_CRITICAL_CAPABILITY_BINDING_REPORT",
    ],
    "BRODY_CHAT_ENTRYPOINT": [
        "P43_UNCONNECTED_RUNTIME_SURFACE_AUDIT_REPORT",
        "P44_CRITICAL_CAPABILITY_BINDING_REPORT",
    ],
    "OS_TRAD_ROUTE_CONTEXT": [
        "P35_REVERSE_OS_INTERLANGUAGE_RUNTIME_EXTENSION_REPORT",
        "P43_UNCONNECTED_RUNTIME_SURFACE_AUDIT_REPORT",
        "P44_CRITICAL_CAPABILITY_BINDING_REPORT",
    ],
}


# ── Helpers de lookup dans l'inventaire ──────────────────────────────────────

def _find_functions(
    inventory: Dict[str, Any],
    module_stems: List[str],
    adapter_names: List[str],
) -> List[str]:
    """Trouve les fonctions matchant les stems de module ou les noms d'adapter."""
    found: List[str] = []
    seen: set = set()
    # Par stem de module
    for fn in inventory.get("functions", []):
        mp = fn.get("module_path", "")
        for stem in module_stems:
            if stem in mp and fn["name"] not in seen:
                found.append(fn["name"])
                seen.add(fn["name"])
                break
    # Par nom d'adapter exact
    for adapter_name in adapter_names:
        if adapter_name not in seen:
            # Cherche si la fonction existe dans l'inventaire
            for fn in inventory.get("functions", []):
                if fn["name"] == adapter_name and adapter_name not in seen:
                    found.append(adapter_name)
                    seen.add(adapter_name)
    return found[:20]


def _find_classes(
    inventory: Dict[str, Any],
    module_stems: List[str],
) -> List[str]:
    """Trouve les classes matchant les stems de module."""
    found: List[str] = []
    seen: set = set()
    for cls in inventory.get("classes", []):
        mp = cls.get("module_path", "")
        for stem in module_stems:
            if stem in mp and cls["name"] not in seen:
                found.append(cls["name"])
                seen.add(cls["name"])
                break
    return found[:10]


def _find_routes(
    inventory: Dict[str, Any],
    route_fragments: List[str],
) -> List[str]:
    """Trouve les routes dont le path contient l'un des fragments."""
    found: List[str] = []
    seen: set = set()
    for route in inventory.get("routes", []):
        path = route.get("path", "")
        for frag in route_fragments:
            if frag in path and path not in seen:
                found.append(path)
                seen.add(path)
                break
    return found


def _find_tests(
    inventory: Dict[str, Any],
    test_stems: List[str],
    module_stems: List[str],
) -> List[str]:
    """Trouve les fichiers test par stems ou par module hint."""
    found: List[str] = []
    seen: set = set()
    for test in inventory.get("tests", []):
        stem = test.get("stem", "")
        hint = test.get("covered_module_hint", "")
        test_path = test.get("test_path", "")
        # Match par stem direct
        for ts in test_stems:
            if ts in stem and test_path not in seen:
                found.append(test_path)
                seen.add(test_path)
                break
        # Match par module hint
        for ms in module_stems:
            if ms in hint and test_path not in seen:
                found.append(test_path)
                seen.add(test_path)
                break
    return found[:10]


def _find_docs(
    inventory: Dict[str, Any],
    doc_stems: List[str],
) -> List[str]:
    """Trouve les docs par stem de fichier."""
    found: List[str] = []
    seen: set = set()
    for doc in inventory.get("docs", []):
        stem = doc.get("stem", "")
        doc_path = doc.get("doc_path", "")
        for ds in doc_stems:
            if ds in stem and doc_path not in seen:
                found.append(doc_path)
                seen.add(doc_path)
                break
    return found[:5]


def _assess_coverage(
    functions: List[str],
    routes: List[str],
    tests: List[str],
) -> str:
    """Évalue le statut de couverture d'une capability."""
    if not functions and not routes:
        return "NO_IMPLEMENTATION_FOUND"
    if not tests:
        return "IMPLEMENTATION_FOUND_NO_TESTS"
    if functions and routes and tests:
        return "FULLY_COVERED"
    return "PARTIALLY_COVERED"


# ── Enrichissement d'un chemin ────────────────────────────────────────────────

def _enrich_path(
    path: Dict[str, Any],
    inventory: Dict[str, Any],
) -> Dict[str, Any]:
    """Enrichit un selected_path avec les données d'inventaire."""
    cap_chain = path.get("capability_chain", [])
    adapter_names = path.get("adapters", [])

    # Collecte les stems de modules pertinents
    module_stems: List[str] = []
    route_fragments: List[str] = []
    test_stems: List[str] = []
    doc_stems: List[str] = []

    for cap_id in cap_chain:
        module_stems.extend(_CAPABILITY_MODULE_STEMS.get(cap_id, []))
        route_fragments.extend(_CAPABILITY_ROUTE_FRAGMENTS.get(cap_id, []))
        test_stems.extend(_CAPABILITY_TEST_STEMS.get(cap_id, []))
        doc_stems.extend(_CAPABILITY_DOC_STEMS.get(cap_id, []))

    # Déduplique
    module_stems = list(dict.fromkeys(module_stems))
    route_fragments = list(dict.fromkeys(route_fragments))
    test_stems = list(dict.fromkeys(test_stems))
    doc_stems = list(dict.fromkeys(doc_stems))

    selected_functions = _find_functions(inventory, module_stems, adapter_names)
    selected_classes = _find_classes(inventory, module_stems)
    selected_routes = _find_routes(inventory, route_fragments)
    selected_tests = _find_tests(inventory, test_stems, module_stems)
    selected_docs = _find_docs(inventory, doc_stems)
    coverage_status = _assess_coverage(selected_functions, selected_routes, selected_tests)

    enriched = dict(path)
    enriched.update({
        "selected_functions": selected_functions,
        "selected_classes": selected_classes,
        "selected_routes": selected_routes,
        "selected_tests": selected_tests,
        "selected_docs": selected_docs,
        "inventory_linked": True,
        "coverage_status": coverage_status,
    })
    return enriched


# ── Fonction principale ────────────────────────────────────────────────────────

def link_capabilities_to_inventory(
    routing_result: Dict[str, Any],
    inventory_graph: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Enrichit un résultat P36 route_capability_path() avec l'inventaire réel.

    Args:
        routing_result: Dict retourné par route_capability_path().
        inventory_graph: Dict retourné par build_runtime_inventory_graph().

    Returns:
        Dict enrichi avec selected_functions, selected_classes, selected_routes,
        selected_tests, selected_docs, inventory_linked, coverage_status dans
        selected_path et ranked_runtime_paths.
        Toujours readonly=True, no_act=True.
    """
    if not inventory_graph or inventory_graph.get("inventory_status") != "READY":
        return {
            **routing_result,
            "inventory_linked": False,
            "inventory_status": "UNAVAILABLE",
        }

    # Enrichit le selected_path
    selected_path = routing_result.get("selected_path", {})
    enriched_selected = _enrich_path(selected_path, inventory_graph)

    # Enrichit les ranked_runtime_paths
    enriched_ranked = [
        _enrich_path(p, inventory_graph)
        for p in routing_result.get("ranked_runtime_paths", [])
    ]

    result = dict(routing_result)
    result["selected_path"] = enriched_selected
    result["ranked_runtime_paths"] = enriched_ranked
    result["inventory_linked"] = True
    result["inventory_status"] = "READY"
    # Expose les champs principaux au niveau racine pour l'API
    result["selected_functions"] = enriched_selected.get("selected_functions", [])
    result["selected_classes"] = enriched_selected.get("selected_classes", [])
    result["selected_routes"] = enriched_selected.get("selected_routes", [])
    result["selected_tests"] = enriched_selected.get("selected_tests", [])
    result["selected_docs"] = enriched_selected.get("selected_docs", [])
    result["coverage_status"] = enriched_selected.get("coverage_status", "UNKNOWN")

    return result
