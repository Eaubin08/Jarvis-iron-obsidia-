"""
Obsidia native project-memory reader.

Pure readonly local retrieval over OBSIDIA_NATIVE_MEMORY_INDEX_V1.

Properties:
- local filesystem only
- no network
- no external retrieval service
- no memory write
- no canonical write
- no kernel/X108 mutation
- no ACT/verdict emission
- KX108 remains the sole decision authority

This module performs retrieval only.
It does not decide whether memory should be activated; MEMZUM owns that
cognitive activation upstream.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable


_REPO_ROOT = Path(__file__).resolve().parents[2]

_DEFAULT_INDEX = (
    _REPO_ROOT
    / "_obsidia_native_memory"
    / "OBSIDIA_NATIVE_MEMORY_INDEX_V1"
    / "obsidia_native_memory_records_v1.jsonl"
)

_RECORD_SCHEMA = "OBSIDIA_NATIVE_MEMORY_RECORD_V1"

NATIVE_MEMORY_BOUNDARY: dict[str, Any] = {
    "readonly": True,
    "memory_authority": False,
    "memory_write": False,
    "canonical_write": False,
    "auto_promotion": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "emits_act": False,
    "emits_verdict": False,
    "allowed_to_decide": False,
    "allowed_to_act": False,
    "decision_authority": "KX108_ONLY",
}


def _normalize_query(query: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(query or "").strip().lower(),
    )


def _safe_excerpt(
    text: str,
    max_chars: int = 900,
) -> str:
    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(text),
    ).strip()[:max_chars]


def _validate_record(
    record: dict[str, Any],
    *,
    ordinal: int,
) -> None:
    if not isinstance(record, dict):
        raise ValueError(
            f"NATIVE_MEMORY_RECORD_NOT_OBJECT:{ordinal}"
        )

    if (
        record.get("schema_version")
        != _RECORD_SCHEMA
    ):
        raise ValueError(
            "NATIVE_MEMORY_SCHEMA_MISMATCH:"
            f"{ordinal}"
        )

    if record.get("readonly") is not True:
        raise ValueError(
            "NATIVE_MEMORY_NOT_READONLY:"
            f"{ordinal}"
        )

    if record.get("memory_write") is not False:
        raise ValueError(
            "NATIVE_MEMORY_WRITE_NOT_FALSE:"
            f"{ordinal}"
        )

    if (
        record.get("decision_authority")
        != "KX108_ONLY"
    ):
        raise ValueError(
            "NATIVE_MEMORY_AUTHORITY_VIOLATION:"
            f"{ordinal}"
        )

    forbidden_true = (
        "allowed_to_decide",
        "allowed_to_act",
        "kernel_mutation",
        "x108_mutation",
        "emits_act",
        "emits_verdict",
        "auto_promotion",
    )

    for key in forbidden_true:
        if record.get(key) is not False:
            raise ValueError(
                "NATIVE_MEMORY_BOUNDARY_VIOLATION:"
                f"{ordinal}:{key}"
            )


def load_native_memory_index(
    index_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """
    Load and validate the native readonly project-memory index.

    No cache and no side effects are used here: callers receive a fresh
    in-memory representation of the current immutable artifact.
    """

    path = (
        Path(index_path)
        if index_path is not None
        else _DEFAULT_INDEX
    )

    if not path.exists():
        raise FileNotFoundError(
            f"NATIVE_MEMORY_INDEX_NOT_FOUND:{path}"
        )

    records: list[dict[str, Any]] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as fh:
        for ordinal, raw_line in enumerate(fh):
            if not raw_line.strip():
                continue

            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "NATIVE_MEMORY_INVALID_JSON:"
                    f"{ordinal}:{exc}"
                ) from exc

            _validate_record(
                record,
                ordinal=ordinal,
            )

            records.append(record)

    ids = [
        str(record.get("native_id") or "")
        for record in records
    ]

    if any(not value for value in ids):
        raise ValueError(
            "NATIVE_MEMORY_EMPTY_NATIVE_ID"
        )

    if len(ids) != len(set(ids)):
        raise ValueError(
            "NATIVE_MEMORY_DUPLICATE_NATIVE_ID"
        )

    return records


def _score_record(
    *,
    q_norm: str,
    q_underscore: str,
    record: dict[str, Any],
) -> int:
    """
    Preserve the proven historical ranking semantics over the native schema.

    Weights:
      title substring       +160
      source/path substring +150
      body substring        +120
      underscore tag        +130
      exact tag             +130
      tag substring         +100
      underscore substring  +100
    """

    title = str(
        record.get("title") or ""
    ).lower()

    path = str(
        record.get("source_ref") or ""
    ).lower()

    body = str(
        record.get("text_excerpt") or ""
    ).lower()

    tags = [
        str(tag).lower()
        for tag in (
            record.get("tags") or []
        )
    ]

    score = 0

    if q_norm in title:
        score += 160

    if q_norm in path:
        score += 150

    if q_norm in body:
        score += 120

    if q_underscore in tags:
        score += 130

    if any(
        q_norm == tag
        for tag in tags
    ):
        score += 130

    if any(
        q_norm in tag
        for tag in tags
    ):
        score += 100

    if any(
        q_underscore in tag
        for tag in tags
    ):
        score += 100

    return score


def query_native_memory(
    query: str,
    records: Iterable[dict[str, Any]] | None = None,
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """
    Query native memory using the parity-proven deterministic ranking.

    Empty queries fail closed and return no material.
    """

    q_norm = _normalize_query(query)

    if not q_norm:
        return []

    if limit <= 0:
        return []

    q_underscore = q_norm.replace(
        " ",
        "_",
    )

    material = (
        list(records)
        if records is not None
        else load_native_memory_index()
    )

    matched: list[
        tuple[int, dict[str, Any]]
    ] = []

    for record in material:
        score = _score_record(
            q_norm=q_norm,
            q_underscore=q_underscore,
            record=record,
        )

        if score > 0:
            matched.append(
                (score, record)
            )

    # Stable descending score ordering deliberately preserves index order
    # on equal scores, matching the parity-proven historical behavior.
    matched.sort(
        key=lambda item: -item[0]
    )

    items: list[dict[str, Any]] = []

    for rank, (score, record) in enumerate(
        matched[:limit],
        1,
    ):
        tags = list(
            record.get("tags") or []
        )

        excerpt = _safe_excerpt(
            record.get("text_excerpt") or "",
            max_chars=900,
        )

        source_ref = str(
            record.get("source_ref") or ""
        )

        path = str(
            record.get("normalized_source_path")
            or source_ref
        )

        items.append({
            "rank": rank,
            "id": record.get("native_id"),
            "title": record.get("title", ""),
            "source": (
                record.get("source_type")
                or "OBSIDIA_NATIVE_MEMORY_V1"
            ),
            "path": path,
            "tags": tags,
            "score": score,
            "excerpt": excerpt,
            "source_ref": source_ref,

            # Explicitly retain non-sovereignty on each surfaced item.
            "readonly": True,
            "memory_write": False,
            "emits_act": False,
            "decision_authority": "KX108_ONLY",
        })

    return items


def build_native_memory_retrieval_snapshot(
    query: str,
    *,
    memory_required: bool,
    limit: int = 8,
    index_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Build the provider-neutral readonly retrieval envelope.

    MEMZUM decides `memory_required` upstream.
    This function only obeys that activation signal.
    """

    base: dict[str, Any] = {
        "schema_version": (
            "OBSIDIA_NATIVE_MEMORY_RETRIEVAL_V1"
        ),
        "source_type": "OBSIDIA_NATIVE_MEMORY_V1",
        "query": str(query or ""),
        "query_normalized": _normalize_query(query),
        "memory_required": bool(memory_required),
        "selected_items_count": 0,
        "selected_items": [],
        "index_record_count": 0,
        **NATIVE_MEMORY_BOUNDARY,
    }

    if not memory_required:
        return {
            **base,
            "status": "MEMORY_NOT_REQUIRED",
            "material_quality": "NOT_REQUIRED",
        }

    if not base["query_normalized"]:
        return {
            **base,
            "status": "MEMORY_REQUIRED_EMPTY_QUERY",
            "material_quality": "NO_MATERIAL",
        }

    try:
        records = load_native_memory_index(
            index_path=index_path,
        )
    except FileNotFoundError:
        return {
            **base,
            "status": "MEMORY_REQUIRED_NO_NATIVE_SOURCE",
            "material_quality": "NO_MATERIAL",
        }
    except (ValueError, OSError):
        return {
            **base,
            "status": "MEMORY_REQUIRED_INVALID_NATIVE_SOURCE",
            "material_quality": "NO_MATERIAL",
        }

    items = query_native_memory(
        query,
        records,
        limit=limit,
    )

    if not items:
        return {
            **base,
            "status": "MEMORY_REQUIRED_EMPTY",
            "material_quality": "NO_MATERIAL",
            "index_record_count": len(records),
        }

    return {
        **base,
        "status": "MEMORY_USABLE",
        "material_quality": "USABLE_MATERIAL",
        "selected_items_count": len(items),
        "selected_items": items,
        "index_record_count": len(records),
    }


__all__ = [
    "NATIVE_MEMORY_BOUNDARY",
    "load_native_memory_index",
    "query_native_memory",
    "build_native_memory_retrieval_snapshot",
]
