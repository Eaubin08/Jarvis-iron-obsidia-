"""Brody native machination composer.

Phase 11B.

Aggregates existing Brody runtime snapshots, contracts, and OS Trad / IR /
OS Reverse support evidence into a single native payload for /api/brody/chat.

This module is readonly/advisory only. It does not decide, act, write memory,
write or promote memory, mutate the kernel, or mutate X108.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from apps.obsidia_api.brody_contracts_packet import (
    BOUNDARY_CONTRACT,
    build_brody_contracts_packet,
)

try:
    from apps.obsidia_api.routes.os_trad_ir_reverse import (
        _alphabet_units,
        _constraints,
        _detect_language,
        _intent,
        _risk_flags,
    )
except Exception:  # pragma: no cover
    _alphabet_units = None
    _constraints = None
    _detect_language = None
    _intent = None
    _risk_flags = None

try:
    from apps.obsidia_api.brody_domain_raccord_adapter import (
        adjust_risk_flags,
        build_domain_raccord_snapshot,
    )
except Exception:  # pragma: no cover
    adjust_risk_flags = None
    build_domain_raccord_snapshot = None


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_flags(text: str) -> list[str]:
    def canonicalize(raw_flags: list[str]) -> list[str]:
        canonical: list[str] = []
        specialized_write_seen = False

        for raw_flag in raw_flags:
            flag = str(raw_flag)

            if (
                flag.endswith("_write_request")
                and flag not in {
                    "write_request",
                    "memory_write_request",
                }
            ):
                specialized_write_seen = True
                continue

            if flag not in canonical:
                canonical.append(flag)

        if specialized_write_seen:
            for flag in (
                "write_request",
                "memory_write_request",
            ):
                if flag not in canonical:
                    canonical.append(flag)

        try:
            from apps.obsidia_api.brody_domain_raccord_adapter import (
                has_memory_write_request,
            )

            if has_memory_write_request(text):
                for flag in (
                    "write_request",
                    "memory_write_request",
                ):
                    if flag not in canonical:
                        canonical.append(flag)

        except Exception:
            pass

        return canonical

    if _risk_flags:
        try:
            flags = list(
                _risk_flags(text)
            )

            if adjust_risk_flags:
                flags = list(
                    adjust_risk_flags(
                        text,
                        flags,
                    )
                )

            return canonicalize(
                flags
            )

        except Exception:
            pass

    low = (
        text
        or ""
    ).lower()

    flags: list[str] = []

    if any(
        token in low
        for token in (
            "autorise",
            "authorize",
            "cr?ateur",
            "createur",
            "admin",
            "root",
        )
    ):
        flags.append(
            "authority_claim"
        )

    if any(
        token in low
        for token in (
            "act",
            "agir",
            "execute",
            "ex?cute",
            "lance",
            "write",
        )
    ):
        flags.append(
            "action_request"
        )

    if any(
        token in low
        for token in (
            "kernel",
            "x108",
            "mutation",
            "modifie",
            "modify",
            "patch",
        )
    ):
        flags.append(
            "mutation_request"
        )

    if any(
        token in low
        for token in (
            "pytest",
            "traceback",
            "exception",
            "bug",
            "debug",
            "powershell",
        )
    ):
        flags.append(
            "code_debug"
        )

    if adjust_risk_flags:
        flags = list(
            adjust_risk_flags(
                text,
                flags,
            )
        )

    return canonicalize(
        flags
    )


def _safe_language(text: str, requested: str) -> str:
    if _detect_language:
        try:
            detected = _detect_language(text, requested)
            if detected:
                return str(detected)
        except Exception:
            pass
    return requested if requested in ("fr", "en") else "unknown"


def _safe_intent(text: str, flags: list[str]) -> str:
    if _intent:
        try:
            return str(_intent(text, flags))
        except Exception:
            pass
    if "code_debug" in flags:
        return "code_debug"
    if "authority_claim" in flags:
        return "authority_claim"
    if any(flag in flags for flag in ("write_request", "memory_write_request", "canon_promotion_request")):
        return "write_request"
    if "action_request" in flags:
        return "action_request"
    if "?" in text or "comment" in text.lower() or "pourquoi" in text.lower() or "explique" in text.lower():
        return "question"
    return "unknown"


def _safe_constraints(flags: list[str]) -> list[str]:
    if _constraints:
        try:
            return list(_constraints(flags))
        except Exception:
            pass

    values = [
        "READONLY",
        "ADVISORY_ONLY",
        "NO_ACT",
        "NO_VERDICT",
        "NO_MEMORY_WRITE",
        "NO_KERNEL_MUTATION",
        "NO_X108_MUTATION",
        "DECISION_AUTHORITY_KX108_ONLY",
    ]
    if any(flag in flags for flag in ("action_request", "mutation_request", "write_request", "memory_write_request", "canon_promotion_request")):
        values.append("ACTION_REQUEST_FORCED_TO_READONLY_PROJECTION")
    return values


def _safe_alphabet_units(text: str, detected_language: str, flags: list[str]) -> list[dict[str, Any]]:
    if _alphabet_units:
        try:
            return list(_alphabet_units(text, detected_language, flags))
        except Exception:
            pass

    units: list[dict[str, Any]] = [
        {"kind": "language", "value": detected_language, "source": "BRODY_NATIVE_COMPOSER"},
        {"kind": "boundary", "value": "KX108_ONLY", "source": "BRODY_NATIVE_COMPOSER"},
        {"kind": "readonly", "value": True, "source": "BRODY_NATIVE_COMPOSER"},
    ]
    for flag in flags:
        units.append({"kind": "risk_flag", "value": flag, "source": "BRODY_NATIVE_COMPOSER"})
    return units


def build_support_routes(
    user_message: str,
    language: str = "auto",
    session_id: str = "local",
    tree_context: dict[str, Any] | None = None,
    memory_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build support routes evidence without HTTP roundtrip."""
    text = user_message or ""
    detected_language = _safe_language(text, language or "auto")
    flags = _safe_flags(text)
    constraints = _safe_constraints(flags)
    alphabet_units = _safe_alphabet_units(text, detected_language, flags)
    intent = _safe_intent(text, flags)

    tree_ctx = _as_dict(tree_context)
    memory_ctx = _as_dict(memory_context)

    contradictions: list[str] = []
    if any(flag in flags for flag in ("write_request", "memory_write_request", "canon_promotion_request")):
        contradictions.append("REQUEST_REQUIRES_WRITE_BUT_ROUTE_IS_READONLY")
    if any(flag in flags for flag in ("action_request", "mutation_request")):
        contradictions.append("REQUEST_REQUIRES_ACTION_BUT_ROUTE_IS_READONLY")

    domain_raccord = build_domain_raccord_snapshot(text) if build_domain_raccord_snapshot else {
        "source": "BRODY_DOMAIN_RACCORD_ADAPTER_UNAVAILABLE",
        "status": "UNAVAILABLE",
        "domains": [],
    }

    os_trad = {
        **BOUNDARY_CONTRACT,
        "source": "BRODY_NATIVE_COMPOSER",
        "route": "/api/os-trad/translate",
        "detected_language": detected_language,
        "alphabet_units": alphabet_units,
        "constraints": constraints,
        "risk_flags": flags,
        "tree_context": tree_ctx or {
            "enabled": True,
            "source": "/api/periphery/cognitive/trees",
            "mode": "readonly_context",
        },
        "memory_context": memory_ctx,
        "session_id": session_id,
        "domain_raccord": domain_raccord,
    }

    ir_candidate = {
        **BOUNDARY_CONTRACT,
        "source": "BRODY_NATIVE_COMPOSER",
        "route": "/api/ir/candidate",
        "ir_candidate": {
            "intent": intent,
            "intent_type": intent,
            "risk_flags": flags,
            "contradictions": contradictions,
            "constraints": constraints,
            "alphabet_units_count": len(alphabet_units),
            "tree_refs": [],
            "memory_refs": [],
            "allowed_to_decide": False,
            "allowed_to_act": False,
            "memory_write": False,
            "kernel_mutation": False,
            "x108_mutation": False,
            "decision_authority": "KX108_ONLY",
            "domain_raccord": domain_raccord,
        },
        "session_id": session_id,
    }

    os_reverse = {
        **BOUNDARY_CONTRACT,
        "source": "BRODY_NATIVE_COMPOSER",
        "route": "/api/os-reverse/project",
        "projection": {
            "response_mode": "readonly_projection",
            "summary": "Projection readonly générée. Aucune action, aucun verdict, aucune écriture mémoire ni promotion canonique, aucune mutation kernel ou X108.",
            "next_safe_step": "inspect_trace_or_call_brody_chat",
            "boundary_notice": "KX108_ONLY",
            "intent": intent,
            "risk_flags": flags,
            "contradictions": contradictions,
            "domain_raccord": domain_raccord,
        },
        "session_id": session_id,
    }

    return {
        "source": "REAL_BACKEND_SUPPORT_NATIVE",
        "status": "SUPPORT_ROUTES_COMPOSED",
        "domain_raccord_snapshot": domain_raccord,
        "os_trad": os_trad,
        "ir_candidate": ir_candidate,
        "os_reverse": os_reverse,
        **BOUNDARY_CONTRACT,
    }


