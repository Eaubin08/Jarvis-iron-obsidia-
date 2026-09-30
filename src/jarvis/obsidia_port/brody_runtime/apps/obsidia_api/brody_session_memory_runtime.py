"""
Foundation B — Brody Session Memory / Follow-up Runtime
==========================================================
Canonical runtime entry point for Foundation B: Session Memory / Follow-up.

Extends brody_session_memory_adapter with:
  remember_session_turn(...)     — candidate-only, no actual write, advisory
  resolve_session_followup(...)  — extract prior context for current message
  build_session_memory_snapshot(...) — delegate + overlay foundation fields

memory_write=false — all session turn records are candidates for operator review.
Boundary: readonly, KX108_ONLY.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from apps.obsidia_api.brody_session_memory_adapter import (
    build_session_memory_snapshot as _build_from_adapter,
)

_FOLLOWUP_KEYWORDS = [
    "reprends", "reprend",
    "développe", "developpe",
    "plus de structure",
    "point précédent", "point precedent",
    "ce point", "celui-là",
    "continue sur ça",
]


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def remember_session_turn(
    session_id: str = "local",
    user_input: str = "",
    response_md: str = "",
    memory_query: str = "",
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    """
    Build a session turn candidate. Does NOT write to disk.
    Returns the candidate dict for operator review.
    memory_write=false — candidate is advisory only.
    """
    turn_data = {
        "session_id": session_id,
        "user_input": (user_input or "")[:500],
        "response_md": (response_md or "")[:800],
        "memory_query": (memory_query or "")[:200],
    }
    event_hash = _sha256(json.dumps(turn_data, sort_keys=True, ensure_ascii=False))
    return {
        "candidate_type": "SESSION_TURN_CANDIDATE",
        "candidate_status": "PENDING_OPERATOR_REVIEW",
        "memory_write": False,
        "graphiti_write": False,
        "neo4j_write": False,
        "write_blocked": True,
        "write_blocked_reason": "FOUNDATION_B_READONLY_ADVISORY_ONLY",
        "event_hash": event_hash,
        "turn_data": turn_data,
        "decision_authority": "KX108_ONLY",
        "note": "Session turn candidate prepared. No write performed. Operator review required.",
    }


def resolve_session_followup(
    session_id: str = "local",
    current_message: str = "",
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    """
    Resolve follow-up context from session ledger for the current message.
    Returns prior context summary without writing.
    """
    snap = _build_from_adapter(
        workspace_root=workspace_root,
        session_id=session_id,
        current_user_message=current_message,
    )
    msg_lower = (current_message or "").lower()
    explicit_followup = any(k in msg_lower for k in _FOLLOWUP_KEYWORDS)

    return {
        "followup_resolved": snap.get("followup_supported", False),
        "explicit_followup_detected": explicit_followup,
        "prior_topic": snap.get("conversation_topic", ""),
        "last_turn_context": snap.get("last_turn_context", {}),
        "session_ledger_found": snap.get("session_ledger_v2_found", False),
        "record_count": snap.get("record_count", 0),
        "memory_write": False,
        "decision_authority": "KX108_ONLY",
    }


def build_session_memory_snapshot(
    workspace_root: Path | None = None,
    session_id: str = "local",
    current_user_message: str = "",
) -> dict[str, Any]:
    """
    Runtime-layer session memory snapshot (Foundation B).
    Delegates to adapter, overlays foundation/status fields.
    """
    snap = _build_from_adapter(
        workspace_root=workspace_root,
        session_id=session_id,
        current_user_message=current_user_message,
    )

    ledger_found = snap.get("session_ledger_v2_found", False)
    followup = snap.get("followup_supported", False)

    runtime_status = "FOUNDATION_B_READY" if (ledger_found and followup) else "FOUNDATION_B_PARTIAL"

    snap["foundation"] = "SESSION_MEMORY_FOLLOWUP"
    snap["status"] = runtime_status
    snap["source_mode"] = "EXISTING_SESSION_MEMORY_ONLY"
    snap["session_ledger"] = ledger_found
    snap["presave_buffer"] = snap.get("presave_buffer_found", False)
    snap["followup_resolver"] = snap.get("followup_resolver", "NOT_IMPLEMENTED")
    snap["last_turn_context"] = snap.get("last_turn_context", {})
    snap["conversation_topic"] = snap.get("conversation_topic", "")
    snap["used_by_api_now"] = snap.get("used_by_api_now", False)
    snap["memory_write"] = False
    snap["graphiti_write"] = False
    snap["neo4j_write"] = False
    snap["decision_authority"] = "KX108_ONLY"
    return snap
