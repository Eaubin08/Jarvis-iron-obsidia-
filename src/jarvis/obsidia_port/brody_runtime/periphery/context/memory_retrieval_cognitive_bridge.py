"""
C2B-M4B1B — provider-neutral readonly memory retrieval bridge.

A precomputed readonly memory retrieval/result snapshot enriches an existing
ContextPacketV2.

This bridge:
- does not execute retrieval,
- does not create/promote MemoryCandidate,
- does not write memory,
- does not decide,
- does not ACT,
- does not mutate Kernel/X108,
- does not know the identity of an external storage/retrieval provider.

KX108 remains the sole decision authority.
"""

from __future__ import annotations

import dataclasses
import hashlib
from typing import Any

from periphery.context.context_packet_builder_v2 import ContextPacketV2


_PFX = "MEMORY_RETRIEVAL_COGNITIVE_BRIDGE"

_REQUIRED_FALSE = (
    "memory_write",
    "emits_act",
    "emits_verdict",
    "kernel_mutation",
)

_OPTIONAL_FALSE = (
    "canonical_write",
    "allowed_to_decide",
    "allowed_to_act",
    "x108_mutation",
    "memory_authority",
    "memory_decision",
    "auto_promotion",
    "real_action",
)

_FORBIDDEN_TOKENS = frozenset({
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
})

_NATIVE_SOURCE_MODES = frozenset({
    "OBSIDIA_NATIVE_MEMORY",
    "OBSIDIA_NATIVE_MEMORY_V1",
})

_FAIL_CLOSED_RETRIEVAL_STATUSES = frozenset({
    "MEMORY_REQUIRED_NO_NATIVE_SOURCE",
    "MEMORY_REQUIRED_INVALID_NATIVE_SOURCE",
    "MEMORY_REQUIRED_EMPTY_QUERY",
    "MEMORY_REQUIRED_EMPTY",
})

_LEGACY_GENERIC_FAILURE_STATUSES = frozenset({
    "ERROR",
    "NO_MEMORY_RESULTS",
    "CHAIN_ERROR",
})


def _sha16(ref: str) -> str:
    return hashlib.sha256(
        ref.encode()
    ).hexdigest()[:16]


def _forbidden_in(text: str) -> list[str]:
    out: list[str] = []

    for word in text.split():
        token = word.strip(
            ".,;:!?\"'()[]{}"
        ).upper()

        if token in _FORBIDDEN_TOKENS:
            out.append(token)

    return out


def _assert_non_sovereign_flags(
    obj: dict[str, Any],
    *,
    scope: str,
) -> None:
    """
    Provider-neutral governance validation.

    Required canonical controls are checked explicitly.
    Any additional boolean write/mutation/authority field is rejected
    generically when True, regardless of its storage/provider name.
    """

    for key in _REQUIRED_FALSE:
        if obj.get(key) is not False:
            raise AssertionError(
                f"{_PFX}:{scope}:"
                f"{key.upper()}_MUST_BE_FALSE:"
                f"{obj.get(key)!r}"
            )

    for key in _OPTIONAL_FALSE:
        if (
            key in obj
            and obj.get(key) is not False
        ):
            raise AssertionError(
                f"{_PFX}:{scope}:"
                f"{key.upper()}_MUST_BE_FALSE:"
                f"{obj.get(key)!r}"
            )

    for raw_key, value in obj.items():
        if value is not True:
            continue

        key = str(raw_key).lower()

        forbidden_true = (
            key.endswith("_write")
            or key.endswith("_mutation")
            or key.startswith("emits_")
            or key.startswith("allowed_to_")
            or key
            in {
                "memory_authority",
                "memory_decision",
                "auto_promotion",
                "real_action",
            }
        )

        if forbidden_true:
            raise AssertionError(
                f"{_PFX}:{scope}:"
                f"NON_SOVEREIGN_FLAG_TRUE:{raw_key}"
            )


def _validate(
    snapshot: dict[str, Any],
) -> None:
    if not isinstance(snapshot, dict):
        raise TypeError(
            f"{_PFX}:DICT_REQUIRED:"
            f"{type(snapshot).__name__}"
        )

    if snapshot.get("readonly") is not True:
        raise AssertionError(
            f"{_PFX}:READONLY_REQUIRED"
        )

    if (
        snapshot.get("decision_authority")
        != "KX108_ONLY"
    ):
        raise AssertionError(
            f"{_PFX}:DECISION_AUTHORITY_VIOLATION"
        )

    _assert_non_sovereign_flags(
        snapshot,
        scope="SNAPSHOT",
    )

    items = snapshot.get(
        "selected_items",
        [],
    )

    if not isinstance(items, list):
        raise TypeError(
            f"{_PFX}:SELECTED_ITEMS_LIST_REQUIRED"
        )

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue

        if (
            "readonly" in item
            and item.get("readonly") is not True
        ):
            raise AssertionError(
                f"{_PFX}:ITEM_{index}:"
                "READONLY_REQUIRED"
            )

        if (
            "decision_authority" in item
            and item.get("decision_authority")
            != "KX108_ONLY"
        ):
            raise AssertionError(
                f"{_PFX}:ITEM_{index}:"
                "DECISION_AUTHORITY_VIOLATION"
            )

        # Item boundary fields are optional for historical normalized
        # response-engine items, but any explicit sovereign flag fails closed.
        for raw_key, value in item.items():
            if value is not True:
                continue

            key = str(raw_key).lower()

            forbidden_true = (
                key.endswith("_write")
                or key.endswith("_mutation")
                or key.startswith("emits_")
                or key.startswith("allowed_to_")
                or key
                in {
                    "memory_authority",
                    "memory_decision",
                    "auto_promotion",
                    "real_action",
                }
            )

            if forbidden_true:
                raise AssertionError(
                    f"{_PFX}:ITEM_{index}:"
                    f"NON_SOVEREIGN_FLAG_TRUE:{raw_key}"
                )


