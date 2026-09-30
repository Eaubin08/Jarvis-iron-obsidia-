"""
Foundation B — Brody Session Memory / Follow-up Adapter
==========================================================
Thin wrapper over session_memory_ledger_readonly V2.

Reads existing session ledger JSONL records for a given session_id.
Provides:
  - last_turn_context: previous user message + response excerpt
  - conversation_topic: detected from last messages
  - followup_supported: whether session has previous records

No invention — session ledger format is defined by
brody_session_memory_ledger_readonly_v2.py.

Boundary: readonly, KX108_ONLY, no write, no Graphiti.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_dir(workspace: Path, session_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:64] or "default"
    return workspace / "_local_audits" / "brody_sessions" / safe


def _detect_followup_request(user_message: str) -> bool:
    """Detect if user is explicitly asking for a followup/continuation."""
    if not user_message:
        return False
    msg = user_message.lower()
    patterns = [
        "reprends", "reprend",
        "développe", "developpe",
        "plus de structure",
        "point précédent", "point precedent",
        "ce point", "celui-là",
        "continue sur ça",
    ]
    return any(p in msg for p in patterns)


def build_session_memory_snapshot(
    workspace_root: Path | None = None,
    session_id: str = "local",
    current_user_message: str = "",
) -> dict[str, Any]:
    """
    Build session_memory_snapshot from existing session ledger.

    Reads the SESSION_LEDGER.jsonl for the given session_id and extracts
    the last turn context and conversation topic.

    Returns dict with: session_ledger_found, last_turn_context,
    conversation_topic, followup_supported, record_count.
    """
    workspace = workspace_root or Path(__file__).resolve().parents[2]
    sdir = _session_dir(workspace, session_id)

    ledger_path = sdir / "SESSION_LEDGER.jsonl"
    index_path = sdir / "SESSION_INDEX.json"

    session_ledger_found = ledger_path.exists()
    jsonl_trace = False
    hash_chain = False
    session_id_found = False
    previous_event_hash = False
    record_count = 0
    last_turn_context: dict[str, Any] = {}
    conversation_topic = ""
    followup_supported = False

    if session_ledger_found:
        try:
            lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
            records = []
            for line in lines:
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        pass

            record_count = len(records)
            jsonl_trace = record_count > 0

            # Check hash chain
            if records and all(r.get("event_hash") for r in records):
                hash_chain = True

            # Check session_id
            if records and all(r.get("session_id") for r in records):
                session_id_found = True

            # Check previous_event_hash chain
            if records and all(r.get("previous_event_hash") for r in records):
                previous_event_hash = True

            # Last turn context
            if records:
                last = records[-1]
                last_turn_context = {
                    "sequence": last.get("sequence"),
                    "user_input": last.get("user_input", "")[:200],
                    "response_md": (last.get("response_md", "") or "")[:300],
                    "memory_query": last.get("memory_query", ""),
                    "event_hash": last.get("event_hash", ""),
                    "triage_status": last.get("triage_status", ""),
                }

                # Simple topic detection from last user input
                last_input = last.get("user_input", "")
                if last_input:
                    words = last_input.split()[:8]
                    conversation_topic = " ".join(words) if words else last_input[:80]

                followup_supported = record_count >= 1

        except Exception:
            session_ledger_found = False

    # Also check presave buffer availability
    presave_ptr = workspace / "CURRENT_BRODY_SESSION_PRESAVE_BUFFER_READONLY.txt"
    presave_buffer_found = presave_ptr.exists()

    # Followup detection: only true if user explicitly requests followup
    # AND previous turn context exists
    explicit_followup = _detect_followup_request(current_user_message)
    followup_resolved = bool(
        explicit_followup
        and followup_supported
        and last_turn_context
        and last_turn_context.get("user_input")
    )

    used_by_api = session_ledger_found and followup_supported

    return {
        "source_type": "LOCAL_EXISTING_SOURCES",
        "source_mode": "SESSION_LEDGER_V2_EXISTING_ONLY",
        "status": "BRODY_SESSION_MEMORY_FOLLOWUP_SOURCE_MAP_PASS",
        "created_at": _now(),
        "session_ledger_v2_found": session_ledger_found,
        "jsonl_trace": jsonl_trace,
        "hash_chain": hash_chain,
        "session_id": session_id_found,
        "previous_event_hash": previous_event_hash,
        "record_count": record_count,
        "presave_buffer_found": presave_buffer_found,
        "followup_supported": followup_supported,
        "followup_requested": explicit_followup,
        "followup_resolved": followup_resolved,
        "followup_resolver": "PARTIAL" if session_ledger_found else "NOT_IMPLEMENTED",
        "last_turn_context": last_turn_context,
        "previous_user_message": last_turn_context.get("user_input", ""),
        "conversation_topic": conversation_topic,
        "current_user_message_excerpt": current_user_message[:200] if current_user_message else "",
        "used_by_api_now": used_by_api,
        "session_dir": str(sdir) if session_ledger_found else "",
        "memory_write": False,
        "graphiti_write": False,
        "neo4j_write": False,
        "emits_act": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "decision_authority": "KX108_ONLY",
    }
