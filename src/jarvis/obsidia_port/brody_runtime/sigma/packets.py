"""
sigma/packets.py — F62 Sigma Domain Packet Normalizer

Builds readonly, sovereignty-annotated, normalized packet structures
for Sigma domain and registry evaluations.

Sovereignty invariants (all packets):
  decision_authority = KX108_ONLY
  readonly = True
  advisory_only = True
  allowed_to_decide = False
  emits_act = False  /  emitted_act = False
  emits_verdict = False  /  emitted_verdict = False
  kernel_mutation = False
  x108_mutation = False
  neo4j_write = False
  graphiti_write = False
  memory_write = False
  brody_decision = False

No pipeline execution. No route creation. No storage.
"""

from __future__ import annotations

from typing import Any

PACKET_VERSION = "F62"

_PACKET_BOUNDARY: dict[str, Any] = {
    "decision_authority": "KX108_ONLY",
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
}

_CONTROL_PLANE_SAFE: dict[str, Any] = {
    "routed_to_decision": False,
    "payload_interpreted_as_command": False,
    "emitted_act": False,
    "emitted_verdict": False,
    "mutation_performed": False,
    "storage_performed": False,
}

_X108_GATE_SAFE: dict[str, Any] = {
    "decision_authority": "KX108_ONLY",
    "sigma_allowed_to_decide": False,
    "sigma_allowed_to_act": False,
    "gate_invoked": False,
}


def build_sigma_domain_packet(
    domain: str,
    registry_domain: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a normalized F62 readonly packet for one Sigma domain.

    Parameters
    ----------
    domain:
        Canonical domain identifier (e.g. "bank").
    registry_domain:
        Output of get_sigma_domain(domain) from sigma.registry — contains
        runtime_bound, agent_count, agents, boundary, etc.
    payload:
        Raw input payload (or None). Used only to record payload_received flag.
    """
    runtime_bound: bool = bool(registry_domain.get("runtime_bound", False))
    agent_count: int = int(registry_domain.get("agent_count", 0))
    agents_raw = registry_domain.get("agents", [])
    agent_ids: list[str] = [
        a.get("id", str(a)) if isinstance(a, dict) else str(a)
        for a in (agents_raw if isinstance(agents_raw, list) else [])
    ]
    payload_received: bool = bool(payload)

    return {
        "packet_version": PACKET_VERSION,
        "packet_type": "SIGMA_DOMAIN_READONLY_PACKET",
        "domain": domain,
        "domain_state": {
            "status": "OBSERVED",
            "runtime_bound": runtime_bound,
            "agent_count": agent_count,
            "payload_received": payload_received,
        },
        "domain_aggregate": {
            "mode": "READONLY_AGGREGATE",
            "summary": f"{domain}: {agent_count} agent(s) observed, advisory only",
            "confidence": 0.0,
            "evidence_refs": [],
        },
        "meta_agents_packet": {
            "agent_count": agent_count,
            "agents": agent_ids,
            "execution_performed": False,
        },
        "reflex_diagnostic_packet": {
            "reflex_mode": "OBSERVATION_ONLY",
            "alerts": [],
            "warnings": [],
        },
        "control_plane_packet": dict(_CONTROL_PLANE_SAFE),
        "x108_gate": dict(_X108_GATE_SAFE),
        "boundary": dict(_PACKET_BOUNDARY),
    }


def build_sigma_registry_packet(
    evaluations: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a normalized F62 readonly packet covering all evaluated domains.

    Parameters
    ----------
    evaluations:
        Mapping {domain: evaluate_sigma_domain(domain, payload)} for all
        canonical domains.
    payload:
        Raw input payload (or None). Not executed — recorded for traceability.
    """
    domains = list(evaluations.keys())
    return {
        "packet_version": PACKET_VERSION,
        "packet_type": "SIGMA_REGISTRY_READONLY_PACKET",
        "domains": domains,
        "evaluations": evaluations,
        "control_plane_packet": dict(_CONTROL_PLANE_SAFE),
        "boundary": dict(_PACKET_BOUNDARY),
    }


def validate_sigma_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Validate that a packet satisfies F62 structure and sovereignty invariants.

    Returns a dict with status=PASS/FAIL and a list of errors.
    """
    errors: list[str] = []

    if packet.get("packet_version") != PACKET_VERSION:
        errors.append(
            f"packet_version={packet.get('packet_version')!r} (expected {PACKET_VERSION!r})"
        )

    for section in (
        "domain_state",
        "domain_aggregate",
        "meta_agents_packet",
        "reflex_diagnostic_packet",
        "control_plane_packet",
        "x108_gate",
        "boundary",
    ):
        if section not in packet:
            errors.append(f"MISSING_SECTION:{section}")

    boundary = packet.get("boundary") or {}
    if boundary.get("decision_authority") != "KX108_ONLY":
        errors.append("boundary.decision_authority != KX108_ONLY")
    for flag in (
        "allowed_to_decide",
        "emits_act",
        "emits_verdict",
        "kernel_mutation",
        "x108_mutation",
        "neo4j_write",
        "graphiti_write",
        "memory_write",
        "brody_decision",
    ):
        if boundary.get(flag) is not False:
            errors.append(f"boundary.{flag} != False")

    control = packet.get("control_plane_packet") or {}
    for flag in (
        "routed_to_decision",
        "payload_interpreted_as_command",
        "emitted_act",
        "emitted_verdict",
        "mutation_performed",
        "storage_performed",
    ):
        if control.get(flag) is not False:
            errors.append(f"control_plane_packet.{flag} != False")

    x108 = packet.get("x108_gate")
    if isinstance(x108, dict):
        if x108.get("sigma_allowed_to_decide") is not False:
            errors.append("x108_gate.sigma_allowed_to_decide != False")
        if x108.get("sigma_allowed_to_act") is not False:
            errors.append("x108_gate.sigma_allowed_to_act != False")
        if x108.get("decision_authority") != "KX108_ONLY":
            errors.append("x108_gate.decision_authority != KX108_ONLY")

    agg = packet.get("domain_aggregate") or {}
    confidence = agg.get("confidence")
    if confidence is not None:
        try:
            cf = float(confidence)
            if not (0.0 <= cf <= 1.0):
                errors.append(f"domain_aggregate.confidence={cf} out of [0.0, 1.0]")
        except (TypeError, ValueError):
            errors.append(f"domain_aggregate.confidence={confidence!r} not numeric")

    return {
        "status": "PASS" if not errors else "FAIL",
        "packet_version": packet.get("packet_version"),
        "packet_type": packet.get("packet_type"),
        "errors": errors,
    }
