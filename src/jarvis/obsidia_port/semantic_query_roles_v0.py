from __future__ import annotations

import re
import unicodedata
from typing import Any


_GOVERNANCE = {
    "readonly": True,
    "advisory_only": True,
    "emits_act": False,
    "memory_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "decision_authority": "KX108_ONLY",
}


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", str(text or ""))
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return " ".join(folded.casefold().split())


def build_semantic_query_roles(
    *,
    user_message: str,
    semantic_snapshot: Any = None,
    ir_snapshot: Any = None,
) -> dict[str, Any]:
    """Describe relative semantic roles without routing or authorizing anything.

    V0 is deliberately narrow. It preserves the distinction exposed by live
    testing: a concept can be the requested object (focus) rather than merely
    a retrieval mechanism. Unknown roles remain explicit instead of guessed.
    """
    text = _normalize(user_message)
    semantic = semantic_snapshot if isinstance(semantic_snapshot, dict) else {}
    ir = ir_snapshot if isinstance(ir_snapshot, dict) else {}

    memory_mentioned = bool(re.search(r"\b(memoire|memory)\b", text))
    obsidia_mentioned = bool(re.search(r"\b(obsidia|obsidian|obsidio)\b", text))
    explain_requested = bool(
        re.search(r"\b(explique|expliquer|expliquez|detaille|detailler|developpe|developper)\b", text)
    )
    detail_requested = bool(
        re.search(r"\b(detaille|detailler|detail|details|developpe|developper)\b", text)
    )
    knowledge_requested = bool(
        re.search(r"\b(sais|savoir|connai[st]|connais|contient|contenu|retrouve|rappelle)\b", text)
    )

    focus = "UNKNOWN"
    scope: list[str] = []
    operations: list[str] = []
    qualifiers: list[str] = []
    confidence = "INSUFFICIENT"

    # Confirmed live pattern: "ce que tu sais en mémoire sur Obsidia".
    # MEMORY is the object being interrogated; OBSIDIA is its scope.
    if memory_mentioned and (knowledge_requested or explain_requested):
        focus = "MEMORY"
        confidence = "HIGH"
        if obsidia_mentioned:
            scope.append("OBSIDIA")
        if knowledge_requested:
            operations.append("RETRIEVE_KNOWLEDGE")
        if explain_requested:
            operations.append("EXPLAIN")
        if detail_requested:
            qualifiers.append("DETAILED")
    elif memory_mentioned:
        focus = "MEMORY"
        confidence = "MEDIUM"
        if obsidia_mentioned:
            scope.append("OBSIDIA")
    elif obsidia_mentioned:
        focus = "OBSIDIA"
        confidence = "MEDIUM"

    return {
        "status": "SEMANTIC_QUERY_ROLES_READY",
        "version": "V0",
        "focus": focus,
        "scope": scope,
        "operations": operations,
        "qualifiers": qualifiers,
        "confidence": confidence,
        "semantic_topic": str(semantic.get("topic") or ""),
        "ir_intent_type": str(ir.get("intent_type") or ""),
        "ir_target_layer": str(ir.get("target_layer") or ""),
        "contract": {
            "presence_not_role": True,
            "understanding_not_capability": True,
            "capability_not_authorization": True,
        },
        "governance": dict(_GOVERNANCE),
    }


__all__ = ["build_semantic_query_roles"]
