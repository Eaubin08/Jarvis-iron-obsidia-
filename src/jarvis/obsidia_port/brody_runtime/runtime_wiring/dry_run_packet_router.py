# runtime_wiring/dry_run_packet_router.py
# Dry-run packet router — validates boundaries, builds IntentEnvelope candidate,
# routes to X108 admission stub, returns (DecisionTicket, OS3Evidence)
# stdlib only — no import from apps/, periphery/, connectors/

from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from .packet_types import (
    ContextPacket,
    DecisionTicketDryRun,
    IntentEnvelope,
    OS3EvidenceTicketDryRun,
)
from .x108_admission_stub import evaluate_dry_run
from .os3_evidence_stub import build_evidence_ticket


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_intent_id(packet_ids: List[str]) -> str:
    content = "|".join(sorted(packet_ids))
    digest = hashlib.sha256(f"IE:{content}".encode()).hexdigest()[:16]
    return f"ie-dryrun-{digest}"


def _validate_all_boundaries(packets: List[ContextPacket]) -> List[str]:
    errors = []
    for pkt in packets:
        try:
            pkt.validate_invariants()
        except AssertionError as exc:
            errors.append(f"{pkt.context_id}: {exc}")
    return errors


def route_packets(
    packets: List[ContextPacket],
    critical_action_requested: bool = False,
    action_candidate_type: str = "EMIT_CONTEXT",
    source_module: str = "runtime_wiring_p8b_demo",
) -> Tuple[DecisionTicketDryRun, OS3EvidenceTicketDryRun, Optional[IntentEnvelope]]:
    """
    Main routing pipeline:

    1. Validate boundaries on all packets (fail_closed on violation).
    2. Build IntentEnvelope candidate ONLY if critical_action_requested=True.
    3. Submit to x108_admission_stub.evaluate_dry_run().
    4. Attach OS3EvidenceTicketDryRun.
    5. Return (decision_ticket, evidence_ticket, envelope_or_None).

    Never executes world action. Never produces real ALLOW.
    """
    if not packets:
        raise ValueError("route_packets: packets list cannot be empty")

    now = _utcnow()

    errors = _validate_all_boundaries(packets)
    violation_notes = "; ".join(errors) if errors else ""

    # Build IntentEnvelope only if critical action requested
    envelope: Optional[IntentEnvelope] = None
    if critical_action_requested:
        intent_id = _make_intent_id([pkt.context_id for pkt in packets])
        envelope = IntentEnvelope(
            intent_id=intent_id,
            source_module=source_module,
            source_status="SPEC_FUTURE",
            claim_scope="CLAIMABLE_SPEC_ONLY",
            action_candidate_type=action_candidate_type,
            irreversibility_level="REVERSIBLE",
            criticality_level="HIGH",
            timestamp_or_tick_context=now,
            context_packet_refs=[pkt.context_id for pkt in packets],
            requires_x108=True,
            authority="KX108_ONLY",
            emits_act=False,
            candidate_only=True,
            notes=(
                f"Dry-run IntentEnvelope candidate. critical_action_requested=True. "
                f"violations: {violation_notes or 'none'}"
            ),
        )
        envelope.validate_invariants()

    decision_ticket = evaluate_dry_run(
        packets=packets,
        envelope=envelope,
        critical_action_requested=critical_action_requested,
    )

    evidence_ticket = build_evidence_ticket(decision_ticket)

    return decision_ticket, evidence_ticket, envelope
