"""
Context Packet Builder V2 — full sovereignty field set per Phase 7 spec.
Fields: packet_id, query, language, context_items, source_refs, source_hashes,
dominant_trees, memory_status, retrieval_status, risk_flags, unknowns,
contradictions, forbidden_tokens_detected, readonly, context_signal_only,
decision_authority, allowed_to_decide, allowed_to_act, kernel_mutation, memory_write.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

_FORBIDDEN_TOKENS = {"ALLOW", "HOLD", "BLOCK", "ACT", "DECIDE", "VERDICT",
                     "AUTHORIZE", "APPROVE", "EXECUTE", "DEPLOY"}


@dataclass
class ContextPacketV2:
    packet_id: str
    query: str
    language: str
    context_items: list[str]
    source_refs: list[str] = field(default_factory=list)
    source_hashes: list[str] = field(default_factory=list)
    dominant_trees: list[int] = field(default_factory=list)
    memory_status: str = "CANDIDATE_ONLY"
    retrieval_status: str = "READ_ONLY"
    risk_flags: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    forbidden_tokens_detected: list[str] = field(default_factory=list)
    readonly: bool = True
    context_signal_only: bool = True
    decision_authority: str = "KX108_ONLY"
    allowed_to_decide: bool = False
    allowed_to_act: bool = False
    kernel_mutation: bool = False
    memory_write: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "query": self.query,
            "language": self.language,
            "context_items": self.context_items,
            "source_refs": self.source_refs,
            "source_hashes": self.source_hashes,
            "dominant_trees": self.dominant_trees,
            "memory_status": self.memory_status,
            "retrieval_status": self.retrieval_status,
            "risk_flags": self.risk_flags,
            "unknowns": self.unknowns,
            "contradictions": self.contradictions,
            "forbidden_tokens_detected": self.forbidden_tokens_detected,
            "readonly": self.readonly,
            "context_signal_only": self.context_signal_only,
            "decision_authority": self.decision_authority,
            "allowed_to_decide": self.allowed_to_decide,
            "allowed_to_act": self.allowed_to_act,
            "kernel_mutation": self.kernel_mutation,
            "memory_write": self.memory_write,
        }


def build_context_packet_v2(
    query: str,
    language: str = "en",
    context_items: list[str] | None = None,
    source_refs: list[str] | None = None,
    packet_id: str | None = None,
    dominant_trees: list[int] | None = None,
    memory_status: str | None = None,
    risk_flags: list[str] | None = None,
    unknowns: list[str] | None = None,
    contradictions: list[str] | None = None,
) -> ContextPacketV2:
    items = context_items or []
    forbidden: list[str] = []
    for item in items:
        for word in item.split():
            if word.strip(".,;:!?\"'").upper() in _FORBIDDEN_TOKENS:
                forbidden.append(word.strip(".,;:!?\"'").upper())
    hashes = []
    for ref in (source_refs or []):
        hashes.append(hashlib.sha256(ref.encode()).hexdigest()[:16])
    return ContextPacketV2(
        packet_id=packet_id or uuid.uuid4().hex,
        query=query,
        language=language,
        context_items=items,
        source_refs=source_refs or [],
        source_hashes=hashes,
        dominant_trees=dominant_trees or [],
        memory_status=memory_status or "CANDIDATE_ONLY",
        risk_flags=risk_flags or [],
        unknowns=unknowns or [],
        contradictions=contradictions or [],
        forbidden_tokens_detected=list(set(forbidden)),
        readonly=True,
        context_signal_only=True,
        decision_authority="KX108_ONLY",
        allowed_to_decide=False,
        allowed_to_act=False,
        kernel_mutation=False,
        memory_write=False,
    )
