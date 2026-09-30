"""
sigma/connectors.py — F64 Sigma Connector Map

Descriptive-only connector map for the canonical Sigma monitoring surface
established by F63.

No network calls.  No hardcoded host (only route-path constants).
No decision.  No ACT.  No verdict.  No mutation.

All connector descriptors carry the full sovereignty boundary so that any
consumer can verify Sigma's non-decisional role without contacting the API.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Version and canonical route table
# ---------------------------------------------------------------------------

CONNECTOR_VERSION = "F64"

# Route path constants — relative, host-agnostic.
# Consumers prepend their own OBSIDIA_API_BASE.
SIGMA_ROUTE_DOMAINS = "/api/periphery/monitoring/sigma/domains"
SIGMA_ROUTE_EVALUATE = "/api/periphery/monitoring/sigma/evaluate"
SIGMA_ROUTE_BANK = "/api/periphery/monitoring/sigma/bank"
SIGMA_ROUTE_TRADING = "/api/periphery/monitoring/sigma/trading"
SIGMA_ROUTE_ECOM = "/api/periphery/monitoring/sigma/ecom"
SIGMA_ROUTE_GPS_DEFENSE_AVIATION = "/api/periphery/monitoring/sigma/gps-defense-aviation"

# ---------------------------------------------------------------------------
# Boundary applied to every connector descriptor
# ---------------------------------------------------------------------------

_CONNECTOR_BOUNDARY: dict[str, Any] = {
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

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_sigma_monitoring_routes() -> list[dict[str, Any]]:
    """Return the canonical list of Sigma monitoring route descriptors.

    Each descriptor is informational only — no HTTP call is made here.
    Consumers can use these to build health-checks, gateway configs, or
    documentation without importing FastAPI.
    """
    return [
        {
            "route": SIGMA_ROUTE_DOMAINS,
            "method": "GET",
            "description": "List canonical Sigma domain identifiers.",
            "domain": None,
            "packet_type": "SIGMA_DOMAINS_LIST",
            **_CONNECTOR_BOUNDARY,
        },
        {
            "route": SIGMA_ROUTE_EVALUATE,
            "method": "GET",
            "description": "Multi-domain F62 Sigma registry evaluation (all domains).",
            "domain": "all",
            "packet_type": "SIGMA_REGISTRY_EVALUATION",
            **_CONNECTOR_BOUNDARY,
        },
        {
            "route": SIGMA_ROUTE_BANK,
            "method": "GET",
            "description": "Readonly F62 Sigma evaluation — bank domain.",
            "domain": "bank",
            "packet_type": "SIGMA_DOMAIN_READONLY_PACKET",
            **_CONNECTOR_BOUNDARY,
        },
        {
            "route": SIGMA_ROUTE_TRADING,
            "method": "GET",
            "description": "Readonly F62 Sigma evaluation — trading domain.",
            "domain": "trading",
            "packet_type": "SIGMA_DOMAIN_READONLY_PACKET",
            **_CONNECTOR_BOUNDARY,
        },
        {
            "route": SIGMA_ROUTE_ECOM,
            "method": "GET",
            "description": "Readonly F62 Sigma evaluation — ecom domain.",
            "domain": "ecom",
            "packet_type": "SIGMA_DOMAIN_READONLY_PACKET",
            **_CONNECTOR_BOUNDARY,
        },
        {
            "route": SIGMA_ROUTE_GPS_DEFENSE_AVIATION,
            "method": "GET",
            "description": "Readonly F62 Sigma evaluation — gps_defense_aviation domain.",
            "domain": "gps_defense_aviation",
            "packet_type": "SIGMA_DOMAIN_READONLY_PACKET",
            **_CONNECTOR_BOUNDARY,
        },
    ]


def get_sigma_connector_map() -> dict[str, Any]:
    """Return the full connector map with metadata and all route descriptors.

    Used by F64 reconciliation tests and external health-check consumers.
    """
    routes = get_sigma_monitoring_routes()
    return {
        "connector_version": CONNECTOR_VERSION,
        "connector_type": "SIGMA_MONITORING_READONLY",
        "reconciliation_palier": "F64",
        "dead_endpoint_replaced": "localhost:3001/kernel/ragnarok",
        "canonical_surface": "F63_SIGMA_MONITORING_ENDPOINTS_READONLY",
        "route_count": len(routes),
        "routes": routes,
        **_CONNECTOR_BOUNDARY,
    }


def validate_sigma_connectors() -> dict[str, Any]:
    """Validate that all connector descriptors carry correct sovereignty invariants.

    Returns a dict with status=PASS/FAIL and a list of errors.
    No network call — purely structural validation.
    """
    errors: list[str] = []
    routes = get_sigma_monitoring_routes()

    required_routes = {
        SIGMA_ROUTE_EVALUATE,
        SIGMA_ROUTE_BANK,
        SIGMA_ROUTE_TRADING,
        SIGMA_ROUTE_ECOM,
        SIGMA_ROUTE_GPS_DEFENSE_AVIATION,
    }
    present_routes = {r["route"] for r in routes}
    for req in required_routes:
        if req not in present_routes:
            errors.append(f"MISSING_ROUTE:{req}")

    for descriptor in routes:
        route = descriptor.get("route", "<unknown>")

        if descriptor.get("method") != "GET":
            errors.append(f"{route}:method={descriptor.get('method')!r} (expected GET)")

        for flag, expected in _CONNECTOR_BOUNDARY.items():
            actual = descriptor.get(flag)
            if actual != expected:
                errors.append(f"{route}:{flag}={actual!r} (expected {expected!r})")

        if "localhost:3001" in descriptor.get("route", ""):
            errors.append(f"{route}:contains legacy localhost:3001 reference")
        if "kernel/ragnarok" in descriptor.get("route", ""):
            errors.append(f"{route}:contains dead kernel/ragnarok reference")

    return {
        "status": "PASS" if not errors else "FAIL",
        "connector_version": CONNECTOR_VERSION,
        "routes_validated": len(routes),
        "errors": errors,
        **_CONNECTOR_BOUNDARY,
    }
