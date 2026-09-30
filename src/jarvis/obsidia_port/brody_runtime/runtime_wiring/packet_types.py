# runtime_wiring/packet_types.py
# Dry-run packet types — ISOLATED / stdlib only
# Distinct from periphery/common.py and periphery/context/context_packet_builder.py
# These types exist ONLY inside runtime_wiring/ and do not import from periphery/

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

VALID_DRY_RUN_DECISIONS = frozenset({"ALLOW_CONTEXT_ONLY", "HOLD", "BLOCK"})


@dataclass
class ContextPacket:
    # Required fields — no defaults, must come first
    context_id: str
    source: str
    source_status: str
    claim_scope: str
    boundary: str
    timestamp_or_tick: str
    # Optional fields with defaults
    advisory_only: bool = True
    readonly: bool = True
    runtime_allowed_now: bool = False
    emits_act: bool = False
    emits_decision: bool = False
    decision_authority: str = "KX108_ONLY"
    labels: List[str] = field(default_factory=list)
    payload: dict = field(default_factory=dict)
    notes: str = ""

    def validate_invariants(self) -> None:
        if not self.advisory_only:
            raise AssertionError("BOUNDARY_VIOLATION: advisory_only must be True")
        if not self.readonly:
            raise AssertionError("BOUNDARY_VIOLATION: readonly must be True")
        if self.emits_act:
            raise AssertionError("BOUNDARY_VIOLATION: emits_act must be False — NO_ACT_FROM_PERIPHERY")
        if self.emits_decision:
            raise AssertionError("BOUNDARY_VIOLATION: emits_decision must be False")
        if self.decision_authority != "KX108_ONLY":
            raise AssertionError("BOUNDARY_VIOLATION: decision_authority must be KX108_ONLY")
        if self.runtime_allowed_now:
            raise AssertionError("BOUNDARY_VIOLATION: runtime_allowed_now must be False in dry-run")


@dataclass
class PeripheralSignalPacket:
    # Required fields
    signal_id: str
    source: str
    source_status: str
    claim_scope: str
    boundary: str
    timestamp_or_tick: str
    # Defaults
    advisory_only: bool = True
    readonly: bool = True
    runtime_allowed_now: bool = False
    emits_act: bool = False
    emits_decision: bool = False
    decision_authority: str = "KX108_ONLY"
    signal_type: str = "ADVISORY"
    payload: dict = field(default_factory=dict)
    notes: str = ""

    def validate_invariants(self) -> None:
        if self.emits_act:
            raise AssertionError("BOUNDARY_VIOLATION: PeripheralSignalPacket cannot emit ACT")
        if self.decision_authority != "KX108_ONLY":
            raise AssertionError("BOUNDARY_VIOLATION: decision_authority must be KX108_ONLY")


@dataclass
class IntentEnvelope:
    # Required fields
    intent_id: str
    source_module: str
    source_status: str
    claim_scope: str
    action_candidate_type: str
    irreversibility_level: str
    criticality_level: str
    timestamp_or_tick_context: str
    context_packet_refs: List[str]
    # Defaults — all safety flags locked
    requires_x108: bool = True
    authority: str = "KX108_ONLY"
    emits_act: bool = False
    emits_allow: bool = False
    emits_hold: bool = False
    emits_block: bool = False
    candidate_only: bool = True
    payload: dict = field(default_factory=dict)
    notes: str = ""

    def validate_invariants(self) -> None:
        if not self.requires_x108:
            raise AssertionError("BOUNDARY_VIOLATION: requires_x108 must be True")
        if self.emits_act:
            raise AssertionError("BOUNDARY_VIOLATION: IntentEnvelope cannot emit ACT")
        if self.authority != "KX108_ONLY":
            raise AssertionError("BOUNDARY_VIOLATION: authority must be KX108_ONLY")
        if not self.candidate_only:
            raise AssertionError("BOUNDARY_VIOLATION: candidate_only must be True in dry-run")


@dataclass
class DecisionTicketDryRun:
    # Required fields
    ticket_id: str
    intent_envelope_ref: str
    decision: str
    reason_codes: List[str]
    x108_gate_status: str
    timestamp_or_tick: str
    # Defaults
    decision_priority: str = "BLOCK > HOLD > ALLOW_CONTEXT_ONLY"
    decision_authority: str = "KX108_ONLY"
    emits_act: bool = False
    input_hash: str = "NOT_COMPUTED_DRY_RUN"
    output_hash: str = "NOT_COMPUTED_DRY_RUN"
    trace_hash: str = "NOT_COMPUTED_DRY_RUN"
    merkle_root: str = "NOT_COMPUTED_DRY_RUN"
    replay_status: str = "NOT_RUN"
    tau_status: str = "NOT_APPLICABLE_DRY_RUN"
    irreversibility_status: str = "REVERSIBLE"
    context_packet_refs: List[str] = field(default_factory=list)
    evidence_ticket_refs: List[str] = field(default_factory=list)
    dry_run: bool = True
    notes: str = ""

    def validate_invariants(self) -> None:
        if self.decision not in VALID_DRY_RUN_DECISIONS:
            raise AssertionError(
                f"BOUNDARY_VIOLATION: decision '{self.decision}' not in {VALID_DRY_RUN_DECISIONS}"
            )
        if self.emits_act:
            raise AssertionError("BOUNDARY_VIOLATION: DecisionTicketDryRun cannot emit ACT")
        if self.decision_authority != "KX108_ONLY":
            raise AssertionError("BOUNDARY_VIOLATION: decision_authority must be KX108_ONLY")
        if not self.dry_run:
            raise AssertionError("BOUNDARY_VIOLATION: dry_run flag must be True")


@dataclass
class OS3EvidenceTicketDryRun:
    # Required fields
    evidence_id: str
    linked_decision_ticket: str
    source: str
    timestamp_or_tick: str
    # Defaults — honest dry-run placeholders
    evidence_type: str = "HASH_CHAIN"
    verification_status: str = "NOT_VERIFIED_DRY_RUN"
    hash_status: str = "NOT_COMPUTED"
    seal_status: str = "NOT_SEALED"
    merkle_status: str = "NOT_BUILT"
    replay_status: str = "NOT_RUN"
    proof_claim: bool = False
    claim_scope: str = "CLAIMABLE_SPEC_ONLY"
    rfc3161_anchor_ref: str = "NOT_ANCHORED_DRY_RUN"
    dry_run: bool = True
    notes: str = ""

    def validate_invariants(self) -> None:
        if self.proof_claim:
            raise AssertionError("BOUNDARY_VIOLATION: proof_claim must be False in dry-run")
        if self.verification_status == "VERIFIED":
            raise AssertionError(
                "BOUNDARY_VIOLATION: verification_status cannot be VERIFIED in dry-run"
            )
        if not self.dry_run:
            raise AssertionError("BOUNDARY_VIOLATION: dry_run flag must be True")
