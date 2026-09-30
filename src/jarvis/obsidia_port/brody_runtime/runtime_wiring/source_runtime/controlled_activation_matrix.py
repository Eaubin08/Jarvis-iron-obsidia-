"""
P50 — Controlled Activation Readiness Matrix.

Classifies every runtime surface item into activation levels after P49 gate.
NO ACT. NO write. NO extraction. NO Graphiti write. NO kernel mutation.
KX108_ONLY. READONLY. activation_allowed_now=False.

Levels:
  LEVEL_0_LOCKED                  — never activate
  LEVEL_1_READONLY_ACTIVE_CANDIDATE  — can be enabled for real reads
  LEVEL_2_DRY_RUN_ACTIVE_CANDIDATE   — can simulate, no real effect
  LEVEL_3_HOLD_GATE_CANDIDATE        — HOLD/BLOCK/ALLOW eval only, no ACT
  LEVEL_4_FUTURE_ACTION_GATE         — real action, requires dedicated palier
"""
from __future__ import annotations

# ── Level 1 — READONLY ACTIVE CANDIDATE ─────────────────────────────────────

_LEVEL_1_READONLY = [
    {
        "id": "brody_context_readonly",
        "label": "Brody context (READONLY_CONTEXT mode)",
        "category": "BRODY",
        "activation_mode": "READONLY_CONTEXT",
        "can_execute_actions": False,
        "can_write_memory": False,
        "can_mutate_graph": False,
        "can_explain_runtime_path": True,
        "rationale": "Brody chat + context bridge fully classified P47/P48; all routes CONNECTED_READONLY",
    },
    {
        "id": "os_map_readonly",
        "label": "OS Map endpoint (status + query, readonly)",
        "category": "OS_MAP",
        "activation_mode": "READONLY_CONTEXT",
        "rationale": "147 routes 100% classified; os-map/status and os-map/query emit no ACT",
    },
    {
        "id": "source_runtime_preview",
        "label": "Source runtime preview (hydration plan, no file extraction)",
        "category": "SOURCE_RUNTIME",
        "activation_mode": "READONLY_CONTEXT",
        "rationale": "readonly_content_loader + source_hydration_planner: no file write",
    },
    {
        "id": "atlas_context_readonly",
        "label": "ATLAS context packet (readonly)",
        "category": "ATLAS",
        "activation_mode": "READONLY_CONTEXT",
        "rationale": "atlas_to_context_packet: CONNECTED_CONTEXT_PACKET, no ACT",
    },
    {
        "id": "os_trad_reverse_readonly",
        "label": "OS_TRAD reverse / interlanguage index (readonly)",
        "category": "OS_TRAD",
        "activation_mode": "READONLY_CONTEXT",
        "rationale": "os_trad_reverse_index + reverse_os_interlanguage_index: status-only, no write",
    },
    {
        "id": "graphiti_readonly_client",
        "label": "Graphiti readonly client (context read, no graph write)",
        "category": "GRAPHITI",
        "activation_mode": "READONLY_CONTEXT",
        "can_write_graph": False,
        "rationale": "graphiti_client_wired=True in P44; read path only, write path = LEVEL_4",
    },
    {
        "id": "workbench_views_readonly",
        "label": "Workbench views (13 views, readonly display)",
        "category": "WORKBENCH",
        "activation_mode": "READONLY_CONTEXT",
        "rationale": "13/13 views classified P46; CONNECTED_TO_RUNTIME + STATUS_ONLY views safe",
    },
    {
        "id": "route_status_endpoints",
        "label": "Route status / readiness / metrics endpoints",
        "category": "ROUTES",
        "activation_mode": "READONLY_CONTEXT",
        "rationale": "STATUS_ONLY (21) + CONNECTED_READONLY (101) routes: no ACT pathway",
    },
    {
        "id": "memory_read",
        "label": "Memory read (SCRATCH.md, CURRENT_FOCUS.md, RISKS.md)",
        "category": "MEMORY",
        "activation_mode": "READONLY_CONTEXT",
        "rationale": "Read-only access to memory files; no write",
    },
    {
        "id": "cognitive_context_packet",
        "label": "Cognitive context packet (readonly)",
        "category": "COGNITIVE",
        "activation_mode": "READONLY_CONTEXT",
        "rationale": "cognitive_to_context_packet: CONNECTED_CONTEXT_PACKET, no ACT",
    },
    {
        "id": "npl_context_packet",
        "label": "NPL context packet (readonly)",
        "category": "NPL",
        "activation_mode": "READONLY_CONTEXT",
        "rationale": "npl_to_context_packet: CONNECTED_CONTEXT_PACKET, no ACT",
    },
    {
        "id": "compliance_context_packet",
        "label": "Compliance / RSSI context packets (readonly)",
        "category": "RSSI_COMPLIANCE",
        "activation_mode": "READONLY_CONTEXT",
        "rationale": "rssi_rgpd + rssi_security + compliance context packets: no write",
    },
    {
        "id": "capability_path_router_readonly",
        "label": "Capability path router (P36/P37, readonly routing)",
        "category": "CAPABILITY_ROUTER",
        "activation_mode": "READONLY_CONTEXT",
        "rationale": "route_capability_path + link_capabilities_to_inventory: no side effects",
    },
]

