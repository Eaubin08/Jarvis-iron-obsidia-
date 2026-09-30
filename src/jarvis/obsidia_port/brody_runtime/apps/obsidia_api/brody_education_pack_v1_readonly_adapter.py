"""
Brody Education Pack V1 Readonly Adapter
SCOPE: READONLY_BINDING_PREP — EDUCATION_CONTEXT_ONLY
DECISION_AUTHORITY: KX108_ONLY

Lit le Pack Brody V1 enrichi depuis le chemin freeze local.
Injecte sous la clé `education_pack_v1_readonly_context`.
Jamais sous decision / gate / kernel_result / authority_result / cic_readonly_context.

Ce que Brody PEUT faire avec ce contexte :
  - répondre à des questions sur l'architecture Obsidia X-108
  - expliquer les domaines, le pipeline, les invariants
  - refuser correctement les pièges selon BRODY_V1_FORBIDDEN_BELIEFS.md

Ce que Brody NE PEUT PAS faire :
  - décider, autoriser, bloquer
  - activer ACT ou émettre un verdict
  - écrire en mémoire, Graphiti, Neo4j
  - modifier le kernel
  - promouvoir DEFERRED en canonique
  - utiliser sigma/contracts.broken-ragnarok.py comme exemple opérationnel
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ── Chemin freeze (relatif à la racine projet) ─────────────────────────────
_PACK_FREEZE_SUBPATH = (
    ".local_freezes"
    "/BRODY_ENRICHED_EDUCATION_PACK_V1_FREEZE_20260617_124000"
)

# Résolution : apps/obsidia_api/ → apps/ → <project_root>/
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_PACK_FREEZE_PATH: Path = _PROJECT_ROOT / _PACK_FREEZE_SUBPATH

# ── Clé d'injection ───────────────────────────────────────────────────────
INJECT_KEY = "education_pack_v1_readonly_context"

# ── Boundary — toutes les valeurs ci-dessous sont HARDCODÉES et IMMUABLES ─
_EDUCATION_BOUNDARY: dict[str, Any] = {
    "readonly": True,
    "advisory_only": True,
    "context_signal_only": True,
    "memory_write": False,
    "graphiti_write": False,
    "neo4j_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "emits_act": False,
    "emits_verdict": False,
    "decision_authority": "KX108_ONLY",
    "authority": "NONE",
    "network": False,
    "fetch": False,
    "crawl": False,
    "mcp_bridge": False,
    "path_compute": False,
    "cache": "NO_CACHE",
}

# ── Clés d'action interdites — leur présence dans le packet bloque toujours ─
# Ces clés ne sont jamais des sentinelles readonly : elles signalent une
# tentative d'autorisation ou d'action souveraine.
_FORBIDDEN_ACTION_KEYS = frozenset([
    "decision",
    "verdict",
    "act",
    "allow",
    "approve",
    "execute",
])

# ── Sentinelles readonly — autorisées uniquement si valeur sûre ──────────
# Si la clé est présente avec une valeur hors de cette liste, on bloque.
_SAFE_SENTINEL_VALUES: dict[str, list] = {
    "decision_authority": ["KX108_ONLY"],
    "authority":          ["NONE"],
    "memory_write":       [False],
    "graphiti_write":     [False],
    "neo4j_write":        [False],
    "kernel_mutation":    [False, "NONE", None],
    "x108_mutation":      [False, "NONE", None],
    "emits_act":          [False],
    "emits_verdict":      [False],
    "network":            [False],
    "fetch":              [False],
    "crawl":              [False],
    "mcp_bridge":         [False],
    "path_compute":       [False],
}

# Rétrocompatibilité : tests existants importent _FORBIDDEN_INJECT_KEYS
_FORBIDDEN_INJECT_KEYS = _FORBIDDEN_ACTION_KEYS

# ── Sections connues du Pack V1 ───────────────────────────────────────────
_PACK_SECTIONS = [
    "BRODY_V1_CANONICAL_CORE.md",
    "BRODY_V1_PROJECT_STORYLINE.md",
    "BRODY_V1_MACHINATION_OBSIDIA_X108.md",
    "BRODY_V1_REAL_DOMAINS.md",
    "BRODY_V1_RND_CONTEXTUAL_MEMORY.md",
    "BRODY_V1_DEFERRED_AND_QUARANTINED_RND.md",
    "BRODY_V1_FORBIDDEN_BELIEFS.md",
    "BRODY_V1_EDUCATION_MODULES.md",
]

_DEFERRED_FILE = "BRODY_V1_DEFERRED_AND_QUARANTINED_RND.md"
_RAGNAROK_REF = "sigma/contracts.broken-ragnarok.py"


def _read_json_safe(path: Path) -> dict[str, Any] | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _check_section_presence() -> dict[str, bool]:
    result = {}
    for fname in _PACK_SECTIONS:
        result[fname] = (_PACK_FREEZE_PATH / fname).exists()
    return result


def build_brody_education_pack_v1_readonly_context() -> dict[str, Any]:
    """
    Lit les métadonnées du Pack V1 depuis le freeze local.
    Retourne un dict structuré — jamais de contenu brut massif.
    Ne lève jamais d'exception fatale.
    """
    if not _PACK_FREEZE_PATH.exists():
        return {
            "status": "PACK_MISSING",
            "freeze_path": str(_PACK_FREEZE_PATH),
            "education_boundary": _EDUCATION_BOUNDARY,
            "inject_key": INJECT_KEY,
            "pack_version": "V1",
            "canonical_core_available": False,
            "rnd_context_available": False,
            "deferred_quarantine_available": False,
            "forbidden_beliefs_available": False,
            "education_modules_available": False,
            "deferred_policy": "QUARANTINE_NOT_INJECTED",
            "ragnarok_policy": "EXCLUDE_ABSOLUTE",
        }

    # Lire les verdicts JSON
    pack_verdict = _read_json_safe(
        _PACK_FREEZE_PATH / "BRODY_ENRICHED_EDUCATION_PACK_V1_VERDICT.json"
    )
    gate = _read_json_safe(_PACK_FREEZE_PATH / "BRODY_V1_ENTRY_GATE.json")
    dryrun = _read_json_safe(
        _PACK_FREEZE_PATH / "BRODY_ENRICHED_EDUCATION_PACK_V1_DRY_RUN_VERDICT.json"
    )
    traceability = _read_json_safe(
        _PACK_FREEZE_PATH / "BRODY_V1_SOURCE_TRACEABILITY.json"
    )

    if pack_verdict is None or gate is None:
        return {
            "status": "PACK_INVALID",
            "freeze_path": str(_PACK_FREEZE_PATH),
            "education_boundary": _EDUCATION_BOUNDARY,
            "inject_key": INJECT_KEY,
            "pack_version": "V1",
            "error": "Verdict ou gate JSON invalide ou manquant",
        }

    sections = _check_section_presence()
    available_sections = [f for f, present in sections.items() if present]

    return {
        "status": "PACK_READY_READONLY",
        "inject_key": INJECT_KEY,
        "pack_version": "V1",
        "pack_id": pack_verdict.get("verdict_id", "BRODY_ENRICHED_EDUCATION_PACK_V1_VERDICT"),
        "pack_verdict": pack_verdict.get("verdict", "UNKNOWN"),
        "pack_commit": pack_verdict.get("head_commit", "783e664"),
        "freeze_path": _PACK_FREEZE_SUBPATH,

        # Disponibilité des sections clés
        "canonical_core_available": sections.get("BRODY_V1_CANONICAL_CORE.md", False),
        "rnd_context_available": sections.get("BRODY_V1_RND_CONTEXTUAL_MEMORY.md", False),
        "deferred_quarantine_available": sections.get(_DEFERRED_FILE, False),
        "forbidden_beliefs_available": sections.get("BRODY_V1_FORBIDDEN_BELIEFS.md", False),
        "education_modules_available": sections.get("BRODY_V1_EDUCATION_MODULES.md", False),
        "available_sections": available_sections,

        # Statuts des audits
        "manifest_status": "MANIFEST_SHA256_PRESENT" if (_PACK_FREEZE_PATH / "MANIFEST_SHA256.json").exists() else "MANIFEST_ABSENT",
        "dry_run_status": dryrun.get("verdict", "UNKNOWN") if dryrun else "DRYRUN_VERDICT_MISSING",
        "entry_gate_status": gate.get("gate_decision", "UNKNOWN"),
        "source_traceability_status": "PRESENT" if traceability else "ABSENT",

        # Politiques de sécurité
        "deferred_policy": "QUARANTINE_NOT_INJECTED",
        "ragnarok_policy": "EXCLUDE_ABSOLUTE",
        "ragnarok_ref": _RAGNAROK_REF,
        "ragnarok_note": (
            "sigma/contracts.broken-ragnarok.py est EXCLUDE_ABSOLUTE. "
            "Ne jamais citer comme exemple opérationnel."
        ),

        # Boundary immuable
        "education_boundary": _EDUCATION_BOUNDARY,
    }


def _check_packet_guard(packet: dict[str, Any]) -> str | None:
    """
    Retourne le motif de blocage si le packet contient une violation, None sinon.

    Niveau 1 — clés d'action interdites : leur simple présence bloque.
    Niveau 2 — sentinelles readonly : bloque uniquement si la valeur est unsafe.
    """
    for key in _FORBIDDEN_ACTION_KEYS:
        if key in packet:
            return f"Clé d'action interdite '{key}' présente dans le packet"

    for key, safe_values in _SAFE_SENTINEL_VALUES.items():
        if key in packet and packet[key] not in safe_values:
            return (
                f"Sentinelle '{key}' présente avec valeur unsafe "
                f"'{packet[key]}' (valeurs sûres: {safe_values})"
            )

    return None


def inject_education_pack_v1_into_runtime_packet(
    packet: dict[str, Any],
) -> dict[str, Any]:
    """
    Injecte education_pack_v1_readonly_context dans un packet runtime Brody.
    Guard deux niveaux : action keys + sentinel value check.
    Ne lève jamais d'exception fatale (fallback sur erreur).
    """
    block_reason = _check_packet_guard(packet)
    if block_reason is not None:
        packet[INJECT_KEY] = {
            "status": "PACK_INJECT_BLOCKED",
            "reason": block_reason,
            "education_boundary": _EDUCATION_BOUNDARY,
            "inject_key": INJECT_KEY,
        }
        return packet

    try:
        packet[INJECT_KEY] = build_brody_education_pack_v1_readonly_context()
    except Exception as exc:
        packet[INJECT_KEY] = {
            "status": "PACK_INJECT_ERROR",
            "error": type(exc).__name__,
            "education_boundary": _EDUCATION_BOUNDARY,
            "inject_key": INJECT_KEY,
        }
    return packet
