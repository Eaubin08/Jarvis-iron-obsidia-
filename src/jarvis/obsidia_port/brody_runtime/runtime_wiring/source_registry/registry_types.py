# runtime_wiring/source_registry/registry_types.py
# SourceFileRegistryEntry dataclass — stdlib only
# No zip extraction. No source pack import. No runtime activation.

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict

# Allowed adapter targets (must match source_adapters.py function names)
VALID_ADAPTER_TARGETS = frozenset({
    "cognitive_to_context_packet",
    "rssi_rgpd_to_context_packet",
    "atlas_to_context_packet",
    "compliance_to_context_packet",
    # P24 — new families
    "rssi_security_to_context_packet",
    "external_signals_to_context_packet",
    "npl_to_context_packet",
    # P32 — 8th family
    "os_trad_reverse_to_context_packet",
    # P35 — OS_TRAD interlanguage canon extension
    "reverse_os_interlanguage_to_context_packet",
    "UNKNOWN_NO_ADAPTER",
})

# Allowed packet targets
VALID_PACKET_TARGETS = frozenset({
    "ContextPacket",
    "ContextPacket|OS3EvidenceTicketDryRun_ref",
    "NONE",
})

# Decisions that require DO_NOT_IMPORT_RUNTIME enforcement
DO_NOT_IMPORT_DECISIONS = frozenset({
    "DO_NOT_IMPORT_RUNTIME",
    "ARCHIVE_ONLY",
    "KEEP_QUARANTINE",
    "KEEP_SOURCE_ONLY",
})

# Quarantine status values
QUARANTINE_STATUSES = frozenset({
    "CLEAR",
    "QUARANTINE",
    "QUARANTINE_CACHE",
    "DO_NOT_IMPORT_RUNTIME",
    "ARCHIVE_ONLY",
    "UNKNOWN",
})


@dataclass
class SourceFileRegistryEntry:
    # Identity
    registry_id: str
    source_family: str
    source_zip: str
    internal_path: str
    file_name: str
    extension: str
    size_bytes: int

    # Decision
    recommended_decision: str
    boundary_required: str
    claim_scope: str
    quarantine_status: str

    # Adapter wiring
    adapter_target: str
    packet_target: str

    # Safety invariants — always False
    runtime_allowed_now: bool = False
    emits_act: bool = False
    emits_decision: bool = False

    # Source status
    source_status: str = "COPIED_READONLY"

    # Subfamily — extension/subspecification within a family (optional, P35+)
    source_subfamily: str = ""

    # Metadata
    notes: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def validate_invariants(self) -> None:
        if self.runtime_allowed_now:
            raise AssertionError(
                f"REGISTRY_VIOLATION: runtime_allowed_now=True on {self.registry_id}"
            )
        if self.emits_act:
            raise AssertionError(
                f"REGISTRY_VIOLATION: emits_act=True on {self.registry_id}"
            )
        if self.emits_decision:
            raise AssertionError(
                f"REGISTRY_VIOLATION: emits_decision=True on {self.registry_id}"
            )
        if self.adapter_target not in VALID_ADAPTER_TARGETS:
            raise AssertionError(
                f"REGISTRY_VIOLATION: invalid adapter_target '{self.adapter_target}' on {self.registry_id}"
            )
        if self.packet_target not in VALID_PACKET_TARGETS:
            raise AssertionError(
                f"REGISTRY_VIOLATION: invalid packet_target '{self.packet_target}' on {self.registry_id}"
            )
        if self.extension == ".py" and "DO_NOT_IMPORT_RUNTIME" not in self.recommended_decision:
            raise AssertionError(
                f"REGISTRY_VIOLATION: .py file without DO_NOT_IMPORT_RUNTIME on {self.registry_id}: {self.recommended_decision}"
            )
        if self.recommended_decision in DO_NOT_IMPORT_DECISIONS and self.quarantine_status == "CLEAR":
            raise AssertionError(
                f"REGISTRY_VIOLATION: decision={self.recommended_decision} but quarantine_status=CLEAR on {self.registry_id}"
            )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("extra", None)
        return d

    def to_csv_row(self) -> Dict[str, Any]:
        return {
            "registry_id": self.registry_id,
            "source_family": self.source_family,
            "source_zip": self.source_zip,
            "internal_path": self.internal_path,
            "file_name": self.file_name,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "recommended_decision": self.recommended_decision,
            "boundary_required": self.boundary_required,
            "claim_scope": self.claim_scope,
            "quarantine_status": self.quarantine_status,
            "adapter_target": self.adapter_target,
            "packet_target": self.packet_target,
            "runtime_allowed_now": self.runtime_allowed_now,
            "emits_act": self.emits_act,
            "emits_decision": self.emits_decision,
            "source_status": self.source_status,
            "source_subfamily": self.source_subfamily,
            "notes": self.notes,
        }