# ── Level 2 — DRY_RUN ACTIVE CANDIDATE ───────────────────────────────────────

_LEVEL_2_DRY_RUN = [
    {
        "id": "world_action_bus_dry_run",
        "label": "World action bus (dry-run mode, no real emission)",
        "category": "WORLD_ACTION_BUS",
        "activation_mode": "DRY_RUN",
        "emits_real_action": False,
        "rationale": "Bus exists; dry-run path simulates without committing to external systems",
    },
    {
        "id": "external_signals_advisory",
        "label": "External signals advisory (Timeverse, no real API call)",
        "category": "EXTERNAL_SIGNALS",
        "activation_mode": "DRY_RUN",
        "emits_real_action": False,
        "rationale": "external_signals_to_context_packet: dry advisory only, no live external call",
    },
    {
        "id": "simulation_routes",
        "label": "Simulation / preview routes (dry path evaluation)",
        "category": "ROUTES",
        "activation_mode": "DRY_RUN",
        "rationale": "Routes classified CONNECTED_READONLY allow dry-run invocation for testing",
    },
    {
        "id": "gencoin_dry_run",
        "label": "Gencoin (dry-run, no blockchain write)",
        "category": "GENCOIN",
        "activation_mode": "DRY_RUN",
        "emits_real_action": False,
        "rationale": "Gencoin simulation path; no real token emission or wallet interaction",
    },
    {
        "id": "blockchain_dry_run",
        "label": "Blockchain interaction (dry-run, no real TX)",
        "category": "BLOCKCHAIN",
        "activation_mode": "DRY_RUN",
        "emits_real_action": False,
        "rationale": "Blockchain dry path; no real transaction; read-only chain state query only",
    },
    {
        "id": "os3_evidence_dry_expansion",
        "label": "OS3 evidence expansion (dry preview, no file write)",
        "category": "OS3",
        "activation_mode": "DRY_RUN",
        "rationale": "Preview expansion plan without materializing new OS3 evidence packs",
    },
]

# ── Level 3 — HOLD_GATE_CANDIDATE ────────────────────────────────────────────

_LEVEL_3_HOLD_GATE = [
    {
        "id": "x108_gate_evaluation",
        "label": "X108 gate evaluation (HOLD/BLOCK/ALLOW decision, no ACT)",
        "category": "X108_GATE",
        "activation_mode": "HOLD_GATE",
        "can_emit_act": False,
        "rationale": "X108 is the decision authority; evaluation allowed, ACT emission forbidden",
    },
    {
        "id": "os3_evidence_expansion_hold",
        "label": "OS3 evidence expansion (HOLD candidate, awaiting scope approval)",
        "category": "OS3",
        "activation_mode": "HOLD_GATE",
        "rationale": "OS3 expansion needs KX108 review before materializing",
    },
    {
        "id": "decision_tickets",
        "label": "Decision tickets (evaluation + classification, no execution)",
        "category": "DECISION",
        "activation_mode": "HOLD_GATE",
        "rationale": "Ticket creation and classification; execution requires dedicated palier",
    },
    {
        "id": "hold_block_allow_simulation",
        "label": "HOLD/BLOCK/ALLOW simulation (evaluate only, no real gate toggle)",
        "category": "X108_GATE",
        "activation_mode": "HOLD_GATE",
        "rationale": "Simulate gate decision paths without changing actual gate state",
    },
    {
        "id": "brody_authority_escalation_hold",
        "label": "Brody authority escalation (evaluate only, no ACT)",
        "category": "BRODY",
        "activation_mode": "HOLD_GATE",
        "rationale": "Brody can evaluate escalation requests; execution requires P51+",
    },
]

# ── Level 4 — FUTURE ACTION GATE ─────────────────────────────────────────────

