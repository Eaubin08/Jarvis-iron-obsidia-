from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


_CANON_PATH = (
    Path(__file__).resolve().parents[2]
    / "_source_packs"
    / "REVERSE_OS_INTERLANGUAGE_CANON_V1"
    / "evidence"
    / "reverse_os_interlanguage_canon_v1.json"
)

_SOURCE_REF = (
    "_source_packs/REVERSE_OS_INTERLANGUAGE_CANON_V1/"
    "evidence/reverse_os_interlanguage_canon_v1.json"
)


# Surface-language scaffolding only.
# This is NOT Brody semantic knowledge.
_FR_SCAFFOLD = {
    "a", "au", "aux", "avec", "ce", "ces", "cette", "de", "des",
    "du", "en", "et", "la", "le", "les", "l", "pour", "sans",
    "sur", "un", "une",
    "explique", "expliquer", "montre", "montrer", "dis", "dire",
    "donne", "donner", "analyse", "analyser", "verifie", "verifier",
    "comment", "pourquoi", "quoi", "quel", "quelle", "quels", "quelles",
}

_EN_SCAFFOLD = {
    "a", "an", "and", "for", "in", "of", "on", "the", "to", "with",
    "without", "explain", "show", "tell", "give", "analyze", "analyse",
    "verify", "what", "why", "how", "which",
}


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(
        ch for ch in text
        if not unicodedata.combining(ch)
    )
    text = text.casefold().replace("_", " ")
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def _alias_variants(value: Any) -> list[str]:
    raw = str(value or "").strip()
    if not raw:
        return []

    variants = [raw]

    for separator in ("/", "↔"):
        expanded: list[str] = []
        for item in variants:
            expanded.extend(item.split(separator))
        variants = expanded

    out: list[str] = []
    for item in variants:
        normalized = _normalize(item)
        if normalized and normalized not in out:
            out.append(normalized)

    return out


def _load_canon() -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(
            _CANON_PATH.read_text(
                encoding="utf-8-sig",
            )
        )
    except Exception as exc:
        return None, f"{type(exc).__name__}:{exc}"

    authority = data.get("authority") or {}

    if (
        authority.get("decision_authority") != "KX108_ONLY"
        or authority.get("readonly") is not True
        or authority.get("allowed_to_decide") is not False
    ):
        return None, "CANON_BOUNDARY_INVALID"

    return data, None


def _known_aliases(
    canon: dict[str, Any],
) -> tuple[list[tuple[str, ...]], dict[tuple[str, ...], str]]:
    aliases: dict[tuple[str, ...], str] = {}

    for symbol in canon.get("ir_alphabet", []):
        normalized = _normalize(symbol)
        if normalized:
            key = tuple(normalized.split())
            aliases[key] = f"IR:{symbol}"

    for concept in canon.get("concepts", []):
        if not isinstance(concept, dict):
            continue

        concept_id = str(
            concept.get("id") or "UNKNOWN_CONCEPT"
        )

        for field in ("id", "fr", "en", "hanzi"):
            for alias in _alias_variants(
                concept.get(field)
            ):
                key = tuple(alias.split())
                if key:
                    aliases[key] = concept_id

    ordered = sorted(
        aliases,
        key=lambda item: (-len(item), item),
    )

    return ordered, aliases


def calibrate_lexical_knownness(
    text: str,
    language: str = "unknown",
) -> dict[str, Any]:
    canon, error = _load_canon()

    if canon is None:
        return {
            "status": "SOURCE_UNAVAILABLE",
            "unknowns": [
                "LEXICAL_CALIBRATION_SOURCE_UNAVAILABLE"
            ],
            "known_concept_ids": [],
            "source_ref": _SOURCE_REF,
            "source_error": error,
            "readonly": True,
            "decision_authority": "KX108_ONLY",
        }

    normalized_text = _normalize(text)
    tokens = normalized_text.split()

    alias_order, alias_map = _known_aliases(
        canon
    )

    covered: set[int] = set()
    known_concepts: list[str] = []

    for alias in alias_order:
        width = len(alias)

        if width == 0 or width > len(tokens):
            continue

        for start in range(
            0,
            len(tokens) - width + 1,
        ):
            if tuple(
                tokens[start:start + width]
            ) != alias:
                continue

            covered.update(
                range(start, start + width)
            )

            concept_id = alias_map[alias]
            if concept_id not in known_concepts:
                known_concepts.append(
                    concept_id
                )

    scaffold = (
        _FR_SCAFFOLD
        if language == "fr"
        else _EN_SCAFFOLD
        if language == "en"
        else _FR_SCAFFOLD | _EN_SCAFFOLD
    )

    unknowns: list[str] = []

    for index, token in enumerate(tokens):
        if index in covered:
            continue

        if token in scaffold:
            continue

        # Ignore punctuation remnants, tiny grammatical units,
        # and pure numeric values.
        if len(token) < 3 or token.isdigit():
            continue

        if token not in unknowns:
            unknowns.append(token)

    return {
        "status": "CALIBRATED",
        "unknowns": unknowns,
        "known_concept_ids": known_concepts,
        "source_ref": _SOURCE_REF,
        "source_status": canon.get("status"),
        "unknown_policy": (
            canon.get("language_policy", {})
            .get("unknown_policy")
        ),
        "readonly": True,
        "decision_authority": "KX108_ONLY",
    }

