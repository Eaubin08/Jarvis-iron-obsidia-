"""
Brody Automation Layer Orchestrator — Readonly
=============================================
Wires existing periphery automation modules to the Brody API pipeline.
Routes by request_type (from rights/authority matrix).

Rules (absolute):
  - Never creates new memory
  - Never writes Graphiti or Neo4j
  - Never emits ACT
  - Never calls operators or executes commands
  - Imports existing module logic — no subprocess invocation
  - Returns automation_snapshot enriching authority_snapshot → final_answer

Boundary (hardcoded, cannot be overridden):
  readonly=True, memory_write=False, graphiti_write=False,
  neo4j_write=False, emits_act=False, decision_authority=KX108_ONLY
"""
from __future__ import annotations

import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Hardcoded boundary ────────────────────────────────────────────────────────
AUTOMATION_BOUNDARY: dict[str, Any] = {
    "readonly": True,
    "advisory_only": True,
    "response_only": True,
    "memory_decision": False,
    "allowed_to_decide": False,
    "allowed_to_act": False,
    "emits_act": False,
    "emits_verdict": False,
    "memory_write": False,
    "graphiti_write": False,
    "neo4j_write": False,
    "kernel_mutation": False,
    "decision_authority": "KX108_ONLY",
}

_PERIPHERY = Path(__file__).resolve().parents[2] / "periphery" / "brody_memory_readonly"
_SESSIONS = Path(__file__).resolve().parents[2] / "_local_audits" / "brody_sessions"


def _add_path(sub: str) -> None:
    p = _PERIPHERY / sub
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))


# ── Module imports — graceful fallback if unavailable ───────────────────────

_LEDGER_OK = False
_ledger_build: Any = None
try:
    _add_path("session_memory_ledger_readonly")
    from brody_session_memory_ledger_readonly_v2 import build_record as _ledger_build  # type: ignore
    _LEDGER_OK = True
except Exception:
    pass

_TRIAGE_OK = False
_triage_classify: Any = None
_TriageSealer: Any = None
try:
    _add_path("auto_triage_memory_intake_readonly")
    from brody_auto_triage_memory_intake_readonly_v1 import (  # type: ignore
        classify_record as _triage_classify,
        MerkleSealer as _TriageSealer,
    )
    _TRIAGE_OK = True
except Exception:
    pass

_PACKET_OK = False
_packet_build: Any = None
try:
    _add_path("brody_human_command_packet_readonly")
    from brody_human_command_packet_readonly_v1 import build_human_command_packet as _packet_build  # type: ignore
    _PACKET_OK = True
except Exception:
    pass

# Request-type constants — imported from rights matrix
from apps.obsidia_api.brody_rights_authority_matrix import (
    PURE_RESPONSE,
    CONTEXT_ANALYSIS,
    CAPABILITY_SCOPE,
    STRUCTURAL_PREPARATION,
    MEMORY_CANDIDATE,
    OPERATOR_COMMAND_PROPOSAL,
    EXTERNAL_ACCESS_REQUEST,
    ACTION_OR_ACT_REQUEST,
    MEMORY_WRITE_REQUEST,
    TREE_SIGNAL_REQUEST,
    PRIORITY_ADVISORY,
)

_MEMORY_TYPES = {MEMORY_CANDIDATE, MEMORY_WRITE_REQUEST}
_ACTION_TYPES = {ACTION_OR_ACT_REQUEST, MEMORY_WRITE_REQUEST}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _session_dir(session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:64] or "default"
    return _SESSIONS / safe


# ── Sub-routines ──────────────────────────────────────────────────────────────