def build_support_summary(support_routes: dict[str, Any]) -> dict[str, Any]:
    os_trad = _as_dict(support_routes.get("os_trad"))
    ir = _as_dict(support_routes.get("ir_candidate"))
    irc = _as_dict(ir.get("ir_candidate"))
    rev = _as_dict(support_routes.get("os_reverse"))
    proj = _as_dict(rev.get("projection"))
    domain_raccord = _as_dict(support_routes.get("domain_raccord_snapshot")) or _as_dict(os_trad.get("domain_raccord"))

    return {
        "source": "BRODY_NATIVE_SUPPORT_SUMMARY_V1",
        "detected_language": os_trad.get("detected_language", "unknown"),
        "intent": irc.get("intent", irc.get("intent_type", "unknown")),
        "risk_flags": _as_list(os_trad.get("risk_flags")) or _as_list(irc.get("risk_flags")),
        "contradictions": _as_list(irc.get("contradictions")),
        "constraints": _as_list(os_trad.get("constraints")) or _as_list(irc.get("constraints")),
        "projection_mode": proj.get("response_mode", "readonly_projection"),
        "next_safe_step": proj.get("next_safe_step", "inspect_trace_or_call_brody_chat"),
        "boundary_notice": proj.get("boundary_notice", "KX108_ONLY"),
        "domain_raccord_snapshot": domain_raccord,
        "domain_raccord_domains": _as_list(domain_raccord.get("domains")),
        "domain_voice_mode": domain_raccord.get("voice_mode"),
        "negation_guard_active": bool(domain_raccord.get("negation_guard_active")),
        "write_boundary_required": bool(domain_raccord.get("write_boundary_required")),
        **BOUNDARY_CONTRACT,
    }


