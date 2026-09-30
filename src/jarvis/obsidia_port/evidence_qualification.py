from __future__ import annotations

import re
from collections import Counter
from typing import Any


PROVENANCE_ONLY = "PROVENANCE_ONLY"
SUPPORTING_MATERIAL = "SUPPORTING_MATERIAL"
CLAIM_SUPPORT = "CLAIM_SUPPORT"

_KNOWN_SUBJECTS = {
    "obsidia": ("obsidia",),
    "brody": ("brody",),
    "jarjar": ("jarjar", "jar jar"),
    "x108": ("x108", "x-108"),
    "kx108": ("kx108", "kx-108"),
}

_PROPERTY_PATTERNS = {
    "SIZE": (
        r"\btailles?\b",
        r"\bsize\b",
        r"\bdimension(?:s)?\b",
        r"\bgrand(?:eur)?\b",
    ),
    "COUNT": (
        r"\bcombien\b",
        r"\bnombre\b",
        r"\bcount\b",
        r"\btotal\b",
        r"\barbres?\b",
    ),
    "VERSION": (
        r"\bversion\b",
        r"\bv\d+(?:[._-]\d+)*\b",
        r"\brelease\b",
    ),
    "STATUS": (
        r"\bstatus\b",
        r"\bstatut\b",
        r"\betat\b",
        r"\b[eé]tat\b",
        r"\bready\b",
        r"\bblocked\b",
    ),
    "ROLE": (
        r"\br[oô]le\b",
        r"\brole\b",
        r"\ben tant que\b",
        r"\bmission\b",
        r"\bfonction\b",
    ),
    "CAPABILITY": (
        r"\bcapacit(?:e|é|es|és)\b",
        r"\bcapability\b",
        r"\bpeux\b",
        r"\bpeut\b",
        r"\bsavoir faire\b",
    ),
}

_PROPERTY_RELATION_PATTERNS = {
    "SIZE": (
        r"{subject}.{{0,80}}\b(?:a\s+(?:une\s+)?taille|a\s+pour\s+taille|taille|size|dimension|mesure)\b.{{0,80}}(?:\d+|arbres?|taille|size|dimension)",
        r"\b(?:taille|size|dimension)\s+(?:de|d['’])\s*{subject}\b.{{0,80}}(?:\d+|arbres?)",
    ),
    "COUNT": (
        r"{subject}.{{0,80}}\b(?:compte|contient|comprend|inclut|a|as|poss[eè]de)\b.{{0,80}}\d+",
        r"\b(?:nombre|count|total)\s+(?:de|d['’])\s*{subject}\b.{{0,80}}\d+",
    ),
    "VERSION": (
        r"{subject}.{{0,80}}\b(?:version|v\d+|release)\b.{{0,80}}(?:\d+|v\d+)",
        r"\bversion\s+(?:de|d['’])\s*{subject}\b.{{0,80}}(?:\d+|v\d+)",
    ),
    "STATUS": (
        r"{subject}.{{0,80}}\b(?:status|statut|[eé]tat|est)\b.{{0,80}}(?:ready|blocked|actif|active|gel[eé]|pass|fail|ouvert|ferm[eé])",
        r"\b(?:status|statut|[eé]tat)\s+(?:de|d['’])\s*{subject}\b.{{0,80}}\w+",
    ),
    "ROLE": (
        r"{subject}.{{0,80}}\b(?:r[oô]le|role|mission|fonction|est|agit comme|sert de)\b.{{0,120}}",
        r"\b(?:r[oô]le|role|mission|fonction)\s+(?:de|d['’]|en tant que)\s*{subject}\b.{{0,120}}",
    ),
    "CAPABILITY": (
        r"{subject}.{{0,80}}\b(?:peut|permet|capacit(?:e|é|es|és)|capability|sait)\b.{{0,120}}",
        r"\b(?:capacit(?:e|é|es|és)|capability)\s+(?:de|d['’])\s*{subject}\b.{{0,120}}",
    ),
}


def _compact_text(value: Any, *, limit: int = 1200) -> str:
    text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _subject_hits(text: str) -> list[str]:
    lowered = text.lower()
    hits = []
    for subject, aliases in _KNOWN_SUBJECTS.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", lowered) for alias in aliases):
            hits.append(subject.upper())
    return hits