_LEVEL_4_FUTURE_ACTION = [
    {
        "id": "memory_write",
        "label": "Memory write (SCRATCH.md, CURRENT_FOCUS.md)",
        "category": "MEMORY",
        "activation_mode": "FUTURE_ACTION_GATE",
        "requires_palier": "P51+",
        "rationale": "Irreversible session state mutation; requires explicit KX108 unlock",
    },
    {
        "id": "graphiti_write",
        "label": "Graphiti write (graph node / edge creation)",
        "category": "GRAPHITI",
        "activation_mode": "FUTURE_ACTION_GATE",
        "requires_palier": "P51+",
        "rationale": "Graph write is irreversible without rollback plan; deferred to dedicated palier",
    },
    {
        "id": "real_external_api_action",
        "label": "Real external API action (live calls with side effects)",
        "category": "EXTERNAL_API",
        "activation_mode": "FUTURE_ACTION_GATE",
        "requires_palier": "P52+",
        "rationale": "External API with real effects; requires full audit trail and reversibility plan",
    },
    {
        "id": "real_blockchain_transaction",
        "label": "Real blockchain transaction (on-chain write)",
        "category": "BLOCKCHAIN",
        "activation_mode": "FUTURE_ACTION_GATE",
        "requires_palier": "P53+",
        "rationale": "Irreversible; requires dedicated gate with multi-sig or KX108 proof",
    },
    {
        "id": "real_wallet_interaction",
        "label": "Real wallet interaction (Gencoin, token emission)",
        "category": "GENCOIN",
        "activation_mode": "FUTURE_ACTION_GATE",
        "requires_palier": "P53+",
        "rationale": "Wallet operations irreversible; blocked until explicit palier",
    },
    {
        "id": "file_mutation",
        "label": "File mutation (edit tracked source files)",
        "category": "FILE_SYSTEM",
        "activation_mode": "FUTURE_ACTION_GATE",
        "requires_palier": "explicit user approval",
        "rationale": "Any tracked file mutation goes through freeze-guardian and risk-reviewer",
    },
    {
        "id": "email_sending",
        "label": "Email / notification sending (Gmail, SMTP, webhook)",
        "category": "EXTERNAL_COMMS",
        "activation_mode": "FUTURE_ACTION_GATE",
        "requires_palier": "P52+",
        "rationale": "External comms are irreversible; not connected; blocked indefinitely for now",
    },
    {
        "id": "irreversible_workflow",
        "label": "Irreversible workflow execution (deploy, migration, release)",
        "category": "WORKFLOW",
        "activation_mode": "FUTURE_ACTION_GATE",
        "requires_palier": "P54+",
        "rationale": "Deploy/migration require proof of reversibility and approval chain",
    },
]

# ── Level 0 — LOCKED ─────────────────────────────────────────────────────────

_LEVEL_0_LOCKED = [
    {
        "id": "unknown_external_tools",
        "label": "Unknown external tools (no KX108 boundary)",
        "category": "EXTERNAL",
        "rationale": "No audit trail; not classified in P43-P49 surface",
    },
    {
        "id": "unsafe_mutation",
        "label": "Unsafe mutation (no freeze-guardian check)",
        "category": "FILE_SYSTEM",
        "rationale": "Any edit bypassing freeze-guardian is permanently locked",
    },
    {
        "id": "unverified_local_packs",
        "label": "Unverified local-only source packs",
        "category": "SOURCE_PACKS",
        "rationale": "Source packs without P42A gate proof are locked",
    },
    {
        "id": "secrets_env_access",
        "label": "Secrets / env file access (.env, credentials)",
        "category": "SECRETS",
        "rationale": "Permanently locked; no context justifies direct secrets access",
    },
    {
        "id": "kernel_mutation",
        "label": "Kernel mutation (proof/, formal/tla/, merkle*, seal*, rfc3161*)",
        "category": "KERNEL",
        "rationale": "Crypto-anchored files; mutation requires proof-sentinel + explicit approval",
    },
    {
        "id": "action_gateway_open",
        "label": "Action gateway open (runtime_allowed_now=True)",
        "category": "GATEWAY",
        "rationale": "Gateway cannot be opened without P51+ palier + X108 decision",
    },
    {
        "id": "activation_allowed_toggle",
        "label": "activation_allowed toggle (setting to True)",
        "category": "GATEWAY",
        "rationale": "activation_allowed remains False until P51; no code path may set it True",
    },
]

# ── Brody readiness ───────────────────────────────────────────────────────────

_BRODY_READINESS = {
    "brody_activation_mode": "READONLY_CONTEXT",
    "brody_level": "LEVEL_1_READONLY_ACTIVE_CANDIDATE",
    "instances": [
        {
            "id": "brody_chat_route",
            "route": "/api/brody/chat",
            "level": "LEVEL_1",
            "mode": "READONLY_CONTEXT",
        },
        {
            "id": "brody_context_bridge",
            "module": "brody_source_context_bridge",
            "level": "LEVEL_1",
            "mode": "READONLY_CONTEXT",
        },
        {
            "id": "brody_true_voice",
            "feature": "true_voice / final_answer",
            "level": "LEVEL_1",
            "mode": "READONLY_CONTEXT",
        },
        {
            "id": "source_runtime_context_injection",
            "feature": "source runtime context injection",
            "level": "LEVEL_1",
            "mode": "READONLY_CONTEXT",
        },
        {
            "id": "os_map_path_explanation",
            "feature": "OS Map path explanation",
            "level": "LEVEL_1",
            "mode": "READONLY_CONTEXT",
        },
    ],
    "can_execute_actions": False,
    "can_write_memory": False,
    "can_mutate_graph": False,
    "can_explain_runtime_path": True,
    "emits_act": False,
    "decision_authority": "KX108_ONLY",
}

