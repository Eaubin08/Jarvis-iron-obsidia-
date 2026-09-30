# runtime_wiring/source_registry/registry_to_adapter_dry_run.py
# Registry-to-Adapter dry-run router — P9B
# Converts SourceFileRegistryEntry metadata → ContextPacket (dry-run)
# WITHOUT reading any file from zip_path or internal_path.
# Stdlib only. No zip extraction. No source pack import. No runtime activation.

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from runtime_wiring.source_registry.registry_types import (
    SourceFileRegistryEntry,
    DO_NOT_IMPORT_DECISIONS,
)
from runtime_wiring.source_adapters import (
    cognitive_to_context_packet,
    rssi_rgpd_to_context_packet,
    atlas_to_context_packet,
    compliance_to_context_packet,
    # P24 — new families
    rssi_security_to_context_packet,
    external_signals_to_context_packet,
    npl_to_context_packet,
    # P32 — 8th family
    os_trad_reverse_to_context_packet,
    # P35 — OS_TRAD interlanguage canon extension
    reverse_os_interlanguage_to_context_packet,
)
from runtime_wiring.packet_types import ContextPacket
from runtime_wiring.dry_run_packet_router import route_packets
from runtime_wiring.packet_types import DecisionTicketDryRun, OS3EvidenceTicketDryRun

# Decisions that are never routable
_FORBIDDEN_DECISIONS = frozenset({
    "DO_NOT_IMPORT_RUNTIME",
    "ARCHIVE_ONLY",
    "KEEP_QUARANTINE",
    "KEEP_SOURCE_ONLY",
})

# Quarantine statuses that are never routable
_FORBIDDEN_QUARANTINE = frozenset({
    "DO_NOT_IMPORT_RUNTIME",
    "ARCHIVE_ONLY",
    "QUARANTINE",
    "QUARANTINE_CACHE",
})

# Adapter dispatch table — name matches source_adapters.py functions
_ADAPTER_DISPATCH = {
    "cognitive_to_context_packet": cognitive_to_context_packet,
    "rssi_rgpd_to_context_packet": rssi_rgpd_to_context_packet,
    "atlas_to_context_packet": atlas_to_context_packet,
    "compliance_to_context_packet": compliance_to_context_packet,
    # P24 — new families
    "rssi_security_to_context_packet": rssi_security_to_context_packet,
    "external_signals_to_context_packet": external_signals_to_context_packet,
    "npl_to_context_packet": npl_to_context_packet,
    # P32 — 8th family
    "os_trad_reverse_to_context_packet": os_trad_reverse_to_context_packet,
    # P35 — OS_TRAD interlanguage canon extension
    "reverse_os_interlanguage_to_context_packet": reverse_os_interlanguage_to_context_packet,
}


def _is_forbidden(entry: SourceFileRegistryEntry) -> Tuple[bool, str]:
    """Return (True, reason) if this entry must never be routed."""
    if entry.recommended_decision in _FORBIDDEN_DECISIONS:
        return True, f"forbidden_decision:{entry.recommended_decision}"
    if entry.quarantine_status in _FORBIDDEN_QUARANTINE:
        return True, f"forbidden_quarantine:{entry.quarantine_status}"
    if entry.runtime_allowed_now:
        return True, "runtime_allowed_now:True"
    if entry.emits_act:
        return True, "emits_act:True"
    if entry.emits_decision:
        return True, "emits_decision:True"
    if entry.extension.lower() == ".py":
        return True, "py_file:DO_NOT_IMPORT_RUNTIME"
    if entry.adapter_target not in _ADAPTER_DISPATCH:
        return True, f"no_adapter:{entry.adapter_target}"
    return False, ""


def reject_forbidden_entries(
    entries: List[SourceFileRegistryEntry],
) -> Tuple[List[SourceFileRegistryEntry], List[Dict[str, str]]]:
    """
    Partition entries into (routable, rejected).
    Returns (routable_list, rejected_list_with_reasons).
    """
    routable = []
    rejected = []
    for entry in entries:
        forbidden, reason = _is_forbidden(entry)
        if forbidden:
            rejected.append({"registry_id": entry.registry_id, "reason": reason})
        else:
            routable.append(entry)
    return routable, rejected


