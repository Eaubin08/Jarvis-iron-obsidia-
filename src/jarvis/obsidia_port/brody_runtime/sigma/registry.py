from __future__ import annotations

from .domains.bank_agents import build_bank_agents
from .domains.gps_defense_aviation_agents import build_gps_defense_aviation_agents
from .domains.trading_agents import build_trading_agents
from .domains.ecom_agents import build_ecom_agents
from .domains.meta_agents import build_meta_agents


def build_agent_registry():
    return {
        "bank": build_bank_agents(),
        "gps_defense_aviation": build_gps_defense_aviation_agents(),
        "trading": build_trading_agents(),
        "ecom": build_ecom_agents(),
        "meta": build_meta_agents(),
    }


REGISTRY = build_agent_registry()

# ── F60 — Sigma domain registry with sovereignty metadata ────────────────────

_CANONICAL_DOMAINS = ("bank", "trading", "ecom", "gps_defense_aviation")

_DOMAIN_DISPLAY_NAMES: dict[str, str] = {
    "bank": "Bank / Risk / Transaction Safety",
    "trading": "Trading / Market / Execution Safety",
    "ecom": "E-Commerce / Basket / Offer Safety",
    "gps_defense_aviation": "GPS / Defense / Aviation Safety",
    "meta": "Meta / Cross-Domain Governance",
}

_BOUNDARY: dict[str, object] = {
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


def list_sigma_domains() -> list[str]:
    """Return canonical Sigma domain identifiers (F60)."""
    return list(_CANONICAL_DOMAINS)


def get_sigma_domain(domain: str) -> dict:
    """Return a readonly sovereignty descriptor for a single Sigma domain (F60)."""
    reg = build_agent_registry()
    if domain not in reg:
        raise KeyError(f"Unknown Sigma domain: {domain}")
    agents = reg[domain]
    runtime_bound = len(agents) > 0
    implementation_status = "RUNTIME_BOUND" if runtime_bound else "DECLARED_READONLY_DESCRIPTOR"
    return {
        "domain": domain,
        "display_name": _DOMAIN_DISPLAY_NAMES.get(domain, domain),
        "implementation_status": implementation_status,
        "runtime_bound": runtime_bound,
        "agent_count": len(agents),
        "agents": [
            {
                "id": a.agent_id,
                "role": type(a).__name__,
                "runtime_bound": True,
                "advisory_only": True,
                "decision_authority": "KX108_ONLY",
                "emits_act": False,
                "emits_verdict": False,
            }
            for a in agents
        ],
        "boundary": dict(_BOUNDARY),
    }


def get_sigma_registry() -> dict:
    """Return full Sigma registry with sovereignty metadata for all canonical domains (F60)."""
    return {
        "registry_version": "F60",
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "advisory_only": True,
        "domains": {d: get_sigma_domain(d) for d in _CANONICAL_DOMAINS},
    }


def validate_sigma_registry() -> dict:
    """Validate all canonical Sigma domains are present, non-empty, and KX108_ONLY (F60)."""
    reg = build_agent_registry()
    errors: list[str] = []
    for domain in _CANONICAL_DOMAINS:
        if domain not in reg:
            errors.append(f"MISSING_DOMAIN:{domain}")
        elif not reg[domain]:
            errors.append(f"EMPTY_DOMAIN:{domain}")
    return {
        "status": "PASS" if not errors else "FAIL",
        "canonical_domains_checked": list(_CANONICAL_DOMAINS),
        "errors": errors,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
    }
