"""
Cognitive context -> X108 dry-run admission (W2).

Closes the pipeline:
  build_cognitive_runtime_packet()
  -> context_packet_validation_projection()
  -> validate_context_packet()
  -> check_x108_context_boundary()
  -> evaluate_dry_run()  [only on PASS]
  -> DecisionTicketDryRun

No AgentResult. No AgentLayer. No new dataclass. No API route.
critical_action_requested is an explicit caller input.
evaluate_dry_run is not called on pre-gate failure.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from periphery.context.context_packet_builder_v2 import ContextPacketV2
from periphery.context.cognitive_context_to_runtime import (
    build_cognitive_runtime_packet,
    context_packet_validation_projection,
)
from periphery.context.context_packet_validator import validate_context_packet
from periphery.x108_ingress.x108_context_boundary import check_x108_context_boundary
from runtime_wiring.packet_types import DecisionTicketDryRun
from runtime_wiring.x108_admission_stub import evaluate_dry_run

_PREGATE_FAIL_CLOSED = "PREGATE_FAIL_CLOSED"
_NO_ENVELOPE = "NO_ENVELOPE_COGNITIVE_PREGATE"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pregate_ticket_id(signal_id: str) -> str:
    digest = hashlib.sha256(f"COGN_PREGATE:{signal_id}".encode()).hexdigest()[:16]
    return f"dt-cogn-pregate-{digest}"


def admit_cognitive_context(
    v2: ContextPacketV2,
    signal_id: str,
    critical_action_requested: bool = False,
) -> DecisionTicketDryRun:
    """
    Cognitive context admission pipeline (W2).

    Fail-closed: if validation or boundary fails, returns a BLOCK ticket
    without calling evaluate_dry_run.
    critical_action_requested is an explicit caller input (not derived from v2).
    """
    context = build_cognitive_runtime_packet(v2, signal_id)
    projection = context_packet_validation_projection(context)
    validation = validate_context_packet(projection)
    boundary = check_x108_context_boundary(projection)
    if not validation.valid or not boundary.passed:
        violations = list(validation.violations) + list(boundary.violations)
        ticket = DecisionTicketDryRun(
            ticket_id=_pregate_ticket_id(signal_id),
            intent_envelope_ref=_NO_ENVELOPE,
            decision="BLOCK",
            reason_codes=[_PREGATE_FAIL_CLOSED] + violations,
            x108_gate_status="X108_FAIL_CLOSED",
            timestamp_or_tick=_utcnow(),
            context_packet_refs=[context.context_id],
            notes="Pre-gate validation/boundary failed — BLOCK without evaluate_dry_run",
        )
        ticket.validate_invariants()
        return ticket

    return evaluate_dry_run(
        [context],
        critical_action_requested=critical_action_requested,
    )