def select_routable_entries(
    entries: List[SourceFileRegistryEntry],
    family: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[SourceFileRegistryEntry]:
    """
    Return routable entries, optionally filtered by family and limited in count.
    Never returns forbidden entries.
    """
    routable, _ = reject_forbidden_entries(entries)
    if family is not None:
        routable = [e for e in routable if e.source_family == family]
    if limit is not None:
        routable = routable[:limit]
    return routable


def entry_to_metadata(entry: SourceFileRegistryEntry) -> Dict[str, Any]:
    """
    Convert a SourceFileRegistryEntry to a metadata dict suitable for source adapters.
    Uses ONLY registry metadata — never reads zip_path or internal_path content.
    """
    return {
        "registry_id": entry.registry_id,
        "source_family": entry.source_family,
        "source_zip": entry.source_zip,
        "file_name": entry.file_name,
        "extension": entry.extension,
        "size_bytes": entry.size_bytes,
        "recommended_decision": entry.recommended_decision,
        "boundary_required": entry.boundary_required,
        "claim_scope": entry.claim_scope,
        "quarantine_status": entry.quarantine_status,
        "adapter_target": entry.adapter_target,
        "source_status": entry.source_status,
        # Explicitly NOT including zip_path or internal_path content
        # Only the path string as a reference label, never opened or extracted
        "internal_path_label": entry.internal_path,
        "_zip_extraction": False,
        "_source_pack_import": False,
        "_runtime_allowed_now": False,
        "notes": entry.notes,
    }


def route_entry_to_context_packet(entry: SourceFileRegistryEntry) -> ContextPacket:
    """
    Convert a single routable SourceFileRegistryEntry to a ContextPacket dry-run.

    Raises ValueError if the entry is forbidden.
    Raises KeyError if the adapter_target is not in the dispatch table.
    Never reads zip content. Uses only registry metadata.
    """
    forbidden, reason = _is_forbidden(entry)
    if forbidden:
        raise ValueError(f"ROUTING_REFUSED: entry {entry.registry_id} is forbidden ({reason})")

    adapter_fn = _ADAPTER_DISPATCH[entry.adapter_target]
    metadata = entry_to_metadata(entry)
    return adapter_fn(metadata)


def route_sample_by_family(
    entries: List[SourceFileRegistryEntry],
    sample_size: int = 1,
) -> Dict[str, List[ContextPacket]]:
    """
    Route sample_size routable entries per family to ContextPacket.
    Returns {family: [ContextPacket, ...]}
    """
    result: Dict[str, List[ContextPacket]] = {}
    families = {e.source_family for e in entries}

    for family in sorted(families):
        sample = select_routable_entries(entries, family=family, limit=sample_size)
        packets = []
        for entry in sample:
            try:
                pkt = route_entry_to_context_packet(entry)
                packets.append(pkt)
            except Exception as exc:
                # Log but do not crash — other families still routed
                packets.append(None)  # type: ignore[arg-type]
        result[family] = [p for p in packets if p is not None]

    return result


def route_registry_packets_to_x108(
    entries: List[SourceFileRegistryEntry],
    critical_action_requested: bool = False,
    sample_size: int = 1,
) -> Dict[str, Any]:
    """
    Route sample entries from all families through the X108 admission stub.

    Returns a structured result dict with decisions and evidence.
    Never produces ACT. Never produces real proof. Never reads zip content.
    """
    by_family = route_sample_by_family(entries, sample_size=sample_size)

    all_packets: List[ContextPacket] = []
    for family_packets in by_family.values():
        all_packets.extend(family_packets)

    if not all_packets:
        return {
            "status": "NO_ROUTABLE_PACKETS",
            "families_routed": {},
            "decision_ticket": None,
            "os3_evidence_ticket": None,
            "all_packets_no_act": True,
            "all_packets_kx108_authority": True,
        }

    decision_ticket, evidence_ticket, envelope = route_packets(
        packets=all_packets,
        critical_action_requested=critical_action_requested,
        action_candidate_type="EMIT_CONTEXT" if not critical_action_requested else "WRITE",
        source_module="registry_to_adapter_dry_run_p9b",
    )

    return {
        "status": "ROUTED",
        "families_routed": {fam: len(pkts) for fam, pkts in by_family.items()},
        "total_packets": len(all_packets),
        "critical_action_requested": critical_action_requested,
        "decision": decision_ticket.decision,
        "decision_ticket_id": decision_ticket.ticket_id,
        "decision_authority": decision_ticket.decision_authority,
        "emits_act": decision_ticket.emits_act,
        "dry_run": decision_ticket.dry_run,
        "evidence_id": evidence_ticket.evidence_id,
        "proof_claim": evidence_ticket.proof_claim,
        "verification_status": evidence_ticket.verification_status,
        "envelope_id": envelope.intent_id if envelope else None,
        "all_packets_no_act": all(not p.emits_act for p in all_packets),
        "all_packets_kx108_authority": all(
            p.decision_authority == "KX108_ONLY" for p in all_packets
        ),
    }


def summarize_routing_result(result: Dict[str, Any]) -> str:
    """Return a one-line summary of a routing result dict."""
    if result.get("status") == "NO_ROUTABLE_PACKETS":
        return "NO_ROUTABLE_PACKETS"
    decision = result.get("decision", "UNKNOWN")
    total = result.get("total_packets", 0)
    families = list(result.get("families_routed", {}).keys())
    no_act = result.get("all_packets_no_act", False)
    return (
        f"decision={decision} | packets={total} | families={families} | "
        f"no_act={no_act} | proof_claim={result.get('proof_claim', '?')}"
    )
