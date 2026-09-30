"""Brody native contracts packet.

Phase 11B.

This module does not decide, act, write memory, mutate the
kernel, or mutate X108. It only normalizes already-stabilized authority and
boundary contracts into one packet for /api/brody/chat.
"""
from __future__ import annotations

from typing import Any

from apps.obsidia_api.brody_rights_authority_matrix import (
    classify_request_authority,
    get_brody_capability_matrix,
)


BOUNDARY_CONTRACT: dict[str, Any] = {
    "readonly": True,
    "advisory_only": True,
    "context_signal_only": True,
    "allowed_to_decide": False,
    "allowed_to_act": False,
    "emits_act": False,
    "emits_verdict": False,
    "memory_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "real_action": False,
    "decision_authority": "KX108_ONLY",
}

FORBIDDEN_OUTPUT_CONTRACT: dict[str, Any] = {
    "forbidden_tokens_as_authority": [
        "ALLOW",
        "HOLD",
        "BLOCK",
        "ACT",
        "DECIDE",
        "VERDICT",
    ],
    "forbidden_fields": [
        "decision",
        "verdict",
        "action",
        "act",
        "execution_request",
        "kernel_patch",
        "x108_patch",
        "memory_commit",
    ],
    "allowed_if_redacted_or_descriptive": True,
    "note": "Conceptual mentions are allowed; sovereign emission is not.",
}

SIGNAL_CONTRACT: dict[str, Any] = {
    "allowed_signal_families": [
        "context_signal",
        "memory_signal",
        "tree_signal",
        "semantic_signal",
        "automation_candidate",
        "ir_reduction_candidate",
        "os_reverse_projection",
        "boundary_warning",
        "proof_pointer",
        "trace_pointer",
    ],
    "forbidden_signal_families": [
        "decision",
        "verdict",
        "act",
        "execution",
        "kernel_patch",
        "x108_patch",
        "memory_commit",
    ],
    "decision_authority": "KX108_ONLY",
    "context_signal_only": True,
}

KERNEL_CONTRACT: dict[str, Any] = {
    "kernel": "X108/KX108",
    "decision_authority": "KX108_ONLY",
    "brody_kernel_access": "READONLY_CONTEXT_ONLY",
    "brody_can_mutate_kernel": False,
    "brody_can_mutate_x108": False,
    "brody_can_authorize_act": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "requires_kx108_for_irreversible_action": True,
}

AUTHORITY_CONTRACT: dict[str, Any] = {
    "decision_authority": "KX108_ONLY",
    "brody_authority": "ADVISORY_ONLY",
    "operator_authority": "REQUEST_ONLY",
    "memory_authority": "CANDIDATE_ONLY",
    "automation_authority": "CANDIDATE_ONLY",
    "tree_authority": "CONTEXT_SIGNAL_ONLY",
    "os_trad_authority": "TRANSLATION_ONLY",
    "ir_authority": "REDUCTION_ONLY",
    "os_reverse_authority": "PROJECTION_ONLY",
    "x108_authority": "SOLE_DECISION_LAYER",
}


