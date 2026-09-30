"""
Brody native memory response adapter.

Pipeline:
    native readonly retrieval
        -> local readonly response engine
        -> provider-neutral response snapshot

This module does not decide whether memory is needed.
`memory_required` is supplied by MEMZUM upstream.

No network.
No external memory service.
No memory write.
No canonical write.
No kernel/X108 mutation.
No ACT/verdict emission.
KX108 remains the sole decision authority.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apps.obsidia_api.brody_obsidia_native_memory import (
    build_native_memory_retrieval_snapshot,
)


_REPO_ROOT = Path(__file__).resolve().parents[2]

_LOCAL_ENGINE_PATH = (
    _REPO_ROOT
    / "periphery"
    / "brody_memory_readonly"
    / "local_response_engine_readonly"
    / "brody_local_response_engine_readonly_v1.py"
)


NATIVE_MEMORY_RESPONSE_BOUNDARY: dict[str, Any] = {
    "readonly": True,
    "response_only": True,
    "memory_authority": False,
    "memory_decision": False,
    "memory_write": False,
    "canonical_write": False,
    "auto_promotion": False,
    "allowed_to_decide": False,
    "allowed_to_act": False,
    "emits_act": False,
    "emits_verdict": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "decision_authority": "KX108_ONLY",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_local_response_engine() -> Any | None:
    """
    Load the existing readonly local response engine only.

    The engine is a formatter/consumer of already-selected material.
    It does not perform retrieval.
    """

    if not _LOCAL_ENGINE_PATH.exists():
        return None

    try:
        spec = importlib.util.spec_from_file_location(
            "obsidia_native_local_response_engine",
            str(_LOCAL_ENGINE_PATH),
        )

        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, "build_response"):
            return None

        return module

    except Exception:
        return None


def _base_snapshot(
    *,
    user_message: str,
    semantic_query: str,
    memory_required: bool,
) -> dict[str, Any]:
    return {
        "schema_version": "BRODY_NATIVE_MEMORY_RESPONSE_V1",
        "source_mode": "OBSIDIA_NATIVE_MEMORY",
        "chain_source": "obsidia_native_memory->local_response_engine",
        "user_message": str(user_message or ""),
        "semantic_query": str(semantic_query or ""),
        "primary_query": str(semantic_query or ""),
        "effective_query": None,
        "memory_required": bool(memory_required),
        "retrieval_status": "NOT_EVALUATED",
        "attempted_queries": [],
        "query_results_count": 0,
        "native_index_records_total": 0,
        "hydration_module_used": False,
        "hydrated_excerpt_count": 0,
        "local_response_engine_used": False,
        "material_quality": "NO_MATERIAL",
        "response_md": "",
        "response_md_length": 0,
        "selected_items_count": 0,
        "selected_items": [],
        "tag_counts": {},
        "final_answer_uses_response_md": False,
        "created_at": _now(),
        **NATIVE_MEMORY_RESPONSE_BOUNDARY,
    }



def _apply_item_boundary(
    raw_items: Any,
    *,
    max_items: int,
) -> list[dict[str, Any]]:
    """
    Re-attach the native readonly/non-sovereign boundary after the
    historical local response engine has transformed retrieval items.

    Content/provenance fields are preserved exactly as produced:
    material, excerpt, source_ref, path, id, score, tags, etc.
    Only governance metadata is enforced here.
    """

    if not isinstance(raw_items, list):
        return []

    bounded: list[dict[str, Any]] = []

    for item in raw_items[:max_items]:
        if not isinstance(item, dict):
            continue

        normalized = dict(item)

        normalized.update({
            "readonly": True,
            "memory_authority": False,
            "memory_decision": False,
            "memory_write": False,
            "canonical_write": False,
            "auto_promotion": False,
            "allowed_to_decide": False,
            "allowed_to_act": False,
            "emits_act": False,
            "emits_verdict": False,
            "kernel_mutation": False,
            "x108_mutation": False,
            "decision_authority": "KX108_ONLY",
        })

        bounded.append(normalized)

    return bounded

def build_native_memory_response(
    *,
    user_message: str,
    semantic_query: str = "",
    memory_required: bool,
    language: str = "fr",
    limit: int = 8,
    max_items: int = 6,
    index_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Execute native readonly retrieval then the existing local response engine.

    The adapter never derives `memory_required`.
    It obeys the upstream MEMZUM activation signal exactly.
    """

    query = str(
        semantic_query
        or user_message
        or ""
    ).strip()

    base = _base_snapshot(
        user_message=user_message,
        semantic_query=query,
        memory_required=memory_required,
    )

    retrieval = build_native_memory_retrieval_snapshot(
        query,
        memory_required=bool(memory_required),
        limit=limit,
        index_path=index_path,
    )

    retrieval_status = str(
        retrieval.get("status")
        or "MEMORY_REQUIRED_INVALID_NATIVE_SOURCE"
    )

    items = list(
        retrieval.get("selected_items")
        or []
    )

    index_count = int(
        retrieval.get("index_record_count")
        or 0
    )

    attempted = []

    if memory_required and query:
        attempted.append({
            "query": query,
            "results_count": len(items),
        })

    common = {
        **base,
        "effective_query": (
            str(
                retrieval.get("query_normalized")
                or query
            )
            if query
            else None
        ),
        "retrieval_status": retrieval_status,
        "attempted_queries": attempted,
        "query_results_count": len(items),
        "native_index_records_total": index_count,
        "selected_items_count": len(items),
        "selected_items": items[:max_items],
        "hydrated_excerpt_count": sum(
            1
            for item in items
            if str(
                item.get("excerpt")
                or ""
            ).strip()
        ),
    }

    # MEMZUM said memory is unnecessary:
    # no index/engine activity is required.
    if retrieval_status == "MEMORY_NOT_REQUIRED":
        return {
            **common,
            "status": "MEMORY_NOT_REQUIRED",
            "material_quality": "NOT_REQUIRED",
            "effective_query": None,
            "attempted_queries": [],
        }

    # Fail closed on unusable retrieval source/material.
    if retrieval_status != "MEMORY_USABLE":
        return {
            **common,
            "status": retrieval_status,
            "material_quality": str(
                retrieval.get("material_quality")
                or "NO_MATERIAL"
            ),
        }

    if not items:
        return {
            **common,
            "status": "MEMORY_REQUIRED_EMPTY",
            "retrieval_status": "MEMORY_REQUIRED_EMPTY",
            "material_quality": "NO_MATERIAL",
        }

    engine = _load_local_response_engine()

    if engine is None:
        return {
            **common,
            "status": "NATIVE_MEMORY_RESPONSE_PARTIAL",
            "material_quality": "USABLE_MATERIAL",
            "local_response_engine_used": False,
        }

    engine_input = {
        "context_packet": {
            "items": items,
            "query": query,
            "source": "OBSIDIA_NATIVE_MEMORY",
            "results_count": len(items),
            "readonly": True,
            "memory_write": False,
            "allowed_to_decide": False,
            "allowed_to_act": False,
            "emits_act": False,
            "kernel_mutation": False,
            "x108_mutation": False,
            "decision_authority": "KX108_ONLY",
        },
        "query": query,
        "text": str(user_message or ""),
        "language": str(language or "fr"),
        "memory_write": False,
        "canonical_write": False,
        "allowed_to_decide": False,
        "allowed_to_act": False,
        "emits_act": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "x108_mutation": False,
        "decision_authority": "KX108_ONLY",
    }

    try:
        result = engine.build_response(
            engine_input,
            max_items=max_items,
        )
    except Exception:
        return {
            **common,
            "status": "NATIVE_MEMORY_RESPONSE_PARTIAL",
            "material_quality": "USABLE_MATERIAL",
            "local_response_engine_used": False,
        }

    if not isinstance(result, dict):
        return {
            **common,
            "status": "NATIVE_MEMORY_RESPONSE_PARTIAL",
            "material_quality": "USABLE_MATERIAL",
            "local_response_engine_used": False,
        }

    response_md = str(
        result.get("response_md")
        or ""
    )

    material_quality = str(
        result.get("material_quality")
        or "USABLE_MATERIAL"
    )

    selected_items = _apply_item_boundary(
        result.get("selected_items")
        or items[:max_items],
        max_items=max_items,
    )

    tag_counts = (
        result.get("tag_counts")
        if isinstance(
            result.get("tag_counts"),
            dict,
        )
        else {}
    )

    valid_response = bool(
        response_md
        and len(response_md) > 50
        and material_quality
        in {
            "USABLE_MATERIAL",
            "PARTIAL_MATERIAL",
            "LOW_MATERIAL",
        }
    )

    # Keep the established generic success status because current downstream
    # consumers already understand it. Provider-specific statuses are not kept.
    status = (
        "BRODY_MEMORY_RESPONSE_CHAIN_PASS"
        if valid_response
        else "NATIVE_MEMORY_RESPONSE_PARTIAL"
    )

    return {
        **common,
        "status": status,
        "retrieval_status": retrieval_status,
        "material_quality": material_quality,
        "response_md": response_md,
        "response_md_length": len(response_md),
        "selected_items_count": len(selected_items),
        "selected_items": selected_items[:max_items],
        "tag_counts": tag_counts,
        "local_response_engine_used": True,
        "final_answer_uses_response_md": valid_response,
    }


__all__ = [
    "NATIVE_MEMORY_RESPONSE_BOUNDARY",
    "build_native_memory_response",
]
