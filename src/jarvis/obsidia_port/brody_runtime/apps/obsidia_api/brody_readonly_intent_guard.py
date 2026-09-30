"""F22B — Readonly Runtime State Intent Guard.

Detects RUNTIME_STATE_READONLY_INTENT: user messages that describe / inspect
the current runtime state (modules, memory, Graphiti, IR, dashboard…) and
must NOT trigger MEMORY_WRITE_CANON_FREEZE or action_request boundaries.

Key invariants enforced here:
  "decris"  ≠ "ecris"  — word-boundary: \\becris\\b does not match "decris"
  "actifs"  ≠ "act"    — word-boundary: \\bact\\b  does not match "actifs"
  "action"  ≠ "act"    — same reason
  "ne propose aucune action" is a negation, NOT an action_request

Boundary: KX108_ONLY, readonly, no emit, no write, no kernel/x108 mutation.
"""
from __future__ import annotations

import re
import unicodedata

BOUNDARY = {
    "readonly": True,
    "advisory_only": True,
    "context_signal_only": True,
    "allowed_to_decide": False,
    "allowed_to_act": False,
    "memory_write": False,
    "graphiti_write": False,
    "neo4j_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "emits_act": False,
    "emits_verdict": False,
    "decision_authority": "KX108_ONLY",
}


def _fold(text: str) -> str:
    text = text or ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower()


# Readonly description signals — any one is sufficient for a PASS candidate.
# Applied to the NFKD-folded, accent-stripped, lowercased text.
_READONLY_SIGNALS: list[str] = [
    r"\bdecris\b",
    r"\bdecrire\b",
    r"\bexplique\b",
    r"\bdescribe\b",
    r"\bexplain\b",
    r"etat\s+(?:systeme|runtime|actuel)",
    r"modules?\s+actifs",
    r"dashboard\s+runtime",
    r"lecture\s+seule",
    r"\breadonly\b",
    r"read[- ]only",
    r"\bdiagnostic\b",
    r"\bstatut\b",
    r"\bstatus\b",
    r"etat\s+actuel",
    r"runtime\s+state",
    r"system\s+state",
    r"etat\s+du\s+(?:systeme|runtime)",
]

# Explicit write/mutation verbs (word-boundary patterns).
# NOTE: "\becris\b" does NOT match "decris" because the "d" before "ecris"
# is a word character, so \b does not fire before the "e".
_WRITE_VERBS: list[str] = [
    r"\becris\b",
    r"\becrire\b",
    r"\bwrite\b",
    r"\bmodifie\b",
    r"\bmodifier\b",
    r"\bmodify\b",
    r"\bcanonise\b",
    r"\bcanoniser\b",
    r"\bcanonize\b",
    r"\bpromote\b",
    r"\bcommit\b",
    r"\bpush\b",
    r"\bmerge\b",
    r"\bexecute\b",
    r"\bexecuter\b",
]

# Write targets — a write verb must co-occur with one of these to be flagged.
_WRITE_TARGETS: list[str] = [
    r"\bgraphiti\b",
    r"\bmemoire\b",
    r"\bmemory\b",
    r"\bcanon\b",
    r"\bkernel\b",
    r"\bx108\b",
    r"\bfreeze\b",
    r"\bneo4j\b",
]

# Direct write phrases — short-circuit to NEGATIVE regardless of other signals.
_DIRECT_WRITE_PHRASES: list[str] = [
    r"ecris\s+(?:en\s+)?memoire",
    r"ecrire\s+(?:en\s+)?memoire",
    r"write\s+(?:to\s+)?memory",
    r"write\s+graphiti",
    r"modifie\s+graphiti",
    r"graphiti_write",
    r"memory_write",
    r"\bwrite\s+canon\b",
    r"\bcanonise\s+ce\b",
    r"\bcanoniser\s+ce\b",
    r"\bpromote\s+(?:to\s+)?canon\b",
    r"ecris\s+graphiti",
    r"write\s+kernel",
    r"ecris\s+en\s+canon",
]


def _has_explicit_write(low: str) -> bool:
    """True when the (folded) text contains an explicit write/mutation instruction."""
    if any(re.search(p, low) for p in _DIRECT_WRITE_PHRASES):
        return True
    has_verb = any(re.search(p, low) for p in _WRITE_VERBS)
    if not has_verb:
        return False
    return any(re.search(p, low) for p in _WRITE_TARGETS)


def _has_readonly_signal(low: str) -> bool:
    return any(re.search(p, low) for p in _READONLY_SIGNALS)


def detect_readonly_runtime_state_intent(user_message: str) -> dict:
    """Classify user_message as RUNTIME_STATE_READONLY_INTENT or not.

    Returns a PASS dict if the message is a readonly description/status request.
    Returns a NEGATIVE dict if explicit write/mutation is detected.
    Returns an UNKNOWN dict if neither signal is strong enough.

    This function is the single authoritative source for RUNTIME_STATE_READONLY
    classification. It is called by build_domain_raccord_snapshot() BEFORE any
    write-boundary logic, so it gates the MEMORY_WRITE_CANON_FREEZE domain.
    """
    low = _fold(user_message)

    if _has_explicit_write(low):
        return {
            "status": "NO_RUNTIME_STATE_READONLY_INTENT",
            "intent": "WRITE_OR_MUTATION_DETECTED",
        }

    if _has_readonly_signal(low):
        return {
            "status": "RUNTIME_STATE_READONLY_INTENT_PASS",
            "intent": "RUNTIME_STATE_READONLY",
            "support_intent": "runtime_state_query",
            "ir_op": "READ",
            "ir_target": "STATE(runtime_status)",
            "domains": ["ARCHITECTURE_EXPLANATION", "RUNTIME_STATE_READONLY"],
            "write_boundary_required": False,
            "risk_flags": [],
            "contradictions": [],
            "readonly": True,
            "decision_authority": "KX108_ONLY",
        }

    return {
        "status": "NO_RUNTIME_STATE_READONLY_INTENT",
        "intent": "UNKNOWN_OR_OTHER",
    }
