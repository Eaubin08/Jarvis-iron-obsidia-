# runtime_wiring/source_runtime/brody_source_context_bridge.py
# Main bridge: query source packs → hydrate → X108 gate → produce Brody context summary.
# P36 extension: capability_path_router branché. No ACT. No write. KX108_ONLY.

from __future__ import annotations
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from runtime_wiring.source_runtime.source_runtime_query import QueryResult, query_source_packs
from runtime_wiring.packet_types import ContextPacket, DecisionTicketDryRun, OS3EvidenceTicketDryRun
from runtime_wiring.dry_run_packet_router import route_packets
from runtime_wiring.source_runtime.source_runtime_cache import (
    list_available_families_cached,
    get_cache_stats,
)
from runtime_wiring.source_runtime.source_family_selector import (
    select_families_for_message,
    describe_selection,
)
from runtime_wiring.source_runtime.capability_path_router import route_capability_path
from runtime_wiring.source_runtime.source_hydration_planner import build_hydration_plan_from_path
from runtime_wiring.source_runtime.runtime_inventory_graph import build_runtime_inventory_graph
from runtime_wiring.source_runtime.capability_inventory_linker import link_capabilities_to_inventory

_BOUNDARY = {
    "decision_authority": "KX108_ONLY",
    "readonly": True,
    "emits_act": False,
    "memory_write": False,
    "graph_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "zip_extraction": False,
    "source_pack_import": False,
    "world_action": False,
}