def _run_session_ledger(
    session_id: str,
    user_message: str,
    response_md: str,
    context_packet: dict,
) -> dict[str, Any]:
    if not _LEDGER_OK or _ledger_build is None:
        return {
            "enabled": False,
            "status": "LEDGER_MODULE_UNAVAILABLE",
            "event_candidate_created": False,
            "memory_write": False,
        }

    # Build boundary-conforming response dict for ledger validator
    resp_obj = {
        "readonly": True,
        "response_only": True,
        "no_external_model_call": True,
        "no_network_call": True,
        "memory_decision": False,
        "allowed_to_decide": False,
        "emits_act": False,
        "emits_allow_hold_block": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "x108_mutation": False,
        "x108_runtime_binding": False,
        "x108_merge": False,
        "real_llm_connected": False,
        "model_provider_bound": False,
        "decision_authority": "KX108_ONLY",
        "response_md": response_md,
        "memory_query": context_packet.get("query", ""),
        "packet_results_count": len(context_packet.get("context_items", [])),
    }

    try:
        result = _ledger_build(
            user_input=user_message,
            response=resp_obj,
            session_dir=_session_dir(session_id),
            session_id=session_id,
        )
        return {
            "enabled": True,
            "status": result.get("status", "LEDGER_PASS"),
            "event_candidate_created": True,
            "event_hash": result.get("event_hash", ""),
            "sequence": result.get("sequence", 0),
            "session_dir": result.get("session_dir", ""),
            "memory_write": False,
        }
    except Exception as exc:
        return {
            "enabled": False,
            "status": f"LEDGER_ERROR:{type(exc).__name__}",
            "event_candidate_created": False,
            "memory_write": False,
        }


def _build_presave_candidate(
    user_message: str,
    response_md: str,
    request_type: str,
) -> dict[str, Any]:
    """Inline presave buffer candidate — no pointer scanning in API context."""
    h = _sha256(user_message + "|" + response_md)
    return {
        "enabled": True,
        "status": "PRESAVE_BUFFER_CANDIDATE_CREATED",
        "presave_candidate": {
            "candidate_hash": h,
            "request_type": request_type,
            "created_at": _now(),
            "source": "BRODY_API_INLINE",
            **AUTOMATION_BOUNDARY,
        },
        "manual_validation_required": True,
    }


def _run_auto_triage(
    user_message: str,
    response_md: str,
    context_packet: dict,
) -> dict[str, Any]:
    if not _TRIAGE_OK or _triage_classify is None or _TriageSealer is None:
        return {
            "enabled": False,
            "zone": "NOT_RUN",
            "memory_intake": False,
            "status": "TRIAGE_MODULE_UNAVAILABLE",
        }

    synthetic = {
        "user_input": user_message,
        "response_md": response_md,
        "memory_query": context_packet.get("query", ""),
        "packet_results_count": len(context_packet.get("context_items", [])),
        # Boundary flags required by triage boundary-alert scanner
        "memory_decision": False,
        "allowed_to_decide": False,
        "emits_act": False,
        "emits_allow_hold_block": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "x108_mutation": False,
        "x108_runtime_binding": False,
        "x108_merge": False,
        "graphiti_index_write": False,
        "decision_authority": "KX108_ONLY",
    }

    try:
        sealer = _TriageSealer()
        item = _triage_classify(synthetic, 1, sealer)
        reflex = item.get("reflex", {})
        return {
            "enabled": True,
            "zone": item.get("zone", "NEANT"),
            "memory_candidate": item.get("memory_candidate", False),
            "review_candidate": item.get("review_candidate", False),
            "reject_candidate": item.get("reject_candidate", True),
            "axes": item.get("axes", []),
            "reasons": item.get("reasons", []),
            "reflex_status": reflex.get("status", "PROCEED_CONTEXT_ONLY"),
            "reflex_alerts": reflex.get("alerts", []),
            "memory_intake": False,
            "status": "TRIAGE_PASS",
        }
    except Exception as exc:
        return {
            "enabled": False,
            "zone": "NOT_RUN",
            "memory_intake": False,
            "status": f"TRIAGE_ERROR:{type(exc).__name__}",
        }


