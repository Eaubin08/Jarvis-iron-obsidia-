"""
Runtime loader — safe periphery module imports.
Returns REAL_MODULE if import succeeds, BACKEND_STUB if module missing,
MODULE_ERROR if import crashes. Never hides real status.
"""
from __future__ import annotations
from typing import Any, Callable


def _safe_import(module_name: str, attr: str) -> tuple[Any | None, str]:
    try:
        mod = __import__(module_name, fromlist=[attr])
        obj = getattr(mod, attr, None)
        if obj is None:
            return None, "BACKEND_STUB"
        return obj, "REAL_MODULE"
    except ImportError:
        return None, "BACKEND_STUB"
    except Exception:
        return None, "MODULE_ERROR"


def load_runtime_components() -> dict[str, dict[str, Any]]:
    components: dict[str, dict[str, Any]] = {}

    # Brody
    brody_respond_fn, brody_status = _safe_import("periphery.brody.brody_runtime_readonly", "brody_respond")
    brody_contract_fn, contract_status = _safe_import("periphery.brody.brody_response_contract", "BrodyResponseContract")
    sanitize_fn, sanitize_status = _safe_import("periphery.brody.brody_response_sanitizer", "sanitize_brody_response")
    components["brody"] = {
        "status": "REAL_MODULE" if all(s == "REAL_MODULE" for s in [brody_status, contract_status, sanitize_status]) else "BACKEND_STUB",
        "brody_respond": brody_respond_fn,
        "brody_contract": brody_contract_fn,
        "sanitize": sanitize_fn,
    }

    # Language
    detect_fn, lang_status = _safe_import("periphery.language.language_router", "detect_language")
    authority_fn, auth_status = _safe_import("periphery.language.language_router", "has_authority_claim")
    components["language"] = {
        "status": "REAL_MODULE" if lang_status == "REAL_MODULE" else "BACKEND_STUB",
        "detect_language": detect_fn,
        "has_authority_claim": authority_fn,
    }

    # Context
    build_ctx_fn, ctx_status = _safe_import("periphery.context.context_packet_builder_v2", "build_context_packet_v2")
    components["context"] = {
        "status": "REAL_MODULE" if ctx_status == "REAL_MODULE" else "BACKEND_STUB",
        "build_context_packet_v2": build_ctx_fn,
    }

    # X108 ingress
    boundary_fn, boundary_status = _safe_import("periphery.x108_ingress.x108_context_boundary", "check_x108_context_boundary")
    components["x108_ingress"] = {
        "status": "REAL_MODULE" if boundary_status == "REAL_MODULE" else "BACKEND_STUB",
        "check_x108_context_boundary": boundary_fn,
    }

    # Reverse OS
    project_fn, rev_status = _safe_import("periphery.reverse_os.action_projection_readonly", "project_action_readonly")
    components["reverse_os"] = {
        "status": "REAL_MODULE" if rev_status == "REAL_MODULE" else "BACKEND_STUB",
        "project_action_readonly": project_fn,
    }

    # Memory
    mem_candidate_fn, mem_status = _safe_import("periphery.memory.memory_candidate", "build_memory_candidate_v2")
    prom_policy_fn, prom_status = _safe_import("periphery.memory.memory_promotion_policy", "evaluate_promotion_policy")
    source_types_mod, src_status = _safe_import("periphery.memory.memory_source_types", "MemorySourceType")
    components["memory"] = {
        "status": "REAL_MODULE" if all(s == "REAL_MODULE" for s in [mem_status, prom_status]) else "BACKEND_STUB",
        "build_memory_candidate_v2": mem_candidate_fn,
        "evaluate_promotion_policy": prom_policy_fn,
        "MemorySourceType": source_types_mod,
    }

    # Graphiti
    graphiti_fn, graph_status = _safe_import("periphery.graphiti.graphiti_readonly_bridge", "query_graphiti_readonly")
    components["graphiti"] = {
        "status": "REAL_MODULE" if graph_status == "REAL_MODULE" else "BACKEND_STUB",
        "query_graphiti_readonly": graphiti_fn,
    }

    # Gencoin
    gencoin_fn, gen_status = _safe_import("periphery.gencoin_ledger", "read_ledger")
    components["gencoin"] = {
        "status": "REAL_MODULE" if gen_status == "REAL_MODULE" else "BACKEND_STUB",
        "read_ledger": gencoin_fn,
    }

    return components