def _normalized_source_mode(
    snapshot: dict[str, Any],
) -> str:
    raw = str(
        snapshot.get("source_mode")
        or snapshot.get("source_type")
        or ""
    )

    if raw in _NATIVE_SOURCE_MODES:
        return raw

    # Historical or unknown source identities are deliberately collapsed.
    return "READONLY_MEMORY_RETRIEVAL"


def enrich_context_packet_v2_with_memory_retrieval(
    context: ContextPacketV2,
    snapshot: dict[str, Any],
) -> ContextPacketV2:
    """
    Add readonly retrieval evidence to ContextPacketV2.

    Retrieval result != MemoryCandidate.
    Retrieval result != decision.
    """

    if not isinstance(
        context,
        ContextPacketV2,
    ):
        raise TypeError(
            f"{_PFX}:CONTEXT_PACKET_V2_REQUIRED"
        )

    _validate(snapshot)

    status = str(
        snapshot.get("status")
        or "UNKNOWN"
    )

    retrieval_status = str(
        snapshot.get("retrieval_status")
        or status
    )

    source_mode = _normalized_source_mode(
        snapshot
    )

    material_quality = str(
        snapshot.get("material_quality")
        or ""
    )

    effective_query = str(
        snapshot.get("effective_query")
        or snapshot.get("query_normalized")
        or snapshot.get("semantic_query")
        or snapshot.get("query")
        or ""
    )

    new_items = list(
        context.context_items
    )

    metadata_items = [
        f"MEMORY_RETRIEVAL_STATUS:{status}",
        f"MEMORY_RETRIEVAL_RESULT:{retrieval_status}",
        f"MEMORY_RETRIEVAL_SOURCE_MODE:{source_mode}",
    ]

    if material_quality:
        metadata_items.append(
            "MEMORY_RETRIEVAL_MATERIAL_QUALITY:"
            f"{material_quality}"
        )

    if effective_query:
        metadata_items.append(
            f"MEMORY_RETRIEVAL_QUERY:{effective_query}"
        )

    for item in metadata_items:
        if item not in new_items:
            new_items.append(item)

    new_refs = list(
        context.source_refs
    )

    new_hashes = list(
        context.source_hashes
    )

    new_forbidden = list(
        context.forbidden_tokens_detected
    )

    selected = snapshot.get(
        "selected_items",
        [],
    )

    for item in selected:
        if not isinstance(item, dict):
            continue

        source_ref = str(
            item.get("source_ref")
            or item.get("id")
            or ""
        ).strip()

        material = str(
            item.get("material")
            or item.get("excerpt")
            or ""
        ).strip()

        # Reference-only retrieval hits remain valid provenance.
        if (
            source_ref
            and source_ref not in new_refs
        ):
            new_refs.append(source_ref)
            new_hashes.append(
                _sha16(source_ref)
            )

        # Only material-bearing hits enter context material.
        if material:
            material_item = (
                "MEMORY_RETRIEVAL:"
                f"{source_ref or 'UNRESOLVED'}:"
                f"{material}"
            )

            if material_item not in new_items:
                new_items.append(
                    material_item
                )

            for token in _forbidden_in(
                material
            ):
                if token not in new_forbidden:
                    new_forbidden.append(
                        token
                    )

    new_unknowns = list(
        context.unknowns
    )

    fail_closed = (
        retrieval_status
        in _FAIL_CLOSED_RETRIEVAL_STATUSES
        or status
        in _LEGACY_GENERIC_FAILURE_STATUSES
    )

    if fail_closed:
        marker = (
            "MEMORY_RETRIEVAL:"
            f"{retrieval_status}"
        )

        if marker not in new_unknowns:
            new_unknowns.append(marker)

    return dataclasses.replace(
        context,
        context_items=new_items,
        source_refs=new_refs,
        source_hashes=new_hashes,
        retrieval_status=retrieval_status,
        unknowns=new_unknowns,
        forbidden_tokens_detected=new_forbidden,
    )


__all__ = [
    "enrich_context_packet_v2_with_memory_retrieval",
]