def _run_operator_loop(
    user_message: str,
    request_type: str,
    authority_snapshot: dict,
) -> dict[str, Any]:
    if request_type != OPERATOR_COMMAND_PROPOSAL:
        return {
            "human_command_packet_ready": False,
            "command_gate_classification": "NOT_APPLICABLE",
            "execution_allowed_for_brody": False,
            "brody_execute_allowed": False,
            "human_operator_required": authority_snapshot.get("requires_human_operator", False),
            "human_execution_required": False,
            "copy_only": False,
            "present_packet_to_operator": False,
            "human_command_packet": None,
            "command_copy_block": None,
        }

    if _PACKET_OK and _packet_build is not None:
        try:
            packet = _packet_build({
                "command": user_message,
                "claimed_purpose": "operator_command_proposal_from_brody_api",
                "target_repo": "obsidia-x108-proofs",
                "expected_output": "",
                "rollback_note": "",
            })
            req = packet.get("request", {}) if isinstance(packet.get("request"), dict) else {}
            return {
                "human_command_packet_ready": True,
                "command_gate_classification": packet.get(
                    "classification", "UNKNOWN_COMMAND_REVIEW_REQUIRED"
                ),
                "execution_allowed_for_brody": False,
                "brody_execute_allowed": False,
                "human_operator_required": True,
                "human_execution_required": True,
                "copy_only": True,
                "present_packet_to_operator": True,
                "packet_status": packet.get("status", ""),
                "human_command_packet": packet,
                "command_copy_block": {
                    "label": "HUMAN_OPERATOR_COMMAND_PACKET_COPY_ONLY",
                    "command": req.get("command", ""),
                    "claimed_purpose": req.get("claimed_purpose", ""),
                    "target_repo": req.get("target_repo", ""),
                    "expected_output": req.get("expected_output", ""),
                    "rollback_note": req.get("rollback_note", ""),
                    "warning": "Manual human review required. Brody cannot execute.",
                },
            }
        except Exception:
            pass

    return {
        "human_command_packet_ready": False,
        "command_gate_classification": "COMMAND_PACKET_MODULE_UNAVAILABLE",
        "execution_allowed_for_brody": False,
        "brody_execute_allowed": False,
        "human_operator_required": True,
        "human_execution_required": False,
        "copy_only": False,
        "present_packet_to_operator": False,
        "human_command_packet": None,
        "command_copy_block": None,
    }


# ── Intent routing → next/blocked steps (Phase 3) ────────────────────────────

def _route_steps(
    request_type: str,
    authority_snapshot: dict,
    triage: dict,
    presave: dict,
    operator_loop: dict,
) -> tuple[list[str], list[str]]:
    allowed: list[str] = ["final_answer_advisory", "context_packet_readonly", "authority_snapshot_readonly"]
    blocked: list[str] = ["emits_act", "kernel_mutation", "bypass_x108"]

    if request_type == PURE_RESPONSE:
        allowed += ["respond_naturally", "contextualize", "describe_perimeter"]
        blocked += ["memory_write", "graphiti_write"]

    elif request_type == CONTEXT_ANALYSIS:
        allowed += ["read_graphiti_readonly", "read_context_packet", "diagnostic_advisory", "explain_capabilities"]
        blocked += ["modify_memory", "memory_write", "decide"]

    elif request_type == STRUCTURAL_PREPARATION:
        allowed += ["context_packet_candidate", "ir_candidate_readonly", "structure_proposal", "formulate_plan_advisory"]
        blocked += ["execute_packet", "memory_write", "graphiti_write"]

    elif request_type in _MEMORY_TYPES:
        allowed += ["presave_buffer_candidate", "auto_triage_candidate", "needs_human_review_gate", "explain_6_gates"]
        blocked += ["graphiti_write", "neo4j_write", "auto_promote_candidate", "memory_intake_direct"]
        if triage.get("zone") == "CRISTAL":
            allowed.append("mark_promotion_ready_for_human_review")
        if presave.get("enabled"):
            allowed.append("session_presave_buffer_candidate_created")

    elif request_type == OPERATOR_COMMAND_PROPOSAL:
        allowed += ["human_command_packet_candidate", "command_gate_classification", "sequence_proposal"]
        blocked += ["execute_command_as_brody", "git_mutation_without_approval", "auto_run"]
        if operator_loop.get("human_command_packet_ready"):
            allowed.append("present_packet_to_operator")

    elif request_type in _ACTION_TYPES:
        allowed += ["explain_refusal", "action_candidate_for_x108", "document_in_context_packet"]
        blocked += ["authorize_act", "emit_act", "graphiti_write_direct", "bypass_x108_decision"]

    elif request_type == EXTERNAL_ACCESS_REQUEST:
        allowed += ["get_only_candidate_if_allowlisted", "prepare_dry_run_packet", "explain_activation_conditions"]
        blocked += ["runtime_fetch_without_authorization", "post_or_mutation", "scrape_without_operator_gate"]

    elif request_type == CAPABILITY_SCOPE:
        allowed += [
            "explain_brody_may_list",
            "explain_brody_must_not_list",
            "explain_human_operator_role",
            "explain_kx108_decision_authority",
            "explain_memory_candidate_only",
        ]
        blocked += ["decide", "emits_act", "ecrire_memoire_automatiquement", "bypass_x108"]

    elif request_type in (TREE_SIGNAL_REQUEST, PRIORITY_ADVISORY):
        allowed += ["read_safe_trees_T13_T29", "advisory_prioritization", "cite_source_context"]
        blocked += ["trigger_blocked_trees", "memory_write", "decide"]

    # Always
    allowed.append("session_ledger_candidate_readonly")

    return sorted(set(allowed)), sorted(set(blocked))


