"""
brody_secret_scrubber — shared secret detection + scrubbing utility.
No IO. No network. No ACT. No write. DECISION_AUTHORITY=KX108_ONLY.
Used by Block 3 pipeline AND route layer to scrub sensitive data.
Block 3F repair V0: G1 (response echo), G2 (flag propagation), G3 (private key preflight).
Block 3F G1b/G4 surface repair: space-separated patterns + scrub_secret_like_deep.
"""
from __future__ import annotations

import re
from typing import Any

# ── Detection patterns (no negative lookahead — for detect_secret_like only) ─
_DETECT_PATTERNS: list[re.Pattern] = [
    # = / : / space form
    re.compile(r"API_KEY\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"GOOGLE_API_KEY\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"SECRET\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"PASSWORD\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]{6,}=*", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", re.IGNORECASE),
    re.compile(r"access_token\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\btoken\s*:\s*[A-Za-z0-9\-._~+/]{8,}", re.IGNORECASE),
    re.compile(r"\bprivate_key\s*[:=]\s*\S+", re.IGNORECASE),
    # G1b — space-separated form (LLM reformulation without = or :)
    re.compile(r"\bAPI_KEY\s+(?!\[REDACTED)(?!=)\S{4,}", re.IGNORECASE),
    re.compile(r"\bGOOGLE_API_KEY\s+(?!\[REDACTED)(?!=)\S{4,}", re.IGNORECASE),
    re.compile(r"\bPASSWORD\s+(?!\[REDACTED)(?!=)\S{4,}", re.IGNORECASE),
    re.compile(r"\bSECRET\s+(?!\[REDACTED)(?!=)\S{4,}", re.IGNORECASE),
    re.compile(r"\baccess_token\s+(?!\[REDACTED)(?!=)\S{6,}", re.IGNORECASE),
    re.compile(r"\bprivate_key\s+(?!\[REDACTED)(?!=)\S{3,}", re.IGNORECASE),
    re.compile(r"\btoken\s+(?!\[REDACTED)(?!:)[A-Za-z0-9\-._~+/]{8,}", re.IGNORECASE),
]

# ── Scrub pairs: (detect pattern, replacement string) ─────────────────────────
# Negative lookahead on [REDACTED to avoid double-redaction of already-scrubbed values.
# = / : forms first — then space forms (G1b). Order matters: = form matched before space form.
_SCRUB_PAIRS: list[tuple[re.Pattern, str]] = [
    # ── existing patterns (= / : form) ────────────────────────────────────────
    (re.compile(r"API_KEY\s*=\s*(?!\[REDACTED)\S+", re.IGNORECASE),
     "API_KEY=[REDACTED_SECRET]"),
    (re.compile(r"GOOGLE_API_KEY\s*=\s*(?!\[REDACTED)\S+", re.IGNORECASE),
     "GOOGLE_API_KEY=[REDACTED_SECRET]"),
    (re.compile(r"SECRET\s*=\s*(?!\[REDACTED)\S+", re.IGNORECASE),
     "SECRET=[REDACTED_SECRET]"),
    (re.compile(r"PASSWORD\s*=\s*(?!\[REDACTED)\S+", re.IGNORECASE),
     "PASSWORD=[REDACTED_SECRET]"),
    (re.compile(r"Bearer\s+(?!\[REDACTED)[A-Za-z0-9\-._~+/]{6,}=*", re.IGNORECASE),
     "Bearer [REDACTED_SECRET]"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"),
     "sk-[REDACTED_SECRET]"),
    (re.compile(r"ghp_[A-Za-z0-9]{36}"),
     "ghp_[REDACTED_SECRET]"),
    (re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", re.IGNORECASE),
     "-----BEGIN PRIVATE KEY [REDACTED_SECRET]"),
    (re.compile(r"access_token\s*[:=]\s*(?!\[REDACTED)\S+", re.IGNORECASE),
     "access_token=[REDACTED_SECRET]"),
    (re.compile(r"\btoken\s*:\s*(?!\[REDACTED)[A-Za-z0-9\-._~+/]{8,}", re.IGNORECASE),
     "token: [REDACTED_SECRET]"),
    (re.compile(r"\bprivate_key\s*[:=]\s*(?!\[REDACTED)\S+", re.IGNORECASE),
     "private_key=[REDACTED_SECRET]"),
    # ── G1b — space-separated form (LLM reformulation, no = or :) ─────────────
    (re.compile(r"\bAPI_KEY\s+(?!\[REDACTED)(?!=)\S{4,}", re.IGNORECASE),
     "API_KEY [REDACTED_SECRET]"),
    (re.compile(r"\bGOOGLE_API_KEY\s+(?!\[REDACTED)(?!=)\S{4,}", re.IGNORECASE),
     "GOOGLE_API_KEY [REDACTED_SECRET]"),
    (re.compile(r"\bPASSWORD\s+(?!\[REDACTED)(?!=)\S{4,}", re.IGNORECASE),
     "PASSWORD [REDACTED_SECRET]"),
    (re.compile(r"\bSECRET\s+(?!\[REDACTED)(?!=)\S{4,}", re.IGNORECASE),
     "SECRET [REDACTED_SECRET]"),
    (re.compile(r"\baccess_token\s+(?!\[REDACTED)(?!=)\S{6,}", re.IGNORECASE),
     "access_token [REDACTED_SECRET]"),
    (re.compile(r"\bprivate_key\s+(?!\[REDACTED)(?!=)\S{3,}", re.IGNORECASE),
     "private_key [REDACTED_SECRET]"),
    (re.compile(r"\btoken\s+(?!\[REDACTED)(?!:)[A-Za-z0-9\-._~+/]{8,}", re.IGNORECASE),
     "token [REDACTED_SECRET]"),
]