def build_permission_matrix(authority_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return explicit role permissions for Brody native payload."""
    auth = authority_snapshot if isinstance(authority_snapshot, dict) else {}

    requires_kx108 = bool(auth.get("requires_kx108_decision", False))
    requires_human = bool(auth.get("requires_human_operator", False))
    requires_memory_gate = bool(auth.get("requires_memory_gate", False))

    return {
        "brody": {
            "can_read": True,
            "can_contextualize": True,
            "can_structure_response": True,
            "can_prepare_candidate": True,
            "can_prepare_memory_candidate": True,
            "can_decide": False,
            "can_act": False,
            "can_authorize_act": False,
            "can_emit_verdict": False,
            "can_write_memory": False,
            "can_mutate_kernel": False,
            "can_mutate_x108": False,
            "decision_authority": "KX108_ONLY",
        },
        "operator": {
            "can_request": True,
            "can_confirm": True,
            "can_review_candidates": True,
            "can_force_decision": False,
            "can_bypass_x108": False,
            "requires_human_operator": requires_human,
        },
        "memory": {
            "can_read": True,
            "can_prepare_candidate": True,
            "can_commit": False,
            "can_auto_triage": False,
            "requires_memory_gate": requires_memory_gate,
            "memory_write": False,
        },
        "automation": {
            "can_prepare": True,
            "can_execute": False,
            "requires_x108_decision": requires_kx108,
            "requires_human_operator": requires_human,
            "emits_act": False,
            "real_action": False,
        },
        "trees": {
            "can_activate_context": True,
            "can_decide": False,
            "can_act": False,
            "context_signal_only": True,
        },
        "os_trad": {
            "can_translate": True,
            "can_decide": False,
            "can_act": False,
        },
        "ir_candidate": {
            "can_reduce": True,
            "can_prepare_candidate": True,
            "can_decide": False,
            "can_act": False,
        },
        "os_reverse": {
            "can_project": True,
            "can_decide": False,
            "can_act": False,
        },
        "x108": {
            "can_decide": True,
            "can_authorize_act": True,
            "sole_decision_authority": True,
        },
    }


def build_memory_contract(authority_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    auth = authority_snapshot if isinstance(authority_snapshot, dict) else {}
    return {
        "memory_read": True,
        "memory_candidate_prepare": True,
        "memory_write": False,
        "memory_commit": False,
        "auto_triage": False,
        "presave": False,
        "requires_memory_gate": bool(auth.get("requires_memory_gate", False)),
        "requires_operator_validation": True,
        "requires_x108_if_actionable": bool(auth.get("requires_kx108_decision", False)),
        "decision_authority": "KX108_ONLY",
    }


def build_automation_contract(authority_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    auth = authority_snapshot if isinstance(authority_snapshot, dict) else {}
    return {
        "automation_snapshot": True,
        "can_prepare_candidate": True,
        "can_execute": False,
        "requires_human_operator": bool(auth.get("requires_human_operator", False)),
        "requires_x108_decision": bool(auth.get("requires_kx108_decision", False)),
        "emits_act": False,
        "real_action": False,
        "dry_run_only": True,
        "next_safe_step": "prepare_candidate_for_x108",
        "decision_authority": "KX108_ONLY",
    }


def build_tree_policy_contract(authority_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    auth = authority_snapshot if isinstance(authority_snapshot, dict) else {}
    tree_policy = auth.get("tree_policy", {}) if isinstance(auth.get("tree_policy", {}), dict) else {}
    return {
        "tree_count": tree_policy.get("total_trees", tree_policy.get("tree_count", 34)),
        "activation_allowed": True,
        "context_signal_only": True,
        "tree_decision": False,
        "tree_action": False,
        "blocked_action": True,
        "blocked_memory": True,
        "decision_authority": "KX108_ONLY",
        "source_tree_policy": tree_policy,
    }


def build_translation_projection_contract() -> dict[str, Any]:
    return {
        "os_trad": {
            "role": "translate_input_to_units",
            "can_decide": False,
            "can_act": False,
        },
        "ir_candidate": {
            "role": "reduce_to_structured_candidate",
            "can_decide": False,
            "can_act": False,
        },
        "os_reverse": {
            "role": "project_readable_response",
            "can_decide": False,
            "can_act": False,
        },
        "decision_authority": "KX108_ONLY",
    }


def build_audit_contract() -> dict[str, Any]:
    return {
        "trace_required": True,
        "boundary_required": True,
        "source_required": True,
        "phase_required": True,
        "bom_free_required": True,
        "tests_required": [
            "pytest",
            "terminal_smoke",
            "ui_build",
            "boundary_assertions",
        ],
        "commit_required_for_freeze": True,
    }


def build_brody_contracts_packet(
    user_message: str,
    authority_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the normalized native contracts packet for /api/brody/chat."""
    auth = authority_snapshot if isinstance(authority_snapshot, dict) and authority_snapshot else classify_request_authority(user_message, {}, {})
    capability_matrix = get_brody_capability_matrix()

    brody_contract = {
        "brody_may": auth.get("brody_may", []),
        "brody_must_not": auth.get("brody_must_not", []),
        "request_type": auth.get("request_type", "PURE_RESPONSE"),
        "response_mode": auth.get("response_mode", "FULL_ANSWER"),
        "requires_human_operator": bool(auth.get("requires_human_operator", False)),
        "requires_kx108_decision": bool(auth.get("requires_kx108_decision", False)),
        "requires_memory_gate": bool(auth.get("requires_memory_gate", False)),
        "requires_api_bridge_gate": bool(auth.get("requires_api_bridge_gate", False)),
        "decision_authority": "KX108_ONLY",
    }

    packet = {
        "source": "BRODY_NATIVE_CONTRACTS_PACKET_V1",
        "status": "CONTRACTS_PACKET_READY",
        "readonly": True,
        "decision_authority": "KX108_ONLY",
        "authority_contract": AUTHORITY_CONTRACT,
        "brody_contract": brody_contract,
        "permission_matrix": build_permission_matrix(auth),
        "kernel_contract": KERNEL_CONTRACT,
        "boundary_contract": BOUNDARY_CONTRACT,
        "signal_contract": SIGNAL_CONTRACT,
        "forbidden_output_contract": FORBIDDEN_OUTPUT_CONTRACT,
        "memory_contract": build_memory_contract(auth),
        "automation_contract": build_automation_contract(auth),
        "tree_policy_contract": build_tree_policy_contract(auth),
        "translation_projection_contract": build_translation_projection_contract(),
        "audit_contract": build_audit_contract(),
        "capability_matrix_ref": {
            "status": "AVAILABLE",
            "categories": capability_matrix.get("categories", []),
            "sources": capability_matrix.get("sources", []),
        },
    }

    return packet
