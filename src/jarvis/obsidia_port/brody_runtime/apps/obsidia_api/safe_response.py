"""
Safe response wrapper — ensures every API response carries sovereignty invariants.

F47.1 — Protected response envelope hardening:
    Sovereignty flags are re-applied AFTER data merge (data.update then sovereignty
    overwrites). A module returning an unsafe allowed_to_decide truthy value cannot propagate that
    value through this layer. KX108_ONLY is always enforced at output.

F47.2 — controlled_response.text sanitizer:
    sanitize_user_facing_text() applies word-boundary replacement of forbidden
    sovereign-decision tokens in any user-echoing text field.
    safe_backend_response() now also sanitizes controlled_response.text.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any

# Only mask when Brody appears to be actively EMITTING a sovereign verdict/action.
# Conceptual mentions ("Brody ne peut pas autoriser ACT") are allowed through.
_EMISSION_RE = re.compile(
    r"(?:"
    r"j['']?[eé]mets?\s+(?:un\s+)?"
    r"|j['']?autorise\s+(?:un\s+)?"
    r"|je\s+d[eé]clenche\s+(?:un\s+)?"
    r"|brody\s+[eé]met\s+"
    r"|brody\s+autorise\s+"
    r"|brody\s+d[eé]clenche\s+"
    r")"
    r"(ACT|HOLD|BLOCK|ALLOW|VERDICT|DECIDE)\b",
    re.IGNORECASE,
)

# F47.2 — word-boundary replacement for isolated forbidden tokens in user-facing text.
# Targets tokens that appear as standalone words (not substrings of e.g. "transaction").
# Applied to controlled_response.text and any user-echoing field.
_ISOLATED_TOKEN_RE = re.compile(
    r"\b(ALLOW|HOLD|BLOCK|ACT|DECIDE|VERDICT)\b",
    re.IGNORECASE,
)

# F47.1 — sovereignty flags that are always enforced after data merge.
# These values can never be overridden by a module response payload.
_SOVEREIGNTY_PROTECTED: dict[str, Any] = {
    "decision_authority": "KX108_ONLY",
    "allowed_to_decide": False,
    "readonly": True,
    "advisory_only": True,
    "context_signal_only": True,
    "emits_act": False,
    "emits_verdict": False,
    "memory_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "brody_decision": False,
    "real_action": False,
}


def strip_forbidden_tokens(text: str) -> str:
    """Mask only sovereign-emission patterns — not conceptual mentions.
    'Brody ne peut pas autoriser ACT' passes through unchanged.
    'j'émets ACT' becomes 'j'émets A***'.
    """
    def _mask(m: re.Match) -> str:
        token = m.group(1)
        return m.group(0)[: -len(token)] + token[0] + "***"
    return _EMISSION_RE.sub(_mask, text)


def sanitize_user_facing_text(text: str) -> str:
    """F47.2 — Replace isolated forbidden sovereign-decision tokens in user-facing text.

    Word-boundary only — no false positives on substrings:
        'transaction' → unchanged  ('ACT' not word-boundary)
        'interaction' → unchanged
        'artifact'    → unchanged
        'ACTOR'       → unchanged
        'ALLOW'       → '[REDACTED]'
        'We must DECIDE' → 'We must [REDACTED]'

    Applied to controlled_response.text and any field that echoes user_input.
    NOT applied to internal traces, proof manifests, or technical fields.
    """
    return _ISOLATED_TOKEN_RE.sub("[REDACTED]", text)


def safe_backend_response(
    data: dict[str, Any] | None = None,
    source: str = "REAL_BACKEND",
) -> dict[str, Any]:
    """Wrap any API response with sovereignty invariants.

    F47.1 merge order: data is merged first, then _SOVEREIGNTY_PROTECTED is
    re-applied unconditionally — sovereignty flags always win.
    """
    # Start from data (preserves all module-provided non-sovereignty fields)
    merged: dict[str, Any] = dict(data) if data else {}
    # Re-apply sovereignty — overwrites any conflicting values from data
    merged.update(_SOVEREIGNTY_PROTECTED)
    # Non-sovereignty metadata (always fresh)
    merged["source"] = source
    merged["timestamp"] = datetime.now(timezone.utc).isoformat()
    # PATCH P1 — suppression des clés de trace interne avant exposition client
    # NOTE : final_answer est intentionnellement exclu — c'est la réponse utilisateur légitime.
    # Seules les clés de débogage interne non-destinées au client sont supprimées ici.
    _INTERNAL_TRACE_KEYS: frozenset[str] = frozenset({
        "internal_trace",   # trace interne de débogage
        "system_prompt",    # prompt système (non destiné au client)
        "raw_prompt",       # prompt brut (non destiné au client)
    })
    for _sk in _INTERNAL_TRACE_KEYS:
        merged.pop(_sk, None)
    # F47.2 — sanitize user-facing text fields
    for field in ("response", "response_text"):
        if field in merged and isinstance(merged[field], str):
            merged[field] = strip_forbidden_tokens(merged[field])
    # F47.2 — sanitize controlled_response.text (nested user-echoing field)
    cr = merged.get("controlled_response")
    if isinstance(cr, dict) and isinstance(cr.get("text"), str):
        cr["text"] = sanitize_user_facing_text(cr["text"])
    return merged
