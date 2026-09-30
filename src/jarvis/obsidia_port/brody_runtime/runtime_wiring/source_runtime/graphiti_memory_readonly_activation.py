"""
P52 — Graphiti / Memory Readonly Controlled Activation.

Activates real Graphiti V20 readonly client and memory module at LEVEL_1 only.
Real components confirmed: graphiti_v20_readonly_client (8011 live),
memory REAL_MODULE (build_memory_candidate_v2, evaluate_promotion_policy).

NO write. NO ACT. NO Graphiti write. NO memory write. NO kernel mutation.
KX108_ONLY. READONLY. runtime_allowed_now=False.
"""
from __future__ import annotations

_REAL_COMPONENT_PATHS = [
    "apps/obsidia_api/graphiti_v20_readonly_client.py",
    "apps/obsidia_api/routes/graphiti.py",
    "apps/obsidia_api/routes/memory.py",
    "apps/obsidia_api/brody_project_memory_adapter.py",
    "apps/obsidia_api/brody_session_memory_adapter.py",
]

_BOUNDARY = {
    "readonly": True,
    "emits_act": False,
    "memory_write": False,
    "graphiti_write": False,
    "neo4j_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "world_action": False,
    "decision_authority": "KX108_ONLY",
    "runtime_allowed_now": False,
}


def _probe_graphiti_readonly() -> dict:
    """Probe the real Graphiti V20 readonly client — never writes."""
    try:
        from apps.obsidia_api.graphiti_v20_readonly_client import (
            graphiti_v20_get,
            graphiti_v20_available,
        )
        payload = graphiti_v20_get("/graph/v20/frozen/status", timeout=2.0)
        if graphiti_v20_available(payload):
            return {
                "graphiti_read_enabled": True,
                "graphiti_live": True,
                "graphiti_nodes": payload.get("nodes", 0),
                "graphiti_rels": payload.get("rels", 0),
                "graphiti_mode": payload.get("mode", "FROZEN_READONLY"),
                "graphiti_source": "GRAPHITI_V20_HTTP",
                "graphiti_write": False,
                "neo4j_write": False,
            }
        return {
            "graphiti_read_enabled": False,
            "graphiti_live": False,
            "graphiti_source": "GRAPHITI_V20_HTTP_UNAVAILABLE",
            "graphiti_write": False,
        }
    except Exception as exc:
        return {
            "graphiti_read_enabled": False,
            "graphiti_live": False,
            "graphiti_source": "IMPORT_ERROR",
            "graphiti_error": type(exc).__name__,
            "graphiti_write": False,
        }


def _probe_memory_readonly() -> dict:
    """Probe the real memory module — never writes."""
    try:
        from apps.obsidia_api.runtime_loader import load_runtime_components
        rt = load_runtime_components()
        mem = rt.get("memory", {})
        is_real = mem.get("status") == "REAL_MODULE"
        has_candidate = callable(mem.get("build_memory_candidate_v2"))
        has_policy = callable(mem.get("evaluate_promotion_policy"))
        return {
            "memory_read_enabled": is_real,
            "memory_real_module": is_real,
            "memory_has_candidate_builder": has_candidate,
            "memory_has_promotion_policy": has_policy,
            "memory_write": False,
            "memory_auto_promotion": False,
            "memory_source": "REAL_MODULE" if is_real else "BACKEND_STUB",
        }
    except Exception as exc:
        return {
            "memory_read_enabled": False,
            "memory_real_module": False,
            "memory_write": False,
            "memory_source": "IMPORT_ERROR",
            "memory_error": type(exc).__name__,
        }


def _get_graphiti_context_for_query(query: str) -> dict:
    """Fetch context from Graphiti V20 frozen graph for a given query. Readonly."""
    try:
        from apps.obsidia_api.graphiti_v20_readonly_client import (
            graphiti_v20_get,
            graphiti_v20_available,
        )
        payload = graphiti_v20_get(
            "/graph/v20/frozen/context",
            {"q": query[:100], "limit": 5},
            timeout=2.0,
        )
        if graphiti_v20_available(payload):
            return {
                "graphiti_context_status": "CONTEXT_RETRIEVED",
                "graphiti_context_query": query[:100],
                "graphiti_kernel_decision": payload.get("kernel_decision", ""),
                "graphiti_graphiti_decision": payload.get("graphiti_decision", ""),
                "graphiti_graphiti_role": payload.get("graphiti_role", ""),
                "graphiti_write": False,
            }
        return {"graphiti_context_status": "GRAPHITI_UNAVAILABLE", "graphiti_write": False}
    except Exception:
        return {"graphiti_context_status": "GRAPHITI_PROBE_ERROR", "graphiti_write": False}


