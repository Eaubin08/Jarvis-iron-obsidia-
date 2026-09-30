"""
Qualification of lexical unknowns before cognitive pre-reasoning.

Purpose:
- preserve raw lexical unknowns,
- separate surface-language words,
- recognize unknown tokens already resolved by a canonical semantic route,
- keep genuinely unresolved concepts available to C265 -> C274.

No retrieval.
No provider.
No memory.
No sovereign decision.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


_FR_SURFACE_WORDS = {
    "a",
    "au",
    "aux",
    "avec",
    "beaucoup",
    "ce",
    "ces",
    "cette",
    "de",
    "des",
    "du",
    "en",
    "et",
    "je",
    "la",
    "le",
    "les",
    "leur",
    "leurs",
    "me",
    "mes",
    "moi",
    "mon",
    "ma",
    "nous",
    "on",
    "ou",
    "par",
    "pour",
    "que",
    "qui",
    "sa",
    "se",
    "ses",
    "son",
    "sur",
    "ta",
    "te",
    "tes",
    "toi",
    "ton",
    "tu",
    "un",
    "une",
    "vous",
    "votre",
    "vos",
}


# Ordinary conversational/surface-language units.
#
# Recovered from the previously-proven unknown-qualification
# branch. These words are not semantic knowledge entries and
# grant no authority. Their only role is to prevent ordinary
# language from becoming causal epistemic debt.
_COMMON_SURFACE_WORDS = {
    "bonjour",
    "bonsoir",
    "salut",
    "coucou",
    "hello",
    "hey",
    "hi",
    "yo",
    "merci",
    "thank",
    "thanks",
    "gars",
    "mec",
    "source",
    "test",
    "context",
    "contexte",
    "maman",
    "papa",
    "mamie",
    "papi",
    "nickel",
    "parfait",
    "vient",
    "stabiliser",
    "reprend",
    "reprends",
    "peux",
    "repondre",
    "reponds",
    "simplement",
    "naturellement",
    "revoir",
    "bientot",
}


_EN_SURFACE_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "for",
    "from",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "we",
    "with",
    "you",
    "your",
}


# Minimal semantic equivalences.
# These are not knowledge entries.
# They only normalize wording already represented by the semantic router.
_SEMANTIC_EQUIVALENTS = {
    "statut": {
        "statut",
        "status",
        "etat",
        "state",
    },
    "status": {
        "statut",
        "status",
        "etat",
        "state",
    },
    "etat": {
        "statut",
        "status",
        "etat",
        "state",
    },
    "actuel": {
        "actuel",
        "current",
        "present",
    },
    "current": {
        "actuel",
        "current",
        "present",
    },
}


def _normalize(value: Any) -> str:
    text = str(value or "").strip().lower()

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    return text


def _tokens(value: Any) -> list[str]:
    return [
        token
        for token in re.findall(
            r"[a-z0-9_]+",
            _normalize(value),
        )
        if token
    ]


def _uniq_strings(values: Any) -> list[str]:
    out: list[str] = []

    if not isinstance(values, list):
        return out

    for value in values:
        token = _normalize(value)

        if token and token not in out:
            out.append(token)

    return out


def _semantic_vocabulary(
    semantic_query_snapshot: dict[str, Any],
) -> set[str]:
    """
    Build vocabulary already resolved by the semantic router.

    Important:
    FALLBACK_WORD_EXTRACTION is not semantic resolution.
    Only a canonical TOPIC_MATCHED route is allowed to resolve lexical
    unknowns here.
    """

    if not isinstance(
        semantic_query_snapshot,
        dict,
    ):
        return set()

    if (
        semantic_query_snapshot.get("route")
        != "TOPIC_MATCHED"
    ):
        return set()

    if (
        semantic_query_snapshot.get("is_canonical")
        is not True
    ):
        return set()

    vocabulary: set[str] = set()

    fields = (
        semantic_query_snapshot.get(
            "semantic_query",
            "",
        ),
        semantic_query_snapshot.get(
            "primary_query",
            "",
        ),
        semantic_query_snapshot.get(
            "topic",
            "",
        ),
    )

    for value in fields:
        vocabulary.update(
            _tokens(value)
        )

    fallbacks = semantic_query_snapshot.get(
        "fallback_queries",
        [],
    )

    if isinstance(fallbacks, list):
        for value in fallbacks:
            vocabulary.update(
                _tokens(value)
            )

    return vocabulary


def _is_semantically_resolved(
    token: str,
    semantic_vocabulary: set[str],
) -> bool:
    if token in semantic_vocabulary:
        return True

    equivalents = _SEMANTIC_EQUIVALENTS.get(
        token,
        {token},
    )

    return bool(
        equivalents
        & semantic_vocabulary
    )


def qualify_unknowns(
    *,
    user_message: str,
    language: str = "unknown",
    lexical_unknowns: list[str] | None = None,
    semantic_query_snapshot: dict[str, Any] | None = None,
    known_concept_ids: list[str] | None = None,
    entities: list[dict[str, Any]] | None = None,
    retrieval_targets: list[str] | None = None,
) -> dict[str, Any]:
    """
    Classify lexical unknowns without resolving new knowledge.

    Only `unresolved_unknowns` should become causal downstream.
    """

    lexical = _uniq_strings(
        lexical_unknowns or []
    )

    semantic = (
        semantic_query_snapshot
        if isinstance(
            semantic_query_snapshot,
            dict,
        )
        else {}
    )

    lang = _normalize(language)

    # Brody accepts mixed-language operator input.
    # A declared language must not make ordinary words from another
    # supported language causal cognitive unknowns.
    surface_words = (
        _FR_SURFACE_WORDS
        | _EN_SURFACE_WORDS
        | _COMMON_SURFACE_WORDS
        | {
            "dans",
            "ceci",
            "cela",
        }
    )

    semantic_vocabulary = (
        _semantic_vocabulary(
            semantic
        )
    )

    # ------------------------------------------------------------
    # Semantic continuity from already-produced IR evidence.
    #
    # This does NOT create knowledge.
    # It only prevents downstream stages from forgetting concepts
    # and entities already recognized upstream.
    # ------------------------------------------------------------

    known_context_vocabulary: set[str] = set()

    for concept_id in (
        known_concept_ids or []
    ):
        known_context_vocabulary.update(
            _tokens(concept_id)
        )

    for entity in (
        entities or []
    ):
        if not isinstance(entity, dict):
            continue

        known_context_vocabulary.update(
            _tokens(
                entity.get("entity")
            )
        )

        known_context_vocabulary.update(
            _tokens(
                entity.get("source_token")
            )
        )

    retrieval_vocabulary: set[str] = set()

    for target in (
        retrieval_targets or []
    ):
        retrieval_vocabulary.update(
            _tokens(target)
        )

    canonical_memory_query = (
        semantic.get("route")
        == "TOPIC_MATCHED"
        and semantic.get("is_canonical")
        is True
        and semantic.get("topic")
        == "MEMORY_QUERY"
    )

    surface_language_unknowns: list[str] = []
    semantically_resolved_unknowns: list[str] = []

    known_context_resolved_unknowns: list[str] = []

    # A retrieval target can be unknown as knowledge while still
    # being a valid thing to search for. It must therefore remain
    # visible without blocking reasoning before retrieval.
    retrieval_target_unknowns: list[str] = []

    # Words belonging to a canonical memory-recall frame such as
    # "retrouve", "precedente", etc. are not epistemic unknowns.
    route_framing_unknowns: list[str] = []

    unresolved_unknowns: list[str] = []

    for token in lexical:
        if token in surface_words:
            surface_language_unknowns.append(
                token
            )
            continue

        if _is_semantically_resolved(
            token,
            semantic_vocabulary,
        ):
            semantically_resolved_unknowns.append(
                token
            )
            continue

        if token in known_context_vocabulary:
            known_context_resolved_unknowns.append(
                token
            )
            continue

        if canonical_memory_query:
            if token in retrieval_vocabulary:
                retrieval_target_unknowns.append(
                    token
                )
            else:
                route_framing_unknowns.append(
                    token
                )
            continue

        unresolved_unknowns.append(
            token
        )

    return {
        "status": "UNKNOWN_QUALIFICATION_PASS",
        "schema": "BRODY_UNKNOWN_QUALIFICATION_V1",

        "user_message": str(
            user_message or ""
        ),
        "language": str(
            language or "unknown"
        ),

        "lexical_unknowns": lexical,

        "surface_language_unknowns": (
            surface_language_unknowns
        ),

        "semantically_resolved_unknowns": (
            semantically_resolved_unknowns
        ),

        "known_context_resolved_unknowns": (
            known_context_resolved_unknowns
        ),

        "retrieval_target_unknowns": (
            retrieval_target_unknowns
        ),

        "route_framing_unknowns": (
            route_framing_unknowns
        ),

        "known_concept_ids": list(
            known_concept_ids or []
        ),

        "retrieval_targets": list(
            retrieval_targets or []
        ),

        "unresolved_unknowns": (
            unresolved_unknowns
        ),

        "semantic_route": semantic.get(
            "route"
        ),
        "semantic_topic": semantic.get(
            "topic"
        ),
        "semantic_is_canonical": semantic.get(
            "is_canonical"
        ),

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
    "qualify_unknowns",
]
