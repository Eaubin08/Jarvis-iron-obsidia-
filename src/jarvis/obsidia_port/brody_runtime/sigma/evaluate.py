from __future__ import annotations

from enum import Enum
from typing import Any

from .contracts import (
    BankState,
    TradingState,
    EcomState,
    GpsDefenseAviationState,
)
from .protocols import (
    run_bank_pipeline,
    run_trading_pipeline,
    run_ecom_pipeline,
    run_gps_defense_aviation_pipeline,
)
from .registry import (
    list_sigma_domains,
    get_sigma_domain,
    validate_sigma_registry,
)
from .packets import build_sigma_domain_packet


BOUNDARY: dict[str, Any] = {
    "decision_authority": "KX108_ONLY",
    "readonly": True,
    "advisory_only": True,
    "allowed_to_decide": False,
    "emits_act": False,
    "emits_verdict": False,
    "memory_write": False,
    "graphiti_write": False,
    "neo4j_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "brody_decision": False,
    "runtime_execute": False,
}


SUPPORTED_DOMAINS = {
    "bank",
    "trading",
    "ecom",
    "gps_defense_aviation",
}


def _hydrate_state(cls: type, payload: dict[str, Any] | None):
    payload = dict(payload or {})

    try:
        return cls(**payload)
    except TypeError:
        obj = cls()
        for key, value in payload.items():
            setattr(obj, key, value)
        return obj


def _plain(value: Any) -> Any:
    """
    Safe serializer for Sigma objects.

    Important:
    - UniversalBase defines dynamic __getattr__.
    - Therefore we must NOT call hasattr(value, "value") before checking __dict__.
    - Enum detection must use isinstance(value, Enum), not hasattr().
    """

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    if isinstance(value, list):
        return [_plain(v) for v in value]

    if isinstance(value, tuple):
        return [_plain(v) for v in value]

    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}

    if hasattr(value, "__dict__"):
        return {
            str(k): _plain(v)
            for k, v in vars(value).items()
            if not k.startswith("_")
        }

    return str(value)


def _envelope_to_dict(envelope: Any, domain: str) -> dict[str, Any]:
    data = _plain(envelope)

    if not isinstance(data, dict):
        data = {"raw_envelope": data}

    # Hard repair if a legacy/dynamic object failed to expose critical fields.
    data["domain"] = str(data.get("domain") or domain)
    data["x108_gate"] = str(data.get("x108_gate") or "HOLD")

    return {
        **data,
        **BOUNDARY,
        "source": "SIGMA_UNIFIED_DISPATCHER_V1",
        "mode": "READONLY_DOMAIN_SIGMA_ENVELOPE",
        "domain_sigma_envelope": True,
        "dispatcher_version": "F61",
        "execution_mode": "READONLY_DESCRIPTOR_EVALUATION",
        "payload_interpreted_as_command": False,
        "routed_to_decision": False,
        "emitted_act": False,
        "emitted_verdict": False,
        "mutation_performed": False,
        "storage_performed": False,
    }


def _is_f62_x108_gate(value: Any) -> bool:
    """Return True only if value is already the normalized F62 x108_gate dict."""
    return (
        isinstance(value, dict)
        and "sigma_allowed_to_decide" in value
        and "sigma_allowed_to_act" in value
    )


