"""
F66 — Sigma Orchestrator Preview READONLY

Purpose:
- Aggregate Sigma readonly layer state.
- Expose no route.
- Emit no decision.
- Mutate no kernel, X108, memory, Graphiti, Neo4j, or bus state.

Boundary:
- decision_authority = KX108_ONLY
- readonly = True
- advisory_only = True
- allowed_to_decide = False
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, List, Optional


PALIER = "F66"
COMPONENT = "SIGMA_ORCHESTRATOR_PREVIEW_READONLY"
DECISION_AUTHORITY = "KX108_ONLY"

_FALSE_FLAGS = (
    "allowed_to_decide",
    "emits_act",
    "emits_verdict",
    "kernel_mutation",
    "x108_mutation",
    "neo4j_write",
    "graphiti_write",
    "memory_write",
    "brody_decision",
)

_REQUIRED_LAYERS = (
    "registry",
    "dispatcher",
    "packets",
    "connectors",
    "bus_bridge",
)


def _safe_import(module_name: str) -> Dict[str, Any]:
    """
    Import a module in read-only inspection mode and return a compact summary.

    This function does not call route handlers, network clients, file writers,
    kernel gates, Graphiti, Neo4j, or memory writers.
    """
    try:
        module = import_module(module_name)
        public_names = [
            name for name in dir(module)
            if not name.startswith("_")
        ]
        return {
            "module": module_name,
            "available": True,
            "error": None,
            "public_symbol_count": len(public_names),
            "public_symbols_preview": public_names[:25],
        }
    except Exception as exc:  # pragma: no cover - defensive introspection path
        return {
            "module": module_name,
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
            "public_symbol_count": 0,
            "public_symbols_preview": [],
        }


def _build_layers() -> Dict[str, Dict[str, Any]]:
    return {
        "registry": _safe_import("sigma.registry"),
        "dispatcher": _safe_import("sigma.evaluate"),
        "packets": _safe_import("sigma.packets"),
        "connectors": _safe_import("sigma.connectors"),
        "bus_bridge": _safe_import("apps.obsidia_api.bus.sigma_bridge"),
    }


def build_sigma_orchestrator_preview() -> Dict[str, Any]:
    """
    Build a readonly Sigma orchestration preview.

    This is an aggregation packet only:
    - no HTTP route
    - no runtime mutation
    - no decision
    - no ACT / verdict emission
    """
    preview: Dict[str, Any] = {
        "palier": PALIER,
        "component": COMPONENT,
        "decision_authority": DECISION_AUTHORITY,
        "readonly": True,
        "advisory_only": True,
        "allowed_to_decide": False,
        "emits_act": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "x108_mutation": False,
        "neo4j_write": False,
        "graphiti_write": False,
        "memory_write": False,
        "brody_decision": False,
        "routes_created": False,
        "main_modified": False,
        "network_call": False,
        "file_write": False,
        "layers": _build_layers(),
        "status": "READY",
    }
    return preview


def validate_sigma_orchestrator_preview(
    preview: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Validate the F66 readonly preview boundary.
    """
    candidate = preview if preview is not None else build_sigma_orchestrator_preview()
    violations: List[str] = []

    if candidate.get("palier") != PALIER:
        violations.append("palier_mismatch")

    if candidate.get("component") != COMPONENT:
        violations.append("component_mismatch")

    if candidate.get("decision_authority") != DECISION_AUTHORITY:
        violations.append("decision_authority_mismatch")

    if candidate.get("readonly") is not True:
        violations.append("readonly_not_true")

    if candidate.get("advisory_only") is not True:
        violations.append("advisory_only_not_true")

    for flag in _FALSE_FLAGS:
        if candidate.get(flag) is not False:
            violations.append(f"{flag}_not_false")

    if candidate.get("routes_created") is not False:
        violations.append("routes_created_not_false")

    if candidate.get("main_modified") is not False:
        violations.append("main_modified_not_false")

    if candidate.get("network_call") is not False:
        violations.append("network_call_not_false")

    if candidate.get("file_write") is not False:
        violations.append("file_write_not_false")

    layers = candidate.get("layers")
    if not isinstance(layers, dict):
        violations.append("layers_not_dict")
    else:
        for layer in _REQUIRED_LAYERS:
            if layer not in layers:
                violations.append(f"missing_layer_{layer}")

    return {
        "status": "PASS" if not violations else "FAIL",
        "palier": PALIER,
        "component": COMPONENT,
        "violations": violations,
        "decision_authority": candidate.get("decision_authority"),
        "readonly": candidate.get("readonly"),
        "advisory_only": candidate.get("advisory_only"),
        "allowed_to_decide": candidate.get("allowed_to_decide"),
        "emits_act": candidate.get("emits_act"),
        "emits_verdict": candidate.get("emits_verdict"),
        "kernel_mutation": candidate.get("kernel_mutation"),
        "x108_mutation": candidate.get("x108_mutation"),
        "neo4j_write": candidate.get("neo4j_write"),
        "graphiti_write": candidate.get("graphiti_write"),
        "memory_write": candidate.get("memory_write"),
        "brody_decision": candidate.get("brody_decision"),
    }


__all__ = [
    "PALIER",
    "COMPONENT",
    "DECISION_AUTHORITY",
    "build_sigma_orchestrator_preview",
    "validate_sigma_orchestrator_preview",
]