def build_brody_context_from_source_packs(
    query: str,
    families: Optional[List[str]] = None,
    limit: int = 5,
    critical_action_requested: bool = False,
) -> Dict[str, Any]:
    """
    Query source packs, hydrate into ContextPackets, route through X108, return Brody context.

    P36: capability_path_router branché — détecte intents, sélectionne chemin runtime optimal.
    Decision allowed: ALLOW_CONTEXT_ONLY only.
    If X108 returns HOLD or BLOCK: Brody gets limited context + warning.

    Returns a dict safe to inject into the Brody payload.
    Never raises — all errors produce a graceful fallback.
    """
    stats_before = get_cache_stats()
    available_families = list_available_families_cached()
    if not available_families:
        return _fallback("NO_SOURCE_PACKS_AVAILABLE", query)

    # P36 — Route via capability path router
    cap_routing = route_capability_path(
        query=query,
        available_families=available_families,
        max_paths=5,
    )

    # P37 — Enrichit avec l'inventaire (cache chaud après premier appel)
    try:
        inventory_graph = build_runtime_inventory_graph()
        cap_routing = link_capabilities_to_inventory(cap_routing, inventory_graph)
    except Exception:
        pass  # L'inventaire est optionnel — le routing P36 fonctionne sans lui

    selected_path = cap_routing.get("selected_path", {})
    hydration_plan = build_hydration_plan_from_path(selected_path, max_files=8, max_bytes=50_000)

    # Smart family selection: explicit override OR capability-router-guided selection
    if families:
        target_families = [f for f in families if f in available_families]
        if not target_families:
            return _fallback("REQUESTED_FAMILIES_NOT_AVAILABLE", query)
        keyword_matched = True
        selection_desc = f"EXPLICIT_OVERRIDE:{','.join(target_families)}"
    else:
        # Prefer families from selected_path if available
        path_families = [
            f for f in selected_path.get("source_families", [])
            if f in available_families
        ]
        if path_families:
            target_families = path_families[:3]
            keyword_matched = True
            selection_desc = f"CAPABILITY_ROUTER:{','.join(target_families)}"
        else:
            target_families, keyword_matched = select_families_for_message(
                query, available_families, max_families=3, fallback_limit=3
            )
            selection_desc = describe_selection(query, target_families, keyword_matched)

    # Query and hydrate
    results = query_source_packs(
        families=target_families,
        limit=limit,
        prefer_short_files=True,
    )
    stats_after = get_cache_stats()
    cache_hit = stats_after["cache_hits"] > stats_before["cache_hits"]

    # P42B: include METADATA_ONLY entries (CI-safe, no local pack) alongside fully-hydrated OK entries
    ok_results = [
        r for r in results
        if r.hydration_status in ("OK", "METADATA_ONLY") and r.context_packet is not None
    ]
    skipped = [r for r in results if r.hydration_status not in ("OK", "METADATA_ONLY")]

    if not ok_results:
        return _fallback("NO_HYDRATED_ENTRIES", query)

    packets: List[ContextPacket] = [r.context_packet for r in ok_results]

    # Route through X108 — always context-only, never critical
    decision_ticket, evidence_ticket, envelope = route_packets(
        packets=packets,
        critical_action_requested=False,
        action_candidate_type="EMIT_CONTEXT",
        source_module="brody_source_context_bridge_p36",
    )

    # Enforce ALLOW_CONTEXT_ONLY
    if decision_ticket.decision != "ALLOW_CONTEXT_ONLY":
        return _fallback(
            f"X108_REFUSED:{decision_ticket.decision}",
            query,
            decision_ticket=decision_ticket,
            evidence_ticket=evidence_ticket,
        )

    # Build Brody-readable context summary
    context_summary = _build_context_summary(ok_results, query)

    return {
        "source_pack_context_used": True,
        "source_pack_families": sorted({r.family for r in ok_results}),
        "source_pack_entries_used": len(ok_results),
        "source_pack_entries_skipped": len(skipped),
        "available_families": available_families,
        "x108_decision": decision_ticket.decision,
        "x108_decision_authority": decision_ticket.decision_authority,
        "x108_gate_status": decision_ticket.x108_gate_status,
        "x108_decision_ticket_id": decision_ticket.ticket_id,
        "os3_evidence_id": evidence_ticket.evidence_id,
        "os3_evidence_hash_status": evidence_ticket.hash_status,
        "os3_proof_claim": evidence_ticket.proof_claim,
        "os3_verification_status": evidence_ticket.verification_status,
        "context_summary_for_brody": context_summary,
        "source_pack_selected_families": target_families,
        "source_pack_selection_desc": selection_desc,
        "source_pack_keyword_matched": keyword_matched,
        "source_pack_cache_hit": cache_hit,
        "source_pack_runtime_stats": get_cache_stats(),
        "hydrated_entries": [
            {
                "family": r.family,
                "file_name": r.file_name,
                "bytes_read": r.bytes_read,
                "content_preview": r.content_preview[:500],
                "content_hash": r.content_hash[:16],
            }
            for r in ok_results
        ],
        # P36 — Capability path router fields
        "capability_path_router_available": True,
        "detected_intents": cap_routing.get("detected_intents", []),
        "required_capabilities": cap_routing.get("required_capabilities", []),
        "ranked_runtime_paths": cap_routing.get("ranked_runtime_paths", []),
        "selected_runtime_path": selected_path,
        "selected_modules": selected_path.get("modules", []),
        "selected_adapters": selected_path.get("adapters", []),
        "selected_routes": selected_path.get("routes", []),
        "selected_source_families": selected_path.get("source_families", []),
        "selected_source_subfamilies": selected_path.get("source_subfamilies", []),
        "selected_evidence_packs": selected_path.get("evidence_packs", []),
        "hydration_plan": hydration_plan,
        "source_file_refs": hydration_plan.get("planned_files", []),
        "x108_decision_path": selected_path.get("x108_decision", "ALLOW_CONTEXT_ONLY"),
        # P37 — Inventory linker fields
        "inventory_linked": cap_routing.get("inventory_linked", False),
        "inventory_status": cap_routing.get("inventory_status", "NOT_LOADED"),
        "selected_functions": cap_routing.get("selected_functions", []),
        "selected_classes": cap_routing.get("selected_classes", []),
        "selected_routes_inventory": cap_routing.get("selected_routes", []),
        "selected_tests": cap_routing.get("selected_tests", []),
        "selected_docs": cap_routing.get("selected_docs", []),
        "coverage_status": cap_routing.get("coverage_status", "UNKNOWN"),
        # Safety invariants
        "no_act": True,
        "memory_write": False,
        "graph_write": False,
        "kernel_mutation": False,
        "zip_extraction": False,
        "boundary": _BOUNDARY,
        "status": "SOURCE_PACK_CONTEXT_READY",
    }


def _build_context_summary(results: List[QueryResult], query: str) -> str:
    """Build a natural language summary of hydrated context for Brody injection."""
    if not results:
        return ""

    families = sorted({r.family for r in results})
    lines = [
        f"[SOURCE PACK CONTEXT — KX108_ONLY — READONLY — NO ACT]",
        f"Query: {query[:100]}",
        f"Families: {', '.join(families)}",
        f"Entries hydrated: {len(results)}",
        "",
    ]
    for r in results:
        lines.append(f"## {r.file_name} ({r.family})")
        lines.append(r.content_preview[:600].strip())
        lines.append("")

    return "\n".join(lines)


def _fallback(reason: str, query: str, **extras) -> Dict[str, Any]:
    base = {
        "source_pack_context_used": False,
        "source_pack_families": [],
        "source_pack_entries_used": 0,
        "x108_decision": "N/A",
        "os3_proof_claim": False,
        "context_summary_for_brody": "",
        "no_act": True,
        "memory_write": False,
        "graph_write": False,
        "kernel_mutation": False,
        "zip_extraction": False,
        "status": f"SOURCE_PACK_CONTEXT_UNAVAILABLE:{reason}",
    }
    base.update(extras)
    return base
