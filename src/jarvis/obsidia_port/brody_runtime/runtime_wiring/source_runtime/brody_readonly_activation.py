"""
P51 — Brody READONLY Controlled Activation.

Activates Brody at LEVEL_1 READONLY_CONTEXT only.
Brody can answer, explain runtime path, use source context and OS Map.
Brody CANNOT execute actions, write memory, write Graphiti, or emit ACT.
KX108_ONLY. READONLY. runtime_allowed_now=False.
"""
from __future__ import annotations

_BRODY_READONLY_BOUNDARY = {
    "readonly": True,
    "emits_act": False,
    "memory_write": False,
    "graph_write": False,
    "kernel_mutation": False,
    "zip_extraction": False,
    "world_action": False,
    "decision_authority": "KX108_ONLY",
    "runtime_allowed_now": False,
}

_ALLOWED_MODES = ["READONLY_CONTEXT"]

_BLOCKED_MODES = [
    "ACTION",
    "MEMORY_WRITE",
    "GRAPHITI_WRITE",
    "WORLD_ACTION",
    "BLOCKCHAIN_ACTION",
    "EMAIL_SEND",
    "KERNEL_MUTATION",
]

_RUNTIME_PATH_FIELDS = [
    "capability",
    "modules",
    "route",
    "adapter",
    "sources",
    "gate",
]


def build_brody_readonly_activation_state(query: str = "") -> dict:
    """
    Return the P51 Brody readonly activation contract for a given query.

    brody_readonly_enabled=True is explicitly permitted at LEVEL_1.
    runtime_allowed_now stays False — only Brody chat reads are activated.
    activation_allowed_now global stays False.
    """
    q = (query or "").strip()

    # Detect if query contains an action request — always blocked
    _action_keywords = (
        "envoie", "envoyer", "email", "mail", "execute", "exécute",
        "write", "écris", "écrit", "modifie", "modifie", "deploy",
        "déploie", "delete", "supprime", "create file", "commit",
        "push", "act", "action", "wallet", "blockchain", "gencoin",
        "transaction", "send", "post",
    )
    q_lower = q.lower()
    action_requested = any(kw in q_lower for kw in _action_keywords)

    # Build runtime path summary (structural, never invented)
    os_map_summary = _build_os_map_summary(q)

    return {
        "audit_id": "P51_BRODY_READONLY_ACTIVATION",
        "audit_date": "2026-06-04",
        "brody_readonly_activation_status": "ACTIVE_READONLY",
        "activation_level": "LEVEL_1_READONLY_ACTIVE",
        "brody_readonly_enabled": True,
        "brody_can_answer": True,
        "brody_can_explain_runtime_path": True,
        "brody_can_use_source_context": True,
        "brody_can_use_os_map": True,
        "brody_can_execute_actions": False,
        "brody_can_write_memory": False,
        "brody_can_write_graphiti": False,
        "runtime_allowed_now": False,
        "activation_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "allowed_modes": _ALLOWED_MODES,
        "blocked_modes": _BLOCKED_MODES,
        "action_requested": action_requested,
        "action_request_blocked": action_requested,
        "action_status": "ACTION_REQUEST_BLOCKED" if action_requested else "NO_ACTION_IN_QUERY",
        "os_map_summary": os_map_summary,
        "runtime_path_fields": _RUNTIME_PATH_FIELDS,
        "source_resolution_status": "METADATA_AVAILABLE",
        "next_blocked_modes": _BLOCKED_MODES,
        "next_allowed_mode": "READONLY_CONTEXT_ONLY",
        "p51_status": "P51_BRODY_READONLY_CONTROLLED_ACTIVATION_READY",
        **_BRODY_READONLY_BOUNDARY,
    }


def _build_os_map_summary(query: str) -> dict:
    """
    Build a structural OS Map summary for the given query.
    Uses capability_path_router if available; falls back to metadata-only.
    Never invents paths. Never writes. No ACT.
    """
    try:
        from runtime_wiring.source_runtime.capability_path_router import route_capability_path
        routing = route_capability_path(query=query, max_paths=3)
        selected = routing.get("selected_path", {})
        return {
            "os_map_summary_status": "CAPABILITY_ROUTER_RESOLVED",
            "detected_intents": routing.get("detected_intents", []),
            "required_capabilities": routing.get("required_capabilities", []),
            "selected_capability": selected.get("capability_id", ""),
            "selected_modules": selected.get("modules", []),
            "selected_routes": selected.get("routes", []),
            "selected_adapters": selected.get("adapters", []),
            "selected_source_families": selected.get("source_families", []),
            "selected_evidence_packs": selected.get("evidence_packs", []),
            "x108_gate": selected.get("x108_decision", "ALLOW_CONTEXT_ONLY"),
            "readonly": True,
            "emits_act": False,
        }
    except Exception:
        return {
            "os_map_summary_status": "METADATA_ONLY_FALLBACK",
            "detected_intents": [],
            "required_capabilities": [],
            "selected_capability": "",
            "selected_modules": [],
            "selected_routes": [],
            "selected_adapters": [],
            "selected_source_families": [],
            "selected_evidence_packs": [],
            "x108_gate": "ALLOW_CONTEXT_ONLY",
            "readonly": True,
            "emits_act": False,
            "source_resolution_status": "METADATA_ONLY_FALLBACK",
        }


def get_brody_readonly_boundary() -> dict:
    """Return the static readonly boundary invariants."""
    return dict(_BRODY_READONLY_BOUNDARY)
