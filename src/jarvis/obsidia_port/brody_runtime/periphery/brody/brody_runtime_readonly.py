"""
Brody Runtime (Read-Only) — processes queries and returns contextual responses.
Brody responds, never decides. No memory write, no ACT emission.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .brody_response_contract import BRODY_CONTRACT, BrodyResponseContract


@dataclass
class BrodyResponse:
    response_id: str
    query: str
    language: str
    response_text: str
    confidence: float
    context_refs: list[str]
    contract: dict
    timestamp: str
    readonly: bool = True
    emits_act: bool = False
    memory_write: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id": self.response_id,
            "query": self.query,
            "language": self.language,
            "response_text": self.response_text,
            "confidence": self.confidence,
            "context_refs": self.context_refs,
            "contract": self.contract,
            "timestamp": self.timestamp,
            "readonly": self.readonly,
            "emits_act": self.emits_act,
            "memory_write": self.memory_write,
        }


def brody_respond(
    query: str,
    language: str = "en",
    context_refs: list[str] | None = None,
    confidence: float = 0.7,
) -> BrodyResponse:
    BRODY_CONTRACT.validate()
    return BrodyResponse(
        response_id=uuid.uuid4().hex,
        query=query[:500],
        language=language,
        response_text=f"[BRODY_READONLY_RESPONSE] Context acknowledged: {query[:100]}",
        confidence=max(0.0, min(1.0, confidence)),
        context_refs=context_refs or [],
        contract=BRODY_CONTRACT.to_dict(),
        timestamp=datetime.now(timezone.utc).isoformat(),
        readonly=True,
        emits_act=False,
        memory_write=False,
    )
