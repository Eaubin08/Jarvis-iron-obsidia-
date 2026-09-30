# runtime_wiring/source_runtime/source_family_selector.py
# Maps user message content → relevant source families for hydration.
# KX108_ONLY. No ACT. No write. No extraction.

from __future__ import annotations
from typing import Dict, List, Tuple

# Keyword → family scoring map (FR + EN terms)
_FAMILY_KEYWORD_MAP: Dict[str, List[str]] = {
    "COGNITIVE_REINTEGRATION": [
        "x108", "kx108", "gouvernance", "governance", "kernel", "noyau",
        "décision", "decision", "autorité", "authority", "cognition", "cognitive",
        "brody", "voice", "voix", "réponse", "réponses", "response",
        "pipeline", "agent", "spec", "reintegration", "moteur",
    ],
    "RSSI_RGPD": [
        "rgpd", "gdpr", "conformité", "compliance", "données personnelles",
        "data protection", "protection données", "vie privée", "privacy",
        "dpo", "iso 27001", "article 5",
    ],
    "ATLAS": [
        "atlas", "arbre", "arbres", "tree", "trees", "structure",
        "branchable", "architecture", "module", "composant", "component",
        "carte", "mapping", "cartographie", "34 arbres",
    ],
    "COMPLIANCE_DATA_GOVERNANCE": [
        "conformité", "compliance", "gouvernance données", "data governance",
        "audit", "règle", "rule", "politique", "policy", "contrôle",
        "backlog", "implémentation",
    ],
    "RSSI_SECURITY_PRESENTATION": [
        "sécurité", "security", "securite", "rssi", "risque", "risk",
        "menace", "threat", "cyber", "cybersecurite", "cybersecurity",
        "présentation sécurité", "security presentation",
    ],
    "EXTERNAL_SIGNALS": [
        "timeverse", "temps", "temporal", "time", "externe", "external",
        "signal", "c459", "chronologie", "timeline", "temporalité",
        "horloge", "clock", "séquence temporelle",
    ],
    "NARRATIVE_PROVENANCE_LAYER": [
        "npl", "narrative", "provenance", "historique", "history",
        "trace", "origine", "origin", "contexte narratif", "narrative layer",
        "memory", "mémoire", "graphiti", "neo4j", "layer",
    ],
    # P32 — 8th family + P35 interlanguage extension
    "OS_TRAD_REVERSE_OS": [
        "os trad", "reverse os", "reverse", "ssr", "mmonde",
        "34 arbres", "34arbres", "arbre", "arbres", "tensor",
        "shazam", "hexaflux", "bdf", "mcp bridge", "mcp",
        "agents 52", "52 agents", "non décision", "non decision",
        "pipeline cognitif", "contexte packet", "context packet",
        "traduction", "intermediate representation", "langage intermédiaire",
        "ir", "structure cognitive", "double cerveau", "jarvis",
        # P35 — interlanguage canon extension keywords
        "ir alphabet", "alphabet ir", "reverse os interlanguage",
        "réciproque miroir", "reciproque miroir", "twin_call", "twin call",
        "scf réciproque", "scf reciproque", "inversion path",
        "translation layer", "os trad interlanguage", "interlanguage canon",
        "alphabet reverse", "langage universel symbolique",
    ],
}

# Fallback order when no keyword matches — most broadly useful families first
_DEFAULT_FAMILY_ORDER = [
    "COGNITIVE_REINTEGRATION",
    "ATLAS",
    "NARRATIVE_PROVENANCE_LAYER",
    "RSSI_RGPD",
    "COMPLIANCE_DATA_GOVERNANCE",
    "RSSI_SECURITY_PRESENTATION",
    "EXTERNAL_SIGNALS",
    "OS_TRAD_REVERSE_OS",
]


def select_families_for_message(
    message: str,
    available_families: List[str],
    max_families: int = 3,
    fallback_limit: int = 3,
) -> Tuple[List[str], bool]:
    """
    Select relevant source families for a given message.

    Args:
        message: User message text.
        available_families: Families with locally available packs.
        max_families: Max families to return when keywords match.
        fallback_limit: Max families to return when no keywords match.

    Returns:
        (selected_families, keyword_matched)
        keyword_matched=True if at least one keyword hit was found.
    """
    if not available_families:
        return [], False

    msg_lower = message.lower()
    scores: Dict[str, int] = {}

    for family, keywords in _FAMILY_KEYWORD_MAP.items():
        if family not in available_families:
            continue
        score = sum(1 for kw in keywords if kw in msg_lower)
        if score > 0:
            scores[family] = score

    if scores:
        ranked = sorted(scores.keys(), key=lambda f: scores[f], reverse=True)
        return ranked[:max_families], True

    # Fallback: preferred order among available families
    ordered = [f for f in _DEFAULT_FAMILY_ORDER if f in available_families]
    remaining = [f for f in available_families if f not in ordered]
    fallback = (ordered + remaining)[:fallback_limit]
    return fallback, False


def describe_selection(
    message: str,
    selected: List[str],
    keyword_matched: bool,
) -> str:
    """Return a short human-readable summary of the family selection."""
    if not selected:
        return "NO_FAMILIES_SELECTED"
    method = "KEYWORD_MATCH" if keyword_matched else "DEFAULT_FALLBACK"
    return f"{method}:{','.join(selected)}"
