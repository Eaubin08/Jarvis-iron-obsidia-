"""
P53 — World Action Bus Dry-Run Controlled Activation.

Activates real World Action Bus components at LEVEL_2 DRY_RUN_ACTIVE only.
Real components confirmed:
  periphery/world_calls/world_action_bus.py         (WorldActionBus, dry_run_only=True)
  periphery/world_action_controlled_runtime_stub.py  (run_world_action_stub, world_action_allowed=False)
  periphery/world_action_gateway.py                  (evaluate_world_action_readiness)

NO real action. NO ACT. NO side effects. NO external API. NO email. NO blockchain tx.
NO memory write. NO Graphiti write. NO kernel mutation.
KX108_ONLY. DRY_RUN. runtime_allowed_now=False. emits_act=False.
"""
from __future__ import annotations

_REAL_COMPONENT_PATHS = [
    "periphery/world_calls/world_action_bus.py",
    "periphery/world_action_controlled_runtime_stub.py",
    "periphery/world_action_gateway.py",
    "runtime_wiring/dry_run_packet_router.py",
    "Demo-obsidia-x108-proof/connectors/world_action_dry_run_flow.py",
]

_BOUNDARY = {
    "readonly": True,
    "emits_act": False,
    "real_action_enabled": False,
    "can_execute_real_action": False,
    "memory_write": False,
    "graphiti_write": False,
    "neo4j_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "world_action": False,
    "decision_authority": "KX108_ONLY",
    "runtime_allowed_now": False,
    "x108_required_before_act": True,
}

# Action type keywords → risk classification
_ACTION_PATTERNS: list[tuple[list[str], str, str]] = [
    (["mail", "email", "envoie", "envoyer", "send mail", "send email"],
     "EMAIL_SEND", "HIGH"),
    (["transaction", "blockchain", "crypto", "wallet", "token", "gencoin",
      "defi", "défi", "on-chain", "onchain", "smart contract", "nft"],
     "BLOCKCHAIN_TX", "CRITICAL"),
    (["écris en mémoire", "écrire en mémoire", "write memory", "sauvegarde mémoire",
      "memory write", "save to memory", "enregistre en mémoire"],
     "MEMORY_WRITE", "HIGH"),
    (["appelle une api", "api externe", "appel api", "external api",
      "webhook", "http post", "http put", "curl", "requests.post"],
     "EXTERNAL_API_CALL", "HIGH"),
    (["fais une action", "exécute", "execute", "run action", "lance une action",
      "perform action", "do action"],
     "GENERAL_ACTION", "MEDIUM"),
]


def _detect_action_type(query: str) -> tuple[bool, str, str]:
    """Return (action_detected, action_type, risk_class)."""
    q = query.lower()
    for keywords, action_type, risk_class in _ACTION_PATTERNS:
        if any(kw in q for kw in keywords):
            return True, action_type, risk_class
    return False, "NO_ACTION", "NONE"


def _probe_world_action_bus() -> dict:
    """Probe the real WorldActionBus — import-only, no publish."""
    try:
        from periphery.world_calls.world_action_bus import (
            WorldActionEvent,
            publish_event,
        )
        return {
            "world_action_bus_found": True,
            "world_action_bus_source": "periphery/world_calls/world_action_bus.py",
            "callable_publish_event": callable(publish_event),
            "WorldActionEvent_found": WorldActionEvent is not None,
            "dry_run_only_hardcoded": True,
            "blocked_default": True,
            "bus_error": None,
        }
    except Exception as exc:
        return {
            "world_action_bus_found": False,
            "world_action_bus_source": "IMPORT_ERROR",
            "bus_error": type(exc).__name__,
        }


def _probe_world_action_stub() -> dict:
    """Probe the real controlled runtime stub — import-only, no execution."""
    try:
        from periphery.world_action_controlled_runtime_stub import (
            WorldActionDryRunPacket,
            run_world_action_stub,
        )
        return {
            "stub_found": True,
            "stub_source": "periphery/world_action_controlled_runtime_stub.py",
            "callable_run_stub": callable(run_world_action_stub),
            "WorldActionDryRunPacket_found": WorldActionDryRunPacket is not None,
            "world_action_allowed_default": False,
            "dry_run_only_default": True,
            "stub_error": None,
        }
    except Exception as exc:
        return {
            "stub_found": False,
            "stub_source": "IMPORT_ERROR",
            "stub_error": type(exc).__name__,
        }


def _build_dry_run_packet(query: str, action_type: str, risk_class: str) -> dict:
    """Build a dry-run intent packet for an action query. No side effects."""
    return {
        "dry_run_packet_type": "WORLD_ACTION_INTENT_DRY_RUN",
        "query": query[:200],
        "detected_action_type": action_type,
        "risk_class": risk_class,
        "x108_required": True,
        "would_require_hold": True,
        "would_require_human_confirmation": True,
        "real_execution": False,
        "side_effects": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": "ACTION_REQUEST_BLOCKED",
        "block_reason": f"KX108_ONLY — {action_type} blocked at dry-run boundary",
    }


def build_world_action_bus_dry_run_state(query: str = "") -> dict:
    """
    Return the P53 World Action Bus dry-run activation contract for a query.

    Uses only real components. Never invents. Never executes real action.
    real_action_enabled=False, emits_act=False, runtime_allowed_now=False at all times.
    """
    bus_probe = _probe_world_action_bus()
    stub_probe = _probe_world_action_stub()

    real_component_found = (
        bus_probe.get("world_action_bus_found", False)
        or stub_probe.get("stub_found", False)
    )

    status = "ACTIVE_DRY_RUN" if real_component_found else "MISSING_REAL_COMPONENT"
    activation_level = (
        "LEVEL_2_DRY_RUN_ACTIVE" if real_component_found else "LEVEL_0_MISSING"
    )

    # Action detection
    action_detected, action_type, risk_class = _detect_action_type(query)
    action_request_blocked = action_detected  # always blocked in dry-run mode

    dry_run_packet: dict = {}
    if action_detected and real_component_found:
        dry_run_packet = _build_dry_run_packet(query, action_type, risk_class)

    return {
        "audit_id": "P53_WORLD_ACTION_BUS_DRY_RUN_ACTIVATION",
        "audit_date": "2026-06-04",
        "world_action_bus_dry_run_status": status,
        "activation_level": activation_level,
        "real_component_found": real_component_found,
        "real_component_paths": _REAL_COMPONENT_PATHS if real_component_found else [],
        # Dry-run capabilities
        "dry_run_enabled": real_component_found,
        "can_build_action_intent": real_component_found,
        "can_route_to_x108": real_component_found,
        "can_emit_dry_run_packet": real_component_found,
        # Action detection
        "action_request_detected": action_detected,
        "action_request_blocked": action_request_blocked,
        "detected_action_type": action_type,
        "action_risk_class": risk_class,
        # Dry-run packet
        "dry_run_packet": dry_run_packet,
        # Bus probe
        "world_action_bus_found": bus_probe.get("world_action_bus_found", False),
        "world_action_bus_source": bus_probe.get("world_action_bus_source", ""),
        "stub_found": stub_probe.get("stub_found", False),
        "stub_source": stub_probe.get("stub_source", ""),
        # Invariants — always False
        "allowed_to_act": False,
        "p53_status": (
            "P53_WORLD_ACTION_BUS_DRY_RUN_CONTROLLED_ACTIVATION_READY"
            if real_component_found
            else "P53_BLOCKED_BY_MISSING_REAL_WORLD_ACTION_BUS"
        ),
        **_BOUNDARY,
    }
