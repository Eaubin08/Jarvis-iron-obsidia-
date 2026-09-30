"""
Brody pre-reasoning adapter.

Composition layer only:

user message
    -> semantic query
    -> existing Reverse OS projection
    -> lexical calibration / IR signals
    -> C265 / C266 / C273 / C274

No memory retrieval.
No provider dependency.
No decision authority.
No ACT.
"""

from __future__ import annotations

from typing import Any

from apps.obsidia_api.brody_semantic_query_router import (
    build_memory_retrieval_queries,
    build_semantic_query,
)

from apps.obsidia_api.brody_existing_reverse_os_bridge import (
    build_existing_reverse_os_projection,
)

from periphery.language.pre_reasoning_calibrator import (
    calibrate_pre_reasoning,
)

from periphery.language.reasoning_directive import (
    build_reasoning_directive,
)

from periphery.language.unknown_qualifier import (
    qualify_unknowns,
)


def build_brody_pre_reasoning_snapshot(
    *,
    user_message: str,
    language: str = "unknown",
    intent: str = "pure_response",
    authority_snapshot: dict[str, Any] | None = None,
    tree_signal_packet: dict[str, Any] | None = None,
    tree_policy_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the bounded cognitive state required before Brody reasoning.

    This adapter only composes already-existing semantic / linguistic
    structures. It performs no retrieval and emits no sovereign decision.
    """

    message = str(user_message or "")
    lang = str(language or "unknown")

    authority = (
        authority_snapshot
        if isinstance(authority_snapshot, dict)
        else {}
    )

    tree_signal = (
        tree_signal_packet
        if isinstance(tree_signal_packet, dict)
        else {}
    )

    tree_policy = (
        tree_policy_snapshot
        if isinstance(tree_policy_snapshot, dict)
        else {}
    )

    # ------------------------------------------------------------
    # 1. Semantic routing
    # ------------------------------------------------------------

    semantic_query_snapshot = build_semantic_query(
        message
    )

    if not isinstance(
        semantic_query_snapshot,
        dict,
    ):
        semantic_query_snapshot = {}

    # ------------------------------------------------------------
    # 2. Existing Reverse OS projection
    # ------------------------------------------------------------

    reverse_os_projection = (
        build_existing_reverse_os_projection(
            user_message=message,
            intent=str(intent or "pure_response"),
            semantic_query_snapshot=semantic_query_snapshot,
            authority_snapshot=authority,
            tree_signal_packet=tree_signal,
            tree_policy_snapshot=tree_policy,
        )
    )

    if not isinstance(
        reverse_os_projection,
        dict,
    ):
        reverse_os_projection = {}

    ir_candidate = reverse_os_projection.get(
        "ir_candidate",
        {},
    )

    if not isinstance(
        ir_candidate,
        dict,
    ):
        ir_candidate = {}

    lexical_calibration = ir_candidate.get(
        "lexical_calibration",
        {},
    )

    if not isinstance(
        lexical_calibration,
        dict,
    ):
        lexical_calibration = {}

    # ------------------------------------------------------------
    # 3. C265 -> C266 -> C273 -> C274
    # ------------------------------------------------------------

    # ------------------------------------------------------------
    # UNKNOWN QUALIFICATION
    #
    # Preserve raw lexical / IR unknowns for auditability.
    # Only genuinely unresolved unknowns become causal inputs
    # for C265 -> C274.
    # ------------------------------------------------------------

    raw_unknowns: list[str] = []

    for source_unknowns in (
        lexical_calibration.get(
            "unknowns",
            [],
        ),
        ir_candidate.get(
            "unknowns",
            [],
        ),
    ):
        if not isinstance(
            source_unknowns,
            list,
        ):
            continue

        for value in source_unknowns:
            token = str(value or "").strip()

            if (
                token
                and token not in raw_unknowns
            ):
                raw_unknowns.append(token)

    known_concept_ids = list(
        lexical_calibration.get(
            "known_concept_ids",
            [],
        )
        if isinstance(
            lexical_calibration.get(
                "known_concept_ids",
                [],
            ),
            list,
        )
        else []
    )

    entities = list(
        ir_candidate.get(
            "entities",
            [],
        )
        if isinstance(
            ir_candidate.get(
                "entities",
                [],
            ),
            list,
        )
        else []
    )

    retrieval_targets: list[str] = []

    if (
        semantic_query_snapshot.get("route")
        == "TOPIC_MATCHED"
        and semantic_query_snapshot.get(
            "is_canonical"
        )
        is True
        and semantic_query_snapshot.get(
            "topic"
        )
        == "MEMORY_QUERY"
    ):
        retrieval_targets = (
            build_memory_retrieval_queries(
                message
            )
        )

    unknown_qualification = qualify_unknowns(
        user_message=message,
        language=lang,
        lexical_unknowns=raw_unknowns,
        semantic_query_snapshot=(
            semantic_query_snapshot
        ),
        known_concept_ids=known_concept_ids,
        entities=entities,
        retrieval_targets=retrieval_targets,
    )

    unresolved_unknowns = list(
        unknown_qualification.get(
            "unresolved_unknowns",
            [],
        )
    )

    # Qualified copies only.
    # The raw objects returned in the snapshot stay untouched.
    qualified_lexical_calibration = dict(
        lexical_calibration
    )

    qualified_lexical_calibration[
        "unknowns"
    ] = unresolved_unknowns

    qualified_ir_candidate = dict(
        ir_candidate
    )

    qualified_ir_candidate[
        "unknowns"
    ] = unresolved_unknowns

    pre_reasoning_calibration = (
        calibrate_pre_reasoning(
            user_message=message,
            language=lang,
            lexical_calibration=(
                qualified_lexical_calibration
            ),
            ir_candidate=(
                qualified_ir_candidate
            ),
        )
    )

    reasoning_directive = (
        build_reasoning_directive(
            pre_reasoning_calibration
        )
    )

    return {
        "status": "BRODY_PRE_REASONING_PASS",
        "schema": "BRODY_PRE_REASONING_SNAPSHOT_V1",

        "user_message": message,
        "language": lang,
        "intent": str(intent or "pure_response"),

        "semantic_query_snapshot": (
            semantic_query_snapshot
        ),

        "reverse_os_projection": (
            reverse_os_projection
        ),

        "ir_candidate": ir_candidate,

        "unknown_qualification": (
            unknown_qualification
        ),

        "pre_reasoning_calibration": (
            pre_reasoning_calibration
        ),

        "reasoning_directive": (
            reasoning_directive
        ),

        "unknowns": list(
            pre_reasoning_calibration.get(
                "unknowns",
                [],
            )
        ),

        "reasoning_readiness": (
            pre_reasoning_calibration.get(
                "reasoning_readiness",
                "CALIBRATED_WITH_UNCERTAINTY",
            )
        ),

        # Hard boundary.
        "readonly": True,
        "advisory_only": True,
        "context_signal_only": True,

        "decision_authority": "KX108_ONLY",

        "allowed_to_decide": False,
        "allowed_to_act": False,

        "emits_act": False,
        "emits_verdict": False,

        "memory_write": False,
        "canonical_write": False,

        "kernel_mutation": False,
        "x108_mutation": False,
    }


__all__ = [
    "build_brody_pre_reasoning_snapshot",
]