def build_graphiti_memory_readonly_activation_state(query: str = "") -> dict:
    """
    Return the P52 Graphiti/Memory readonly activation contract for a query.

    Uses only real components. Never invents. Never writes.
    graphiti_write=False, memory_write=False at all times.
    """
    graphiti_probe = _probe_graphiti_readonly()
    memory_probe = _probe_memory_readonly()

    graphiti_read_enabled = graphiti_probe.get("graphiti_read_enabled", False)
    memory_read_enabled = memory_probe.get("memory_read_enabled", False)

    real_component_found = graphiti_read_enabled or memory_read_enabled

    # Fetch context only if graphiti is live
    graphiti_context: dict = {}
    if graphiti_read_enabled and query:
        graphiti_context = _get_graphiti_context_for_query(query)

    # Brody enrichment flags
    brody_can_use_graphiti = graphiti_read_enabled
    brody_can_use_memory = memory_read_enabled

    status = "ACTIVE_READONLY" if real_component_found else "MISSING_REAL_COMPONENT"

    graphiti_memory_context_refs: list = []
    if graphiti_read_enabled:
        graphiti_memory_context_refs.append({
            "source": "GRAPHITI_V20_HTTP",
            "base_url": "http://127.0.0.1:8011",
            "endpoints": [
                "/graph/v20/frozen/status",
                "/graph/v20/frozen/context",
                "/graph/v20/frozen/search",
            ],
        })
    if memory_read_enabled:
        graphiti_memory_context_refs.append({
            "source": "MEMORY_REAL_MODULE",
            "module": "apps/obsidia_api/routes/memory.py",
            "endpoints": ["/api/memory/status", "/api/memory/candidates"],
        })

    return {
        "audit_id": "P52_GRAPHITI_MEMORY_READONLY_ACTIVATION",
        "audit_date": "2026-06-04",
        "graphiti_memory_readonly_activation_status": status,
        "activation_level": "LEVEL_1_READONLY_ACTIVE" if real_component_found else "LEVEL_0_MISSING",
        "real_component_found": real_component_found,
        "real_component_paths": _REAL_COMPONENT_PATHS if real_component_found else [],
        # Graphiti
        "graphiti_read_enabled": graphiti_read_enabled,
        "graphiti_write_enabled": False,
        "graphiti_live": graphiti_probe.get("graphiti_live", False),
        "graphiti_nodes": graphiti_probe.get("graphiti_nodes", 0),
        "graphiti_rels": graphiti_probe.get("graphiti_rels", 0),
        "graphiti_mode": graphiti_probe.get("graphiti_mode", ""),
        "graphiti_source": graphiti_probe.get("graphiti_source", ""),
        "graphiti_context": graphiti_context,
        # Memory
        "memory_read_enabled": memory_read_enabled,
        "memory_write_enabled": False,
        "memory_real_module": memory_probe.get("memory_real_module", False),
        "memory_source": memory_probe.get("memory_source", ""),
        # Brody integration
        "brody_can_use_graphiti_context": brody_can_use_graphiti,
        "brody_can_use_memory_context": brody_can_use_memory,
        "graphiti_memory_context_refs": graphiti_memory_context_refs,
        "graphiti_memory_context_status": status,
        # Invariants
        "runtime_allowed_now": False,
        "activation_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "p52_status": (
            "P52_GRAPHITI_MEMORY_READONLY_CONTROLLED_ACTIVATION_READY"
            if real_component_found
            else "P52_BLOCKED_BY_MISSING_REAL_GRAPHITI_COMPONENT"
        ),
        **_BOUNDARY,
    }