# ── Graphiti / Memory readiness ───────────────────────────────────────────────

_GRAPHITI_MEMORY_READINESS = {
    "graphiti_readonly": {
        "level": "LEVEL_1_READONLY_ACTIVE_CANDIDATE",
        "can_write": False,
        "rationale": "Graph read: safe, classified P44. Write: deferred to LEVEL_4.",
    },
    "graphiti_write": {
        "level": "LEVEL_4_FUTURE_ACTION_GATE",
        "requires_palier": "P51+",
        "rationale": "Irreversible graph mutation; blocked.",
    },
    "memory_read": {
        "level": "LEVEL_1_READONLY_ACTIVE_CANDIDATE",
        "can_write": False,
        "rationale": "SCRATCH.md / CURRENT_FOCUS.md / RISKS.md: safe read.",
    },
    "memory_write": {
        "level": "LEVEL_4_FUTURE_ACTION_GATE",
        "requires_palier": "P51+",
        "rationale": "Session state mutation; blocked until dedicated palier.",
    },
}

# ── World action bus readiness ────────────────────────────────────────────────

_WORLD_ACTION_BUS_READINESS = {
    "dry_run": {
        "level": "LEVEL_2_DRY_RUN_ACTIVE_CANDIDATE",
        "emits_real_action": False,
        "rationale": "Dry-run path: simulate bus emission without external effect.",
    },
    "real_action": {
        "level": "LEVEL_4_FUTURE_ACTION_GATE",
        "requires_palier": "P52+",
        "rationale": "Real bus emission: irreversible external effect. Blocked.",
    },
    "action_request": {
        "status": "ACTION_REQUEST_BLOCKED",
        "x108_required": True,
        "rationale": "All action requests blocked until X108 gate evaluation.",
    },
}


def build_controlled_activation_matrix() -> dict:
    """Return the P50 controlled activation readiness matrix."""

    def _count_items_with_real_action(level_list: list) -> int:
        return sum(
            1 for item in level_list
            if item.get("emits_real_action") is True
            or item.get("activation_mode") == "FUTURE_ACTION_GATE"
        )

    readonly_candidate_ids = [item["id"] for item in _LEVEL_1_READONLY]
    has_action_in_level_1 = any(
        item.get("can_execute_actions") is True
        or item.get("emits_real_action") is True
        for item in _LEVEL_1_READONLY
    )

    return {
        "audit_id": "P50_CONTROLLED_ACTIVATION_MATRIX",
        "audit_date": "2026-06-04",
        "activation_matrix_status": "READY",
        "based_on": "P49_GLOBAL_RUNTIME_SURFACE_100_GATE",
        "activation_allowed_now": False,
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "levels": {
            "LEVEL_0_LOCKED": _LEVEL_0_LOCKED,
            "LEVEL_1_READONLY_ACTIVE_CANDIDATE": _LEVEL_1_READONLY,
            "LEVEL_2_DRY_RUN_ACTIVE_CANDIDATE": _LEVEL_2_DRY_RUN,
            "LEVEL_3_HOLD_GATE_CANDIDATE": _LEVEL_3_HOLD_GATE,
            "LEVEL_4_FUTURE_ACTION_GATE": _LEVEL_4_FUTURE_ACTION,
        },
        "brody_readiness": _BRODY_READINESS,
        "graphiti_memory_readiness": _GRAPHITI_MEMORY_READINESS,
        "world_action_bus_readiness": _WORLD_ACTION_BUS_READINESS,
        "counts": {
            "level_0_locked": len(_LEVEL_0_LOCKED),
            "level_1_readonly": len(_LEVEL_1_READONLY),
            "level_2_dry_run": len(_LEVEL_2_DRY_RUN),
            "level_3_hold_gate": len(_LEVEL_3_HOLD_GATE),
            "level_4_future_action": len(_LEVEL_4_FUTURE_ACTION),
        },
        "readonly_activation_candidates": readonly_candidate_ids,
        "any_real_action_in_level_1": has_action_in_level_1,
        "invariant_check": {
            "no_act_in_level_1": not has_action_in_level_1,
            "no_real_action_gate_open": True,
            "activation_allowed_now_is_false": True,
            "runtime_allowed_now_is_false": True,
            "kx108_only": True,
        },
        "next_activation_palier": "P51_BRODY_READONLY_CONTROLLED_ACTIVATION",
        "p50_status": "P50_CONTROLLED_ACTIVATION_READINESS_READY",
    }
