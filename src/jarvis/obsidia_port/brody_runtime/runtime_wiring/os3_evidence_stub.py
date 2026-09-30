# runtime_wiring/os3_evidence_stub.py
# OS3 evidence stub — dry-run only, purely probatory
# All hash/seal/merkle statuses = NOT_COMPUTED (honest dry-run)
# Never sets proof_claim=True, never sets verification_status=VERIFIED
# stdlib only

from __future__ import annotations
import hashlib
from datetime import datetime, timezone

from .packet_types import DecisionTicketDryRun, OS3EvidenceTicketDryRun


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_evidence_id(decision_ticket_id: str, timestamp: str) -> str:
    content = f"OS3:{decision_ticket_id}|{timestamp}"
    digest = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"os3-dryrun-{digest}"


def build_evidence_ticket(decision_ticket: DecisionTicketDryRun) -> OS3EvidenceTicketDryRun:
    """
    Create an OS3EvidenceTicketDryRun attached to a DecisionTicketDryRun.

    Honest about dry-run status: all hash/seal/merkle fields are NOT_COMPUTED.
    proof_claim is always False.
    """
    now = _utcnow()
    evidence_id = _make_evidence_id(decision_ticket.ticket_id, now)

    evidence = OS3EvidenceTicketDryRun(
        evidence_id=evidence_id,
        linked_decision_ticket=decision_ticket.ticket_id,
        source="runtime_wiring/os3_evidence_stub.py",
        timestamp_or_tick=now,
        evidence_type="HASH_CHAIN",
        verification_status="NOT_VERIFIED_DRY_RUN",
        hash_status="NOT_COMPUTED",
        seal_status="NOT_SEALED",
        merkle_status="NOT_BUILT",
        replay_status="NOT_RUN",
        proof_claim=False,
        claim_scope="CLAIMABLE_SPEC_ONLY",
        rfc3161_anchor_ref="NOT_ANCHORED_DRY_RUN",
        dry_run=True,
        notes=(
            "Dry-run evidence stub. No real hash chain. No merkle seal. "
            "RFC3161 anchor pending P5. verification_status deliberately NOT_VERIFIED_DRY_RUN."
        ),
    )
    evidence.validate_invariants()
    return evidence
