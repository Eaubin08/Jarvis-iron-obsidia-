"""
Readonly local/external model evidence -> ContextPacketV2 bridge.

A model result is evidence only:
- not a decision,
- not execution authority,
- not KX authority,
- not memory authority,
- not ACT,
- not a write.

The evidence is cryptographically bound to the input query.
KX108 remains the sole decision authority.
"""

from __future__ import annotations

import dataclasses
import hashlib
from typing import Any

from periphery.context.context_packet_builder_v2 import (
    ContextPacketV2,
)


_PFX = "MODEL_EVIDENCE_COGNITIVE_BRIDGE"

_MAX_CONTENT_CHARS = 3000

_REQUIRED_FALSE = (
    "is_execution_authority",
    "is_kx_authority",
    "is_sovereign",
    "allowed_to_decide",
    "allowed_to_act",
    "emits_act",
    "emits_verdict",
    "memory_write",
    "kernel_mutation",
    "x108_mutation",
    "real_action",
)

_FORBIDDEN_TOKENS = frozenset(
    {
        "ALLOW",
        "HOLD",
        "BLOCK",
        "ACT",
        "DECIDE",
        "VERDICT",
        "AUTHORIZE",
        "APPROVE",
        "EXECUTE",
        "DEPLOY",
    }
)


def _sha256(value: str) -> str:
    return hashlib.sha256(
        value.encode(
            "utf-8",
            errors="replace",
        )
    ).hexdigest()


def _sha16(value: str) -> str:
    return _sha256(value)[:16]


def _forbidden_in(
    text: str,
) -> list[str]:
    found: list[str] = []

    for word in text.split():
        token = word.strip(
            ".,;:!?\"'()[]{}"
        ).upper()

        if token in _FORBIDDEN_TOKENS:
            found.append(token)

    return found


def _validate(
    context: ContextPacketV2,
    evidence: dict[str, Any],
) -> None:
    if not isinstance(
        context,
        ContextPacketV2,
    ):
        raise TypeError(
            f"{_PFX}:CONTEXT_PACKET_V2_REQUIRED"
        )

    if not isinstance(
        evidence,
        dict,
    ):
        raise TypeError(
            f"{_PFX}:EVIDENCE_DICT_REQUIRED"
        )

    if evidence.get("readonly") is not True:
        raise AssertionError(
            f"{_PFX}:READONLY_REQUIRED"
        )

    if (
        evidence.get(
            "decision_authority"
        )
        != "KX108_ONLY"
    ):
        raise AssertionError(
            f"{_PFX}:DECISION_AUTHORITY_VIOLATION"
        )

    if evidence.get("result_kind") != "EVIDENCE":
        raise AssertionError(
            f"{_PFX}:RESULT_KIND_EVIDENCE_REQUIRED"
        )

    provider = str(
        evidence.get("provider")
        or ""
    ).strip()

    if not provider:
        raise ValueError(
            f"{_PFX}:PROVIDER_REQUIRED"
        )

    for key in _REQUIRED_FALSE:
        if evidence.get(key) is not False:
            raise AssertionError(
                f"{_PFX}:"
                f"{key.upper()}_MUST_BE_FALSE:"
                f"{evidence.get(key)!r}"
            )

    content = str(
        evidence.get("content")
        or ""
    ).strip()

    if not content:
        raise ValueError(
            f"{_PFX}:CONTENT_REQUIRED"
        )

    if len(content) > _MAX_CONTENT_CHARS:
        raise ValueError(
            f"{_PFX}:CONTENT_TOO_LARGE"
        )

    expected_input_hash = _sha256(
        context.query
    )

    if (
        evidence.get("input_hash")
        != expected_input_hash
    ):
        raise ValueError(
            f"{_PFX}:INPUT_HASH_MISMATCH"
        )


def enrich_context_packet_v2_with_model_evidence(
    context: ContextPacketV2,
    evidence: dict[str, Any],
) -> ContextPacketV2:
    """
    Add validated model output to ContextPacketV2.

    Additive only.
    Never overwrites existing context material or governance state.
    """

    _validate(
        context,
        evidence,
    )

    provider = str(
        evidence["provider"]
    ).strip()

    content = str(
        evidence["content"]
    ).strip()

    evidence_hash = str(
        evidence.get("evidence_hash")
        or _sha256(content)
    )

    source_ref = str(
        evidence.get("source_ref")
        or (
            "model-evidence:"
            + provider.lower()
            + ":"
            + evidence_hash[:16]
        )
    )

    model_id = str(
        evidence.get("model")
        or "UNSPECIFIED"
    )

    new_items = list(
        context.context_items
    )

    metadata = [
        (
            "MODEL_EVIDENCE_PROVIDER:"
            + provider
        ),
        (
            "MODEL_EVIDENCE_MODEL:"
            + model_id
        ),
        (
            "MODEL_EVIDENCE_HASH:"
            + evidence_hash
        ),
        (
            "MODEL_EVIDENCE:"
            + provider
            + ":"
            + content
        ),
    ]

    for item in metadata:
        if item not in new_items:
            new_items.append(item)

    new_refs = list(
        context.source_refs
    )

    new_hashes = list(
        context.source_hashes
    )

    if source_ref not in new_refs:
        new_refs.append(
            source_ref
        )

        new_hashes.append(
            _sha16(source_ref)
        )

    new_forbidden = list(
        context.forbidden_tokens_detected
    )

    for token in _forbidden_in(
        content
    ):
        if token not in new_forbidden:
            new_forbidden.append(
                token
            )

    return dataclasses.replace(
        context,
        context_items=new_items,
        source_refs=new_refs,
        source_hashes=new_hashes,
        forbidden_tokens_detected=new_forbidden,
    )


__all__ = [
    "enrich_context_packet_v2_with_model_evidence",
]