def _property_hits(text: str) -> list[str]:
    lowered = text.lower()
    hits = []
    for family, patterns in _PROPERTY_PATTERNS.items():
        if any(re.search(pattern, lowered) for pattern in patterns):
            hits.append(family)
    return hits


def _detect_requested_subjects(
    user_message: str,
    semantic_snapshot: dict[str, Any] | None,
    requested_memory_target: str | None,
) -> list[str]:
    haystack = " ".join(
        _compact_text(part, limit=600)
        for part in (
            user_message,
            requested_memory_target,
            (semantic_snapshot or {}).get("primary_query"),
            (semantic_snapshot or {}).get("semantic_query"),
            (semantic_snapshot or {}).get("topic"),
        )
    )
    return _subject_hits(haystack)


def _detect_requested_properties(user_message: str) -> list[str]:
    return _property_hits(user_message)


def _item_ref(item: dict[str, Any]) -> str:
    for key in (
        "title",
        "file_name",
        "source_ref",
        "source_original_path",
        "native_id",
        "id",
        "name",
        "family",
    ):
        value = _compact_text(item.get(key), limit=240)
        if value:
            return value
    return "selected item"


def _item_material(item: dict[str, Any]) -> str:
    parts = []
    for key in (
        "material",
        "excerpt",
        "text_excerpt",
        "content_preview",
        "preview",
        "content",
        "text",
        "summary",
    ):
        value = _compact_text(item.get(key), limit=1600)
        if value:
            parts.append(value)
    material = _compact_text("\n".join(parts), limit=1600)
    if material.startswith("[METADATA_ONLY:"):
        return ""
    return material


def _metadata_text(item: dict[str, Any]) -> str:
    pieces = []
    for key in (
        "title",
        "file_name",
        "source_ref",
        "source_original_path",
        "native_id",
        "family",
        "tags",
        "taxonomy",
    ):
        value = item.get(key)
        if value:
            pieces.append(str(value))
    return _compact_text(" ".join(pieces), limit=1200)


def _claim_supported_by_material(
    material: str,
    requested_subjects: list[str],
    requested_properties: list[str],
) -> bool:
    if not material or not requested_subjects or not requested_properties:
        return False

    lowered = material.lower()
    for subject in requested_subjects:
        aliases = _KNOWN_SUBJECTS.get(subject.lower(), (subject.lower(),))
        for prop in requested_properties:
            for alias in aliases:
                subject_pattern = re.escape(alias)
                for pattern in _PROPERTY_RELATION_PATTERNS.get(prop, ()):
                    if re.search(
                        pattern.format(subject=subject_pattern),
                        lowered,
                        flags=re.IGNORECASE,
                    ):
                        return True
    return False


def _qualify_item(
    *,
    kind: str,
    item: dict[str, Any],
    requested_subjects: list[str],
    requested_properties: list[str],
) -> dict[str, Any]:
    material = _item_material(item)
    metadata = _metadata_text(item)
    material_subjects = _subject_hits(material)
    material_properties = _property_hits(material)
    metadata_subjects = _subject_hits(metadata)
    metadata_properties = _property_hits(metadata)

    subject_hits = sorted(set(material_subjects + metadata_subjects))
    property_hits = sorted(set(material_properties + metadata_properties))

    if _claim_supported_by_material(
        material,
        requested_subjects,
        requested_properties,
    ):
        qualification = CLAIM_SUPPORT
    elif material:
        qualification = SUPPORTING_MATERIAL
    else:
        qualification = PROVENANCE_ONLY

    return {
        "source_kind": kind,
        "source_ref": _item_ref(item),
        "qualification": qualification,
        "subject_hits": subject_hits,
        "property_hits": property_hits,
        "bounded_material": material[:1200],
    }


def _memory_items(native_memory_selected_items: Any) -> list[dict[str, Any]]:
    if not isinstance(native_memory_selected_items, list):
        return []
    return [
        item
        for item in native_memory_selected_items
        if isinstance(item, dict)
    ]


def _source_items(source_pack_hydrated_entries: Any) -> list[dict[str, Any]]:
    if not isinstance(source_pack_hydrated_entries, list):
        return []
    return [
        item
        for item in source_pack_hydrated_entries
        if isinstance(item, dict)
    ]


