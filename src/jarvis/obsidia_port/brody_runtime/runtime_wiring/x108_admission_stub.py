# runtime_wiring/x108_admission_stub.py
# X108 admission stub — deterministic, dry-run only
# Priority: BLOCK > HOLD > ALLOW_CONTEXT_ONLY (aggregate4_fail_closed)
# Never emits ACT. No real proof chain.
# stdlib only — no import from apps/, periphery/, connectors/

from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from typing import List, Optional

from .packet_types import (
    ContextPacket,
    DecisionTicketDryRun,
    IntentEnvelope,
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_ticket_id(envelope_ref: str) -> str:
    digest = hashlib.sha256(f"DT:{envelope_ref}".encode()).hexdigest()[:16]
    return f"dt-dryrun-{digest}"


def _detect_boundary_violations(packets: List[ContextPacket]) -> List[str]:
    violations = []
    for pkt in packets:
        if pkt.emits_act:
            violations.append(f"VIOLATION:emits_act_true:{pkt.context_id}")
        if pkt.emits_decision:
            violations.append(f"VIOLATION:emits_decision_true:{pkt.context_id}")
        if pkt.decision_authority != "KX108_ONLY":
            violations.append(f"VIOLATION:bad_decision_authority:{pkt.context_id}")
        if not pkt.advisory_only:
            violations.append(f"VIOLATION:advisory_only_false:{pkt.context_id}")
        if not pkt.readonly:
            violations.append(f"VIOLATION:readonly_false:{pkt.context_id}")
        if pkt.runtime_allowed_now:
            violations.append(f"VIOLATION:runtime_allowed_now_true:{pkt.context_id}")
    return violations


def evaluate_dry_run(
    packets: List[ContextPacket],
    envelope: Optional[IntentEnvelope] = None,
    critical_action_requested: bool = False,
) -> DecisionTicketDryRun:
    """
    X108 admission stub — deterministic decision (BLOCK > HOLD > ALLOW_CONTEXT_ONLY).

    Rule 1: boundary violation on any packet → BLOCK
    Rule 2: critical_action_requested=True → HOLD
    Rule 3/4: otherwise → ALLOW_CONTEXT_ONLY

    Never returns ACT. Never a real ALLOW.
    """
    now = _utcnow()
    envelope_ref = envelope.intent_id if envelope else "NO_ENVELOPE_DRY_RUN"
    ticket_id = _make_ticket_id(envelope_ref)
    context_refs = [pkt.context_id for pkt in packets]

    # Rule 1: boundary violations → BLOCK
    violations = _detect_boundary_violations(packets)
    if violations:
        ticket = DecisionTicketDryRun(
            ticket_id=ticket_id,
            intent_envelope_ref=envelope_ref,
            decision="BLOCK",
            reason_codes=["BOUNDARY_VIOLATION"] + violations,
            x108_gate_status="X108_FAIL_CLOSED",
            timestamp_or_tick=now,
            context_packet_refs=context_refs,
            notes="Boundary violation detected — fail_closed → BLOCK",
        )
        ticket.validate_invariants()
        return ticket

    # Rule 2: critical action requested → HOLD
    if critical_action_requested:
        reason = ["CRITICAL_ACTION_REQUIRES_HOLD", "DRY_RUN_NO_REAL_GATE"]
        if envelope:
            reason.append(f"INTENT:{envelope.action_candidate_type}:{envelope.criticality_level}")
        ticket = DecisionTicketDryRun(
            ticket_id=ticket_id,
            intent_envelope_ref=envelope_ref,
            decision="HOLD",
            reason_codes=reason,
            x108_gate_status="X108_EVALUATED_DRY_RUN",
            timestamp_or_tick=now,
            context_packet_refs=context_refs,
            notes="Critical action → HOLD. X108 gate required before any real execution.",
        )
        ticket.validate_invariants()
        return ticket

    # Rule 3 & 4: ALLOW_CONTEXT_ONLY
    reason = ["CONTEXT_ADVISORY_ONLY", "NO_CRITICAL_ACTION", "DRY_RUN_READONLY"]
    if envelope:
        reason.append(f"INTENT:{envelope.action_candidate_type}")
    ticket = DecisionTicketDryRun(
        ticket_id=ticket_id,
        intent_envelope_ref=envelope_ref,
        decision="ALLOW_CONTEXT_ONLY",
        reason_codes=reason,
        x108_gate_status="X108_EVALUATED_DRY_RUN",
        timestamp_or_tick=now,
        context_packet_refs=context_refs,
        notes="Context advisory acknowledged. ALLOW_CONTEXT_ONLY — no world action, no real ALLOW.",
    )
    ticket.validate_invariants()
    return ticket