# ── Main entry point ──────────────────────────────────────────────────────────

def run_brody_automation_layer(
    session_id: str,
    user_message: str,
    language: str,
    request_type: str,
    authority_snapshot: dict,
    context_packet: dict,
    response_md: str,
) -> dict[str, Any]:
    """
    Brody Automation Layer — main orchestrator function.

    Chains existing modules by request_type.
    Returns automation_snapshot to be added to /api/brody/chat payload.
    """

    # Phase 3 routing: determine which modules to activate

    run_memory_pipeline = request_type in _MEMORY_TYPES

    # 1. Session ledger (always)
    ledger = _run_session_ledger(session_id, user_message, response_md, context_packet)

    # 2. Presave buffer (memory requests only)
    presave = (
        _build_presave_candidate(user_message, response_md, request_type)
        if run_memory_pipeline
        else {
            "enabled": False,
            "status": "NOT_APPLICABLE_FOR_REQUEST_TYPE",
            "presave_candidate": None,
            "manual_validation_required": True,
        }
    )

    # 3. Auto-triage (memory requests only)
    triage = (
        _run_auto_triage(user_message, response_md, context_packet)
        if run_memory_pipeline
        else {
            "enabled": False,
            "zone": "NOT_RUN",
            "memory_intake": False,
            "status": "NOT_APPLICABLE_FOR_REQUEST_TYPE",
        }
    )

    # 4. Memory candidate pipeline state
    candidate_created = presave.get("enabled", False)
    needs_review = candidate_created or triage.get("review_candidate", False)
    memory_candidate_pipeline = {
        "candidate_created": candidate_created,
        "needs_review": needs_review,
        "review_gate_status": "NEEDS_HUMAN_REVIEW" if needs_review else "NOT_APPLICABLE",
        "gates_passing": 0,
        "gates_total": 6,
        "graphiti_write": False,
        "neo4j_write": False,
    }

    # 5. Operator loop
    operator_loop = _run_operator_loop(user_message, request_type, authority_snapshot)

    # 6. Next / blocked steps
    next_steps, blocked_steps = _route_steps(
        request_type, authority_snapshot, triage, presave, operator_loop
    )

    # 7. Writable memory protocol — sourced from WRITABLE_MEMORY_ACTIVATION_CHECKLIST.md
    writable_memory_protocol = {
        "source_doc": "WRITABLE_MEMORY_ACTIVATION_CHECKLIST.md",
        "writable_memory_active": False,
        "protocol_state": "PROTOCOL_CANDIDATE_ONLY",
        "gates_passing": "0/6",
        "operator_approval": False,
        "real_import_ready": False,
    }

    return {
        "session_ledger": ledger,
        "presave_buffer": presave,
        "auto_triage": triage,
        "memory_candidate_pipeline": memory_candidate_pipeline,
        "writable_memory_protocol": writable_memory_protocol,
        "operator_loop": operator_loop,
        "next_allowed_steps": next_steps,
        "blocked_steps": blocked_steps,
        "request_type": request_type,
        "created_at": _now(),
        **AUTOMATION_BOUNDARY,
    }
