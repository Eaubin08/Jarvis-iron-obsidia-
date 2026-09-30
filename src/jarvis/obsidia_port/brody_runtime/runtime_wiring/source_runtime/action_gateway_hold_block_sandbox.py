"""
P54 — Action Gateway Hold/Block Sandbox.

Connects P53 dry-run packet to a real HOLD/BLOCK evaluation via
runtime_wiring.x108_admission_stub.evaluate_dry_run().

BLOCK > HOLD > ALLOW_CONTEXT_ONLY — priority order from x108_admission_stub.
NEVER ACT. NEVER real_action_enabled. NEVER runtime_allowed_now=True.
KX108_ONLY. emits_act=False at all times.

Mapping:
  EMAIL_SEND       → BLOCK
  BLOCKCHAIN_TX    → BLOCK
  MEMORY_WRITE     → BLOCK
  GRAPHITI_WRITE   → BLOCK
  EXTERNAL_API_CALL→ BLOCK
  FILE_MUTATION    → HOLD
  GENERAL_ACTION   → HOLD
  NO_ACTION        → ALLOW_CONTEXT_ONLY
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

_BOUNDARY = {
    "readonly": True,
    "emits_act": False,
    "real_action_enabled": False,
    "can_execute_real_action": False,
    "memory_write": False,
    "graphiti_write": False,
    "neo4j_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "world_action": False,
    "decision_authority": "KX108_ONLY",
    "runtime_allowed_now": False,
    "x108_required_before_act": True,
}

# Sandbox verdict mapping — action type → verdict
_BLOCK_ACTION_TYPES = frozenset({
    "EMAIL_SEND",
    "BLOCKCHAIN_TX",
    "MEMORY_WRITE",
    "GRAPHITI_WRITE",
    "EXTERNAL_API_CALL",
})
_HOLD_ACTION_TYPES = frozenset({
    "FILE_MUTATION",
    "GENERAL_ACTION",
})

# Action type patterns (same as P53 for consistency)
_ACTION_PATTERNS: list[tuple[list[str], str, str]] = [
    (["mail", "email", "envoie", "envoyer", "send mail", "send email"],
     "EMAIL_SEND", "HIGH"),
    (["transaction", "blockchain", "crypto", "wallet", "token", "gencoin",
      "defi", "défi", "on-chain", "onchain", "smart contract", "nft"],
     "BLOCKCHAIN_TX", "CRITICAL"),
    (["écris en mémoire", "écrire en mémoire", "write memory", "sauvegarde mémoire",
      "memory write", "save to memory", "enregistre en mémoire"],
     "MEMORY_WRITE", "HIGH"),
    (["graphiti write", "écrire graphiti", "neo4j write", "écrire neo4j",
      "write graphiti", "write neo4j"],
     "GRAPHITI_WRITE", "HIGH"),
    (["appelle une api", "api externe", "appel api", "external api",
      "webhook", "http post", "http put", "curl", "requests.post"],
     "EXTERNAL_API_CALL", "HIGH"),
    (["modifie ce fichier", "modify file", "file mutation", "write file",
      "edit file", "delete file", "écrire fichier"],
     "FILE_MUTATION", "MEDIUM"),
    (["fais une action", "exécute", "execute", "run action", "lance une action",
      "perform action", "do action"],
     "GENERAL_ACTION", "MEDIUM"),
]


def _detect_action_type(query: str) -> tuple[bool, str, str]:
    q = query.lower()
    for keywords, action_type, risk_class in _ACTION_PATTERNS:
        if any(kw in q for kw in keywords):
            return True, action_type, risk_class
    return False, "NO_ACTION", "NONE"


def _classify_sandbox_verdict(action_type: str) -> str:
    if action_type in _BLOCK_ACTION_TYPES:
        return "BLOCK"
    if action_type in _HOLD_ACTION_TYPES:
        return "HOLD"
    return "ALLOW_CONTEXT_ONLY"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_context_id(query: str) -> str:
    digest = hashlib.sha256(f"P54:{query[:80]}".encode()).hexdigest()[:12]
    return f"p54-ctx-{digest}"


def _run_x108_evaluation(action_detected: bool, action_type: str) -> dict:
    """
    Call the real evaluate_dry_run() with a valid ContextPacket.
    critical_action_requested=True for any detected action → HOLD from x108 stub.
    The sandbox then overrides to BLOCK for high-risk action types.
    Never passes a packet with boundary violations.
    """
    try:
        from runtime_wiring.x108_admission_stub import evaluate_dry_run
        from runtime_wiring.packet_types import ContextPacket

        pkt = ContextPacket(
            context_id=_make_context_id(action_type),
            source="P54_ACTION_GATEWAY_SANDBOX",
            source_status="SPEC_FUTURE",
            claim_scope="CLAIMABLE_SPEC_ONLY",
            boundary="P54_SANDBOX_DRY_RUN",
            timestamp_or_tick=_utcnow(),
            advisory_only=True,
            readonly=True,
            runtime_allowed_now=False,
            emits_act=False,
            emits_decision=False,
            decision_authority="KX108_ONLY",
            labels=["P54", "ACTION_GATEWAY", action_type],
            notes=f"P54 sandbox packet for action_type={action_type}",
        )
        pkt.validate_invariants()

        ticket = evaluate_dry_run(
            packets=[pkt],
            envelope=None,
            critical_action_requested=action_detected,
        )

        return {
            "x108_evaluation_status": "EVALUATED",
            "x108_ticket_id": ticket.ticket_id,
            "x108_decision": ticket.decision,
            "x108_gate_status": ticket.x108_gate_status,
            "x108_reason_codes": ticket.reason_codes,
            "x108_dry_run": ticket.dry_run,
            "x108_emits_act": ticket.emits_act,
            "x108_error": None,
        }
    except Exception as exc:
        return {
            "x108_evaluation_status": "EVALUATION_ERROR",
            "x108_decision": "BLOCK",
            "x108_gate_status": "X108_FAIL_CLOSED",
            "x108_reason_codes": ["EVALUATION_ERROR", type(exc).__name__],
            "x108_dry_run": True,
            "x108_emits_act": False,
            "x108_error": type(exc).__name__,
        }


def build_action_gateway_sandbox_state(query: str = "") -> dict:
    """
    Return the P54 Action Gateway Hold/Block sandbox state for a query.

    Uses real runtime_wiring.x108_admission_stub.evaluate_dry_run().
    Sandbox verdict: BLOCK > HOLD > ALLOW_CONTEXT_ONLY.
    real_action_enabled=False, emits_act=False at all times.
    """
    action_detected, action_type, risk_class = _detect_action_type(query)
    sandbox_verdict = _classify_sandbox_verdict(action_type)

    # Run real X108 evaluation
    x108_eval = _run_x108_evaluation(action_detected, action_type)

    # Sandbox can override x108 HOLD to BLOCK for high-risk types
    # (x108 stub returns HOLD for critical_action_requested=True,
    #  sandbox adds BLOCK override for _BLOCK_ACTION_TYPES)
    final_sandbox_verdict = sandbox_verdict  # sandbox authority wins

    act_blocked_reason = "P54_SANDBOX_NO_ACT"
    if action_type in _BLOCK_ACTION_TYPES:
        act_blocked_reason = f"P54_SANDBOX_BLOCK_{action_type}"
    elif action_type in _HOLD_ACTION_TYPES:
        act_blocked_reason = f"P54_SANDBOX_HOLD_{action_type}_PENDING_KX108"

    return {
        "audit_id": "P54_ACTION_GATEWAY_HOLD_BLOCK_SANDBOX",
        "audit_date": "2026-06-04",
        # Sandbox status
        "action_gateway_sandbox_status": "ACTIVE_HOLD_BLOCK_SANDBOX",
        "activation_level": "LEVEL_3_HOLD_GATE_CANDIDATE",
        "sandbox_enabled": True,
        # Sandbox verdict
        "sandbox_verdict": final_sandbox_verdict,
        "act_blocked_reason": act_blocked_reason,
        # Action detection
        "action_request_detected": action_detected,
        "detected_action_type": action_type,
        "action_risk_class": risk_class,
        # X108 evaluation
        "x108_evaluation": x108_eval,
        "x108_ticket_id": x108_eval.get("x108_ticket_id", ""),
        "x108_gate_decision": x108_eval.get("x108_decision", "BLOCK"),
        # Invariants — always False
        "can_evaluate_hold_block": True,
        "can_emit_act": False,
        "allowed_to_act": False,
        "p54_status": "P54_ACTION_GATEWAY_HOLD_BLOCK_SANDBOX_READY",
        **_BOUNDARY,
    }