def _enrich_with_packet(
    base: dict[str, Any],
    domain: str,
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    try:
        registry_domain: dict[str, Any] = get_sigma_domain(domain)
    except Exception:
        registry_domain = {"runtime_bound": False, "agent_count": 0, "agents": []}
    packet = build_sigma_domain_packet(domain, registry_domain, payload)

    # Rescue any legacy pipeline x108_gate (string or non-F62 dict) so the
    # normalized F62 dict from the packet is never overwritten.
    raw_gate = base.get("x108_gate")
    if raw_gate is not None and not _is_f62_x108_gate(raw_gate):
        base = dict(base)  # avoid mutating caller's dict
        del base["x108_gate"]
        base["pipeline_x108_gate_observed"] = raw_gate

    # base wins on remaining key conflicts — preserves all F61 flat sovereignty flags
    return {**packet, **base}


def evaluate_sigma_domain(
    domain: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = str(domain or "").strip().lower()

    if normalized == "bank":
        base = _envelope_to_dict(
            run_bank_pipeline(_hydrate_state(BankState, payload)), normalized
        )
        return _enrich_with_packet(base, normalized, payload)

    if normalized == "trading":
        base = _envelope_to_dict(
            run_trading_pipeline(_hydrate_state(TradingState, payload)), normalized
        )
        return _enrich_with_packet(base, normalized, payload)

    if normalized == "ecom":
        base = _envelope_to_dict(
            run_ecom_pipeline(_hydrate_state(EcomState, payload)), normalized
        )
        return _enrich_with_packet(base, normalized, payload)

    if normalized == "gps_defense_aviation":
        base = _envelope_to_dict(
            run_gps_defense_aviation_pipeline(
                _hydrate_state(GpsDefenseAviationState, payload)
            ),
            normalized,
        )
        return _enrich_with_packet(base, normalized, payload)

    fallback: dict[str, Any] = {
        **BOUNDARY,
        "source": "SIGMA_UNIFIED_DISPATCHER_V1",
        "mode": "READONLY_DOMAIN_SIGMA_ENVELOPE",
        "domain_sigma_envelope": True,
        "domain": normalized or "unknown",
        "supported_domains": sorted(SUPPORTED_DOMAINS),
        "status": "UNSUPPORTED_DOMAIN",
        "x108_gate": "HOLD",
        "reason_code": "UNSUPPORTED_SIGMA_DOMAIN",
        "unknowns": ["UNSUPPORTED_SIGMA_DOMAIN"],
        "risk_flags": [],
        "contradictions": [],
    }
    return _enrich_with_packet(fallback, normalized or "unknown", payload)


def evaluate_sigma_registry(
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    domains = list_sigma_domains()
    results: dict[str, Any] = {}
    for domain in domains:
        results[domain] = evaluate_sigma_domain(domain, payload)
    return {
        **BOUNDARY,
        "source": "SIGMA_UNIFIED_DISPATCHER_V1",
        "mode": "READONLY_REGISTRY_EVALUATION",
        "dispatcher_version": "F61",
        "packet_version": "F62",
        "execution_mode": "READONLY_DESCRIPTOR_EVALUATION",
        "payload_interpreted_as_command": False,
        "routed_to_decision": False,
        "emitted_act": False,
        "emitted_verdict": False,
        "mutation_performed": False,
        "storage_performed": False,
        "domains_evaluated": domains,
        "results": results,
    }


def validate_sigma_dispatcher() -> dict[str, Any]:
    registry_validation = validate_sigma_registry()
    domains = list_sigma_domains()
    errors: list[str] = []

    for domain in domains:
        result = evaluate_sigma_domain(domain, None)
        for flag, expected in (
            ("advisory_only", True),
            ("allowed_to_decide", False),
            ("emits_act", False),
            ("emitted_act", False),
            ("emits_verdict", False),
            ("emitted_verdict", False),
            ("routed_to_decision", False),
            ("payload_interpreted_as_command", False),
            ("mutation_performed", False),
            ("storage_performed", False),
            ("kernel_mutation", False),
            ("x108_mutation", False),
            ("brody_decision", False),
        ):
            if result.get(flag) != expected:
                errors.append(f"{domain}:{flag}={result.get(flag)!r} (expected {expected!r})")

    registry_errors = registry_validation.get("errors", [])
    errors.extend(registry_errors)

    return {
        "status": "PASS" if not errors else "FAIL",
        "dispatcher_version": "F61",
        "canonical_domains_checked": domains,
        "registry_validation": registry_validation,
        "errors": errors,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "advisory_only": True,
        "allowed_to_decide": False,
        "emits_act": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "x108_mutation": False,
        "brody_decision": False,
    }


def evaluate(domain: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return evaluate_sigma_domain(domain, payload)