def build_machination_packet(
    *,
    user_message: str,
    language: str,
    session_id: str,
    source: str,
    authority_snapshot: dict[str, Any],
    automation_snapshot: dict[str, Any],
    semantic_query_snapshot: dict[str, Any],
    memory_response_chain_snapshot: dict[str, Any],
    project_memory_snapshot: dict[str, Any],
    session_memory_snapshot: dict[str, Any],
    candidate_memory_snapshot: dict[str, Any],
    operator_loop_snapshot: dict[str, Any],
    tree_policy_snapshot: dict[str, Any],
    temporal_context_snapshot: dict[str, Any],
    cognitive_modules_snapshot: dict[str, Any],
    runtime_context: dict[str, Any],
    context_packet: dict[str, Any],
    translation_trace: dict[str, Any],
    ir_candidate_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Build full native machination packet for /api/brody/chat."""
    contracts = build_brody_contracts_packet(user_message, authority_snapshot)

    support_routes = build_support_routes(
        user_message=user_message,
        language=language or "auto",
        session_id=session_id or "local",
        tree_context=tree_policy_snapshot,
        memory_context=memory_response_chain_snapshot,
    )
    support_summary = build_support_summary(support_routes)

    packet = {
        "source": "BRODY_NATIVE_MACHINATION_PACKET_V1",
        "status": "MACHINATION_PACKET_READY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session": {
            "session_id": session_id or "local",
            "language": language,
            "backend_source": source,
            "mode": "readonly",
        },
        "contracts": contracts,
        "authority_snapshot": authority_snapshot,
        "automation_snapshot": automation_snapshot,
        "semantic_query_snapshot": semantic_query_snapshot,
        "memory_response_chain_snapshot": memory_response_chain_snapshot,
        "project_memory_snapshot": project_memory_snapshot,
        "session_memory_snapshot": session_memory_snapshot,
        "candidate_memory_snapshot": candidate_memory_snapshot,
        "operator_loop_snapshot": operator_loop_snapshot,
        "tree_policy_snapshot": tree_policy_snapshot,
        "temporal_context_snapshot": temporal_context_snapshot,
        "cognitive_modules_snapshot": cognitive_modules_snapshot,
        "runtime_context": runtime_context,
        "context_packet": context_packet,
        "translation_trace": translation_trace,
        "ir_candidate_snapshot": ir_candidate_snapshot,
        "support_routes": support_routes,
        "support_summary": support_summary,
        "domain_raccord_snapshot": support_routes.get("domain_raccord_snapshot"),
        **BOUNDARY_CONTRACT,
    }

    return packet
