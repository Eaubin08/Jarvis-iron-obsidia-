"""
Brody Full Runtime Reconnect
==============================
Unifies all existing snapshot adapters into a single brody_full_context dict.

Sources unified:
  - project_memory_snapshot (Foundation A)
  - session_memory_snapshot (Foundation B)
  - true_response_structure_snapshot (Foundation C)
  - freeze_metrics_snapshot
  - structured_response_snapshot
  - authority_snapshot
  - automation_snapshot

No invention — each snapshot sourced from existing modules/freeze files.
Boundary: readonly, KX108_ONLY, no write.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from apps.obsidia_api.brody_project_memory_runtime import build_project_memory_snapshot
from apps.obsidia_api.brody_session_memory_runtime import build_session_memory_snapshot
from apps.obsidia_api.brody_true_response_structure_runtime import build_true_response_structure_snapshot


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _detect_creator_context(user_message: str) -> dict[str, Any]:
    """
    Detect creator/inventor context from user message.
    Does NOT grant special authority — only flags context for response shaping.

    NOT_FOUND_IN_EXISTING_SOURCES: 'Etienne' / 'createur du cadre'
    Detector uses keyword patterns specified by operator — thin layer only.
    """
    msg_lower = (user_message or "").lower()
    detected = False
    triggers: list[str] = []

    creator_patterns = [
        "créateur", "createur", "creator",
        "inventeur", "inventor",
        "je t ai crée", "je t'ai créé", "je t ai cree", "i made you",
        "i built you", "i created you",
        "ton créateur", "ton createur", "your creator",
        "cadre obsidia", "obsidia frame",
    ]

    for pattern in creator_patterns:
        if pattern in msg_lower:
            detected = True
            triggers.append(pattern)
            break  # One match is enough

    return {
        "creator_context_detected": detected,
        "triggers": triggers,
        "note": (
            "Creator context detected via keyword matching. "
            "This does NOT grant special authority — KX108_ONLY remains sole decision authority. "
            "Response should acknowledge the context without elevating permissions."
        ),
    }


def build_brody_full_context(
    user_message: str,
    language: str = "fr",
    session_id: str = "local",
    context_packet: dict[str, Any] | None = None,
    structured_response_snapshot: dict[str, Any] | None = None,
    freeze_metrics_snapshot: dict[str, Any] | None = None,
    authority_snapshot: dict[str, Any] | None = None,
    automation_snapshot: dict[str, Any] | None = None,
    memory_response_chain_snapshot: dict[str, Any] | None = None,
    semantic_query_snapshot: dict[str, Any] | None = None,
    governed_cognitive_projection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build unified Brody full context from all existing sources.

    Chains Foundation A/B/C snapshots + existing API snapshots into
    a single brody_full_context dict used by true_voice_adapter
    and exposed in the API response payload.
    """
    # ── Foundation A — Project Memory ─────────────────────────────────────
    project_memory = build_project_memory_snapshot(
        freeze_metrics=freeze_metrics_snapshot,
    )

    # ── Foundation B — Session Memory / Follow-up ─────────────────────────
    session_memory = build_session_memory_snapshot(
        session_id=session_id,
        current_user_message=user_message,
    )

    # ── Foundation C — True Response Structure ────────────────────────────
    true_response = build_true_response_structure_snapshot()

    # ── Creator context ───────────────────────────────────────────────────
    creator = _detect_creator_context(user_message)

    # ── Rights / Action from authority snapshot ───────────────────────────
    rights_action = {
        "request_type": (authority_snapshot or {}).get("request_type", "PURE_RESPONSE"),
        "response_mode": (authority_snapshot or {}).get("response_mode", "FULL_ANSWER"),
        "requires_human_operator": (authority_snapshot or {}).get("requires_human_operator", False),
        "requires_kx108_decision": (authority_snapshot or {}).get("requires_kx108_decision", False),
        "requires_memory_gate": (authority_snapshot or {}).get("requires_memory_gate", False),
    }

    # ── Contextual material status ───────────────────────────────────────
    if project_memory.get("contextual_material_status") == "HAS_PROJECT_MEMORY":
        material = "HAS_PROJECT_MEMORY"
    elif project_memory.get("contextual_material_status") == "PARTIAL_PROJECT_MEMORY":
        material = "PARTIAL_PROJECT_MEMORY"
    elif session_memory.get("followup_supported"):
        material = "HAS_SESSION_CONTEXT_ONLY"
    elif true_response.get("all_core_features_present"):
        material = "HAS_RESPONSE_STRUCTURE_ONLY"
    else:
        material = "NO_PROJECT_MEMORY"

    # ── Missing links ─────────────────────────────────────────────────────
    missing: list[str] = []
    if not project_memory.get("native_memory_ready"):
        missing.append("obsidia_native_memory_not_ready")
    if not session_memory.get("session_ledger_v2_found"):
        missing.append("session_ledger_not_found_for_session_id")
    if not true_response.get("terminal_dialogue_found"):
        missing.append("terminal_dialogue_not_importable")
    if not creator.get("creator_context_detected"):
        # Not a missing link — it's normal for most messages
        pass

    used_modules = []
    if project_memory.get("context_packet_query_found"):
        used_modules.append("context_packet_query_readonly")
    if project_memory.get("content_hydration_found"):
        used_modules.append("content_hydration_readonly")
    if project_memory.get("local_response_engine_found"):
        used_modules.append("local_response_engine_readonly")
    if session_memory.get("session_ledger_v2_found"):
        used_modules.append("session_memory_ledger_readonly_v2")
    if true_response.get("terminal_dialogue_found"):
        used_modules.append("terminal_structural_dialogue_readonly_v1_1b")

    # ── Build full context ────────────────────────────────────────────────
    return {
        "source_mode": "THREE_FOUNDATIONS_RECONNECTED",
        "status": "BRODY_FULL_RUNTIME_RECONNECT_PASS",
        "created_at": _now(),
        "project_memory_snapshot": project_memory,
        "session_memory_snapshot": session_memory,
        "true_response_structure_snapshot": true_response,
        "rights_action_snapshot": rights_action,
        "freeze_metrics_snapshot": freeze_metrics_snapshot or {},
        "structured_response_snapshot": structured_response_snapshot or {},
        "memory_response_chain_snapshot": memory_response_chain_snapshot or {},
        "semantic_query_snapshot": semantic_query_snapshot or {},
        "governed_cognitive_projection": governed_cognitive_projection or {},
        "creator_context": creator,
        "contextual_material_status": material,
        "followup_resolved": session_memory.get("followup_resolved", False),
        "followup_requested": session_memory.get("followup_requested", False),
        "creator_context_detected": creator.get("creator_context_detected", False),
        "creator_authority_granted": False,
        "used_existing_modules": used_modules,
        "missing_runtime_links": missing,
        "readonly": True,
        "memory_write": False,
        "graphiti_write": False,
        "neo4j_write": False,
        "emits_act": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "decision_authority": "KX108_ONLY",
    }
