"""
sigma/graphiti_readonly_bridge.py — F70 Sigma → Graphiti Readonly Bridge

Builds a readonly query candidate from the Sigma domain state toward the
Graphiti memory surface.

Pure in-process.  No HTTP.  No Neo4j write.  No Graphiti write.  No ACT.
KX108_ONLY decision authority preserved.
"""
from __future__ import annotations

from typing import Any

from sigma.registry import list_sigma_domains, validate_sigma_registry
from sigma.connectors import get_sigma_connector_map

GRAPHITI_BRIDGE_VERSION = "F70"

_BOUNDARY: dict[str, Any] = {
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

_CANONICAL_DOMAINS = ("bank", "trading", "ecom", "gps_defense_aviation")

# Graphiti search topic keywords per domain (readonly query candidates only).
_DOMAIN_GRAPHITI_TOPICS: dict[str, list[str]] = {
    "bank": ["bank", "risk", "transaction", "fraud", "compliance"],
    "trading": ["trading", "market", "execution", "portfolio", "signal"],
    "ecom": ["ecom", "basket", "offer", "cart", "pricing"],
    "gps_defense_aviation": ["gps", "defense", "aviation", "navigation", "safety"],
}


def build_sigma_graphiti_readonly_query(domain: str) -> dict[str, Any]:
    """Build a readonly Graphiti search candidate for a given Sigma domain.

    In-process only — no HTTP call, no Neo4j access.
    Returns a query candidate dict with graphiti_probe_mode=IN_PROCESS_ONLY.
    """
    topics = _DOMAIN_GRAPHITI_TOPICS.get(domain, [domain])
    connector_map = get_sigma_connector_map()
    return {
        "bridge_version": GRAPHITI_BRIDGE_VERSION,
        "domain": domain,
        "domain_valid": domain in _CANONICAL_DOMAINS,
        "graphiti_probe_mode": "IN_PROCESS_ONLY",
        "graphiti_live_probe": False,
        "search_topics": topics,
        "search_query_candidate": " OR ".join(topics),
        "connector_version": connector_map.get("connector_version"),
        "sigma_available": True,
        **_BOUNDARY,
    }


def validate_sigma_graphiti_bridge() -> dict[str, Any]:
    """Validate the Sigma → Graphiti bridge structure (in-process only).

    Checks registry health, domain list, and boundary flags.
    Returns status=PASS/FAIL.  Never contacts Neo4j or ObsidiaShell.
    """
    errors: list[str] = []

    registry = validate_sigma_registry()
    if registry.get("status") != "PASS":
        errors.extend(f"registry:{e}" for e in registry.get("errors", []))

    domains = list_sigma_domains()
    for d in _CANONICAL_DOMAINS:
        if d not in domains:
            errors.append(f"missing_domain:{d}")

    # Verify no write flags active
    probe = build_sigma_graphiti_readonly_query("bank")
    for flag in ("neo4j_write", "graphiti_write", "memory_write", "emits_act"):
        if probe.get(flag) is not False:
            errors.append(f"boundary_violation:{flag}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "bridge_version": GRAPHITI_BRIDGE_VERSION,
        "registry_status": registry.get("status"),
        "canonical_domains": domains,
        "domain_count": len(domains),
        "errors": errors,
        **_BOUNDARY,
    }
