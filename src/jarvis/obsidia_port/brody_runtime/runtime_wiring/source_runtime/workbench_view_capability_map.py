"""
P46 — Workbench View → Capability / Route Map.
Chaque vue Workbench est mappée à sa capability, ses routes et ses contraintes X-108.
NO ACT. NO write. runtime_allowed_now=False partout. emits_act=False partout.
KX108_ONLY pour toute vue actionnelle.
"""
from __future__ import annotations

from typing import Any

WORKBENCH_VIEW_CAPABILITY_MAP: dict[str, dict[str, Any]] = {
    "AuditView.tsx": {
        "coverage_status": "CONNECTED_TO_RUNTIME",
        "capability": "AUDIT_TRAIL_READONLY",
        "routes": ["/api/audit/events"],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "note": "Append-only audit trail replay — no deletion, no mutation",
    },
    "BlockchainView.tsx": {
        "coverage_status": "BLOCKED_ACTION_VIEW",
        "capability": "ACTION_REQUEST_BLOCKED",
        "routes": [],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": "BLOCK_OR_HOLD_CONTEXT_ONLY",
        "note": "All blockchain actions BLOCKED — no real chain, no wallet, no contract",
    },
    "ChatView.tsx": {
        "coverage_status": "CONNECTED_TO_RUNTIME",
        "capability": "BRODY_CONTEXT_ENGINE",
        "routes": ["/api/brody/chat"],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "note": "Brody responds — readonly=true, allowed_to_decide=false, allowed_to_act=false",
    },
    "GencoinView.tsx": {
        "coverage_status": "BLOCKED_ACTION_VIEW",
        "capability": "ACTION_REQUEST_BLOCKED",
        "routes": [],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": "BLOCK_OR_HOLD_CONTEXT_ONLY",
        "note": "Gencoin is NOT a real token — LEDGER_ONLY, no mint, no trade, no wallet",
    },
    "GraphitiView.tsx": {
        "coverage_status": "CONNECTED_TO_RUNTIME",
        "capability": "GRAPHITI_FROZEN_READONLY",
        "routes": [
            "/graph/v20/frozen/status",
            "/graph/v20/frozen/metrics",
            "/graph/v20/frozen/readiness",
            "/graph/v20/frozen/context",
        ],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "note": "Graphiti V20 frozen readonly — neo4j_write=false, graphiti_write=false",
    },
    "MemoryView.tsx": {
        "coverage_status": "CONNECTED_TO_RUNTIME",
        "capability": "MEMORY_CANDIDATE_READONLY",
        "routes": ["/api/memory/candidates"],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "note": "CANDIDATE_ONLY — memory_write=false, auto_promotion_allowed=false",
    },
    "OS3View.tsx": {
        "coverage_status": "INTERNAL_UI_ONLY",
        "capability": "OS3_PROOF_DISPLAY",
        "routes": [],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "note": "Mock OS3 proof ticket display — no API, no kernel decision, PROTECTED artifacts",
    },
    "OSMapView.tsx": {
        "coverage_status": "CONNECTED_TO_OS_MAP",
        "capability": "WORKBENCH_PREVIEW",
        "routes": ["/api/runtime-wiring/os-map/query"],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "note": "P38 — READONLY_PREVIEW_ONLY, KX108_ONLY, full OS map query",
    },
    "RuntimeWiringPreviewView.tsx": {
        "coverage_status": "CONNECTED_TO_RUNTIME",
        "capability": "SOURCE_RUNTIME_PREVIEW",
        "routes": [
            "/api/runtime-wiring/preview",
            "/api/runtime-wiring/source-runtime/preview",
        ],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "note": "P11A+P29 — dry-run state preview, READONLY_PREVIEW_ONLY",
    },
    "SettingsView.tsx": {
        "coverage_status": "CONNECTED_TO_WORKBENCH_ONLY",
        "capability": "WORKBENCH_CONFIG_DISPLAY",
        "routes": [],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "note": "Config display only — reads VITE env vars, no API calls",
    },
    "TranslationView.tsx": {
        "coverage_status": "CONNECTED_TO_WORKBENCH_ONLY",
        "capability": "OS_TRAD_LOCAL_PIPELINE",
        "routes": [],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "note": "Local OS Trad pipeline — runOSTradPipeline lib, no backend call",
    },
    "WorldCallView.tsx": {
        "coverage_status": "BLOCKED_ACTION_VIEW",
        "capability": "ACTION_REQUEST_BLOCKED",
        "routes": [],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": "BLOCK_OR_HOLD_CONTEXT_ONLY",
        "note": "DRY_RUN ONLY — no real egress, real_action_blocked=true",
    },
    "X108View.tsx": {
        "coverage_status": "CONNECTED_TO_STATUS_ONLY",
        "capability": "GOVERNANCE_KERNEL_STATUS",
        "routes": ["/health"],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "note": "Kernel health + invariants display — readonly, no mutation",
    },
}


def get_view_capability_map() -> dict[str, dict[str, Any]]:
    return WORKBENCH_VIEW_CAPABILITY_MAP


def get_view_classification(view_file: str) -> dict[str, Any]:
    return WORKBENCH_VIEW_CAPABILITY_MAP.get(view_file, {})


def build_workbench_coverage_summary() -> dict[str, Any]:
    """Résumé complet P46 — toutes vues classifiées, unclassified=0, coverage=100%."""
    total = len(WORKBENCH_VIEW_CAPABILITY_MAP)
    counts: dict[str, int] = {}
    unclassified = 0

    for entry in WORKBENCH_VIEW_CAPABILITY_MAP.values():
        status = entry.get("coverage_status", "UNCLASSIFIED")
        if status == "UNCLASSIFIED":
            unclassified += 1
        counts[status] = counts.get(status, 0) + 1

    covered = total - unclassified
    percent = (covered / total * 100.0) if total > 0 else 0.0

    return {
        "workbench_view_coverage_status": "FULL_COVERAGE" if percent >= 100.0 else "PARTIAL_COVERAGE",
        "workbench_views_total": total,
        "workbench_views_classified": covered,
        "unclassified_views_count": unclassified,
        "workbench_views_coverage_percent": percent,
        "coverage_counts": counts,
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
    }