def build_evidence_qualification_snapshot(
    *,
    user_message: str,
    semantic_snapshot: dict[str, Any] | None = None,
    requested_memory_target: str | None = None,
    native_memory_selected_items: Any = None,
    source_pack_hydrated_entries: Any = None,
) -> dict[str, Any]:
    requested_subjects = _detect_requested_subjects(
        user_message,
        semantic_snapshot,
        requested_memory_target,
    )
    requested_properties = _detect_requested_properties(user_message)
    claim_support_required = bool(
        requested_subjects
        and requested_properties
    )

    qualified_items = []
    for item in _memory_items(native_memory_selected_items):
        qualified_items.append(
            _qualify_item(
                kind="NATIVE_MEMORY",
                item=item,
                requested_subjects=requested_subjects,
                requested_properties=requested_properties,
            )
        )
    for item in _source_items(source_pack_hydrated_entries):
        qualified_items.append(
            _qualify_item(
                kind="SOURCE_PACK",
                item=item,
                requested_subjects=requested_subjects,
                requested_properties=requested_properties,
            )
        )

    counts = Counter(
        item["qualification"]
        for item in qualified_items
    )
    for key in (PROVENANCE_ONLY, SUPPORTING_MATERIAL, CLAIM_SUPPORT):
        counts.setdefault(key, 0)

    claim_support_available = counts[CLAIM_SUPPORT] > 0

    return {
        "status": "EVIDENCE_QUALIFICATION_READY",
        "requested_subjects": requested_subjects,
        "requested_properties": requested_properties,
        "claim_support_required": claim_support_required,
        "claim_support_available": claim_support_available,
        "counts_by_qualification": dict(counts),
        "qualified_items": qualified_items,
        "readonly": True,
        "advisory_only": True,
        "memory_write": False,
        "emits_act": False,
        "kernel_mutation": False,
        "x108_mutation": False,
        "decision_authority": "KX108_ONLY",
    }


def build_qualified_context(snapshot: dict[str, Any]) -> str:
    lines = [
        "[QUALIFIED READONLY EVIDENCE]",
        "Evidence qualifier: Jarjar-owned advisory layer.",
        "Routing metadata and retrieved provenance are not factual claim support.",
        "decision_authority=KX108_ONLY readonly=True advisory_only=True memory_write=False emits_act=False kernel_mutation=False x108_mutation=False",
        "requested_subjects="
        + ", ".join(snapshot.get("requested_subjects") or ["NONE"]),
        "requested_properties="
        + ", ".join(snapshot.get("requested_properties") or ["NONE"]),
        "claim_support_required="
        + str(bool(snapshot.get("claim_support_required"))),
        "claim_support_available="
        + str(bool(snapshot.get("claim_support_available"))),
    ]

    counts = snapshot.get("counts_by_qualification") or {}
    lines.append(
        "qualification_counts="
        + ", ".join(
            f"{key}:{int(counts.get(key) or 0)}"
            for key in (
                PROVENANCE_ONLY,
                SUPPORTING_MATERIAL,
                CLAIM_SUPPORT,
            )
        )
    )

    if (
        snapshot.get("claim_support_required")
        and not snapshot.get("claim_support_available")
    ):
        lines.extend([
            "",
            "ASSERTION_BOUNDARY:",
            "Selected readonly material does NOT establish the requested subject-property relation.",
            "Do not infer a value from SUPPORTING_MATERIAL, PROVENANCE_ONLY, filenames, families, tags, or routing metadata.",
            "A grounded insufficiency answer is acceptable.",
        ])

    for index, item in enumerate(snapshot.get("qualified_items") or [], 1):
        lines.extend([
            "",
            f"ITEM {index}",
            f"source_kind={item.get('source_kind')}",
            f"source_ref={item.get('source_ref')}",
            f"qualification={item.get('qualification')}",
            "subject_hits="
            + ", ".join(item.get("subject_hits") or ["NONE"]),
            "property_hits="
            + ", ".join(item.get("property_hits") or ["NONE"]),
        ])
        material = _compact_text(item.get("bounded_material"), limit=900)
        if material:
            lines.append("bounded_material=" + material)
        else:
            lines.append("bounded_material=NONE")

    return "\n".join(lines)


__all__ = [
    "PROVENANCE_ONLY",
    "SUPPORTING_MATERIAL",
    "CLAIM_SUPPORT",
    "build_evidence_qualification_snapshot",
    "build_qualified_context",
]
