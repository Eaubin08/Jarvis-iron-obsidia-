"""
Canonical AgentResult -> runtime ContextPacket adapter.

Purpose:
    Bind an already-produced non-sovereign AgentResult to the existing
    runtime_wiring ContextPacket dry-run path.

This adapter:
- does not decide;
- does not emit ACT;
- does not authorize execution;
- does not mutate the kernel;
- does not write memory;
- does not enable runtime execution;
- preserves AgentResult provenance and peripheral signals.

decision_authority remains KX108_ONLY.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from periphery.agent_contracts import AgentResult
from runtime_wiring.packet_types import ContextPacket


BOUNDARY = "AGENT_RESULT_CONTEXT_ADVISORY_ONLY"
SOURCE_STATUS = "RUNTIME_AGENT_RESULT_READONLY"
CLAIM_SCOPE = "RUNTIME_CONTEXT_ONLY"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_payload(result: AgentResult) -> dict[str, Any]:
    packet = result.packet

    return {
        "agent_id": result.agent_id,
        "agent_layer": result.layer.value,
        "action_id": packet.action_id,
        "domain": packet.domain,
        "extra_metrics": dict(packet.extra_metrics),
        "unknowns": list(packet.unknowns),
        "risk_flags": list(packet.risk_flags),
        "contradictions": list(packet.contradictions),
        "evidence_refs": list(packet.evidence_refs),
        "recommended_gate": packet.recommended_gate,
        "agent_notes": list(result.notes),
        "agent_can_emit_act": packet.can_emit_act,
        "_agent_result_bound": True,
        "_context_signal_only": True,
        "_allowed_to_decide": False,
        "_allowed_to_act": False,
        "_memory_write": False,
        "_kernel_mutation": False,
        "_boundary": BOUNDARY,
        "_dry_run": True,
    }


def _make_context_id(result: AgentResult) -> str:
    payload = _canonical_payload(result)

    encoded = json.dumps(
        payload,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")

    digest = hashlib.sha256(encoded).hexdigest()[:20]

    return f"cp-agent-{digest}"


def agent_result_to_context_packet(
    result: AgentResult,
) -> ContextPacket:
    """
    Convert one non-sovereign AgentResult into the canonical runtime
    ContextPacket used by the existing X108 dry-run admission path.

    Fail closed if the source AgentResult violates peripheral sovereignty.
    """
    if not isinstance(result, AgentResult):
        raise TypeError("AGENT_RESULT_REQUIRED")

    result.assert_non_sovereign()

    packet = result.packet

    if not result.agent_id:
        raise ValueError("AGENT_RESULT_MISSING_AGENT_ID")

    if not packet.action_id:
        raise ValueError("AGENT_RESULT_MISSING_ACTION_ID")

    if not packet.domain:
        raise ValueError("AGENT_RESULT_MISSING_DOMAIN")

    context = ContextPacket(
        context_id=_make_context_id(result),
        source=f"agent:{result.agent_id}",
        source_status=SOURCE_STATUS,
        claim_scope=CLAIM_SCOPE,
        boundary=BOUNDARY,
        timestamp_or_tick=_utcnow(),
        advisory_only=True,
        readonly=True,
        runtime_allowed_now=False,
        emits_act=False,
        emits_decision=False,
        decision_authority="KX108_ONLY",
        labels=[
            "AGENT_RESULT",
            "NON_SOVEREIGN",
            "READONLY_CONTEXT",
            f"AGENT_LAYER:{result.layer.value}",
        ],
        payload=_canonical_payload(result),
        notes=(
            "Canonical AgentResult -> ContextPacket binding. "
            "Context-only dry-run path; KX108_ONLY."
        ),
    )

    context.validate_invariants()

    return context


def context_packet_validation_projection(
    context: ContextPacket,
) -> dict[str, Any]:
    """
    Project the runtime ContextPacket onto the existing context sovereignty
    validator/boundary schema.

    This does not create another authority-bearing packet.
    """
    context.validate_invariants()

    action_id = context.payload.get("action_id")

    return {
        "packet_id": context.context_id,
        "action_id": action_id,
        "readonly": context.readonly,
        "context_signal_only": True,
        "decision_authority": context.decision_authority,
        "allowed_to_decide": False,
        "allowed_to_act": False,
        "kernel_mutation": False,
        "memory_write": False,
        "emits_act": context.emits_act,
        "emits_decision": context.emits_decision,
        "runtime_allowed_now": context.runtime_allowed_now,
        "boundary": context.boundary,
        "source": context.source,
    }