# ── Named flag keys (parallel to _SCRUB_PAIRS) ────────────────────────────────
_FLAG_NAMES = [
    # = / : form
    "api_key", "google_api_key", "secret_eq", "password",
    "bearer", "sk_key", "ghp_token", "private_key_header",
    "access_token", "token_colon", "private_key_field",
    # G1b space form
    "api_key_space", "google_api_key_space", "password_space", "secret_space",
    "access_token_space", "private_key_space", "token_space",
]

# ── Private key detector ───────────────────────────────────────────────────────
_PRIVATE_KEY_RE = re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", re.IGNORECASE)

# ── Max recursion depth for scrub_secret_like_deep ────────────────────────────
_MAX_DEPTH = 25

# ── G5: sensitive key tokens for context-aware sequence scrubbing ─────────────
# Exact match, case-insensitive. "tokenisation" != "TOKEN". "project" != any.
_SENSITIVE_KEY_TOKENS: frozenset[str] = frozenset({
    "API_KEY", "GOOGLE_API_KEY", "PASSWORD", "SECRET",
    "TOKEN", "ACCESS_TOKEN", "PRIVATE_KEY", "BEARER",
})


def scrub_secret_token_sequence(seq: list) -> list:
    """
    G5 context-aware scrub: in a list, replace any element immediately following
    a recognized sensitive key token with [REDACTED_SECRET].

    Handles two structures:
      - Flat strings:      ["API_KEY", "abc123SECRET"] → ["API_KEY", "[REDACTED_SECRET]"]
      - Dict query ladder: [{"query": "TOKEN"}, {"query": "abc.def.ghi"}]
                           → [{"query": "TOKEN"}, {"query": "[REDACTED_SECRET]"}]

    Matching is case-insensitive and exact — "tokenisation" != "TOKEN".
    Idempotent: already-redacted values are preserved.
    No IO. No network. No ACT. DECISION_AUTHORITY=KX108_ONLY.
    Never raises.
    """
    if not seq:
        return seq
    try:
        result = list(seq)
        for i, item in enumerate(result):
            # Case 1: flat string token list
            if (
                isinstance(item, str)
                and item.strip().upper() in _SENSITIVE_KEY_TOKENS
                and i + 1 < len(result)
                and isinstance(result[i + 1], str)
                and result[i + 1] != "[REDACTED_SECRET]"
            ):
                result[i + 1] = "[REDACTED_SECRET]"
            # Case 2: dict query ladder [{"query": "KEY_TOKEN"}, {"query": "value"}]
            elif (
                isinstance(item, dict)
                and isinstance(item.get("query"), str)
                and item["query"].strip().upper() in _SENSITIVE_KEY_TOKENS
                and i + 1 < len(result)
                and isinstance(result[i + 1], dict)
                and isinstance(result[i + 1].get("query"), str)
                and result[i + 1]["query"] != "[REDACTED_SECRET]"
            ):
                new_dict = dict(result[i + 1])
                new_dict["query"] = "[REDACTED_SECRET]"
                result[i + 1] = new_dict
        return result
    except Exception:
        return list(seq)


def detect_secret_like(text: str) -> bool:
    """Return True if text contains any secret-like pattern (raw or scrubbed check)."""
    if not text:
        return False
    for pat in _DETECT_PATTERNS:
        if pat.search(text):
            return True
    return False


def scrub_secret_like(text: str) -> str:
    """
    Replace secret values with [REDACTED_SECRET]. Preserves surrounding context.
    Idempotent: already-redacted values are not double-redacted.
    Handles = / : forms AND space-separated (G1b) forms.
    Never raises.
    """
    if not text:
        return text
    try:
        result = text
        for pat, replacement in _SCRUB_PAIRS:
            result = pat.sub(replacement, result)
        return result
    except Exception:
        return text


def scrub_secret_like_deep(obj: Any, _depth: int = 0) -> Any:
    """
    Recursively scrub secret-like patterns in dicts, lists, and strings.
    Returns a scrubbed copy — does not modify the input in place.
    Preserves booleans, ints, floats, None, and non-sensitive values.
    Max recursion depth = _MAX_DEPTH to prevent stack overflow.
    Scope: HTTP surface scrubbing only. No write, no ACT, DECISION_AUTHORITY=KX108_ONLY.
    Never raises.
    """
    if _depth > _MAX_DEPTH:
        return obj
    try:
        if isinstance(obj, bool):
            return obj
        if isinstance(obj, str):
            return scrub_secret_like(obj)
        if isinstance(obj, dict):
            return {k: scrub_secret_like_deep(v, _depth + 1) for k, v in obj.items()}
        if isinstance(obj, list):
            # G5: context-aware sequence scrub before per-element recursion
            seq = scrub_secret_token_sequence(obj)
            return [scrub_secret_like_deep(item, _depth + 1) for item in seq]
        # int, float, None, and other non-string scalars — preserve as-is
        return obj
    except Exception:
        return obj


def secret_flags(text: str) -> dict:
    """Return per-pattern detection flags as a dict."""
    if not text:
        return {name: False for name in _FLAG_NAMES}
    flags: dict[str, bool] = {}
    for name, (pat, _) in zip(_FLAG_NAMES, _SCRUB_PAIRS):
        flags[name] = bool(pat.search(text))
    return flags


def is_private_key_message(text: str) -> bool:
    """Return True if message contains -----BEGIN [RSA] PRIVATE KEY----- marker."""
    return bool(_PRIVATE_KEY_RE.search(text or ""))
