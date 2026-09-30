# runtime_wiring/source_runtime/capability_path_router.py
# P36 — Global Capability Path Router.
# Classe une query → intents → capabilities → chemins runtime candidats.
# Sélectionne le meilleur chemin parmi les candidats.
# KX108_ONLY. No ACT. No write. No execution. readonly=True.
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from runtime_wiring.source_runtime.capability_taxonomy import (
    CAPABILITY_TAXONOMY,
    get_capability,
)

# ── Mots-clés d'intent par capability ────────────────────────────────────────

_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "ACTION_REQUEST": [
        "envoie", "envoyer", "send", "mail", "email", "courriel",
        "modifie", "modifier", "edit", "delete", "supprime", "supprimer",
        "lance", "lancer", "run", "execute", "exécute", "exécuter",
        "écris", "écrire", "write", "push", "commit", "déploie", "déployer",
        "poste", "poster", "post", "publie", "publier", "publish",
        "crée", "créer", "create", "insert", "update", "mets à jour",
        "ouvre", "ouvrir", "ferme", "fermer", "démarre", "démarrer",
        "connecte", "connecter", "appelle", "appeler", "call",
    ],
    "IR_ALPHABET": [
        "ir alphabet", "alphabet ir", "alphabet reverse", "ir reverse",
        "intermediate representation", "représentation intermédiaire",
        "value state read write", "12 tokens", "ir spec", "l2 ir",
        "ir mapping", "ir schema",
    ],
    "REVERSE_OS_INTERLANGUAGE": [
        "reverse os interlanguage", "interlanguage canon", "réciproque miroir",
        "reciproque miroir", "twin_call", "twin call", "scf réciproque",
        "scf reciproque", "inversion path", "translation layer",
        "os trad interlanguage", "langage universel symbolique",
        "reverse_os_interlanguage_canon", "canon v1",
    ],
    "OS_TRAD": [
        "os trad", "reverse os", "reverse", "ssr", "mmonde",
        "traduction", "translation", "traducteur",
        "pipeline cognitif", "contexte packet", "context packet",
        "structure cognitive", "double cerveau", "jarvis",
    ],
    "AGENT_TREE": [
        "34 arbres", "34arbres", "arbre", "arbres", "tree",
        "52 agents", "agents 52", "agent", "tensor", "shazam",
        "hexaflux", "bdf", "ssr agent", "registry agents",
    ],
    "LAW_PROTOCOL": [
        "loi", "lois", "law", "laws", "protocole", "protocoles",
        "protocol", "non décision", "non decision", "non_decision",
        "boundary", "invariant", "constitution", "guard", "guards",
        "non action", "non_action",
    ],
    "RSSI_SECURITY": [
        "rssi", "sécurité", "security", "securite", "risque", "risk",
        "menace", "threat", "cyber", "cybersécurité", "cybersecurity",
        "présentation sécurité", "security presentation",
    ],
    "COMPLIANCE_AUDIT": [
        "audit", "conformité", "compliance", "rgpd", "gdpr",
        "données personnelles", "data protection", "vie privée",
        "privacy", "dpo", "iso 27001", "gouvernance données",
        "data governance",
    ],
    "MEMORY_CONTEXT": [
        "mémoire", "memory", "graphe mémoire",
        "réintégration", "reintegration", "cognition", "brody mémoire",
        "brody memory",
    ],
    "NARRATIVE_NPL": [
        "npl", "narrative", "provenance", "historique", "history",
        "trace", "origine", "origin", "contexte narratif",
        "narrative layer", "narrative provenance",
    ],
    # P44 — 5 gaps MUST_BIND_NEXT branchés
    "ATLAS": [
        "atlas", "cartographie", "carte atlas", "corpus map", "component map",
        "atlas map", "atlas obsidia", "arbre atlas", "module atlas",
        "composant atlas", "atlas component",
    ],
    "EXTERNAL_SIGNALS": [
        "timeverse", "external signals", "signal temporel", "temporal signal",
        "c459", "signaux temporels", "temps externe", "signal externe",
        "chronologie externe", "calendar signal", "timeverse signal",
    ],
    "BRODY_CHAT": [
        "brody chat", "true voice", "final answer", "brody réponse",
        "brody response", "réponse brody", "brody answer", "brody entrypoint",
    ],
    "OS_TRAD_ROUTE": [
        "os trad route", "os-trad route", "ir candidate", "os reverse project",
        "api os-trad", "os trad translate", "translate endpoint", "ir route",
        "os reverse route", "os-trad api", "api ir",
    ],
}

# ── Mapping intent → capabilities candidates ──────────────────────────────────

_INTENT_TO_CAPABILITIES: Dict[str, List[str]] = {
    "ACTION_REQUEST": ["ACTION_REQUEST_BLOCKED"],
    "IR_ALPHABET": ["IR_ALPHABET_MAPPING", "REVERSE_OS_INTERLANGUAGE"],
    "REVERSE_OS_INTERLANGUAGE": ["REVERSE_OS_INTERLANGUAGE", "IR_ALPHABET_MAPPING"],
    "OS_TRAD": ["OS_TRAD_TRANSLATION", "AGENT_TREE_LOOKUP"],
    "AGENT_TREE": ["AGENT_TREE_LOOKUP", "OS_TRAD_TRANSLATION"],
    "LAW_PROTOCOL": ["LAW_PROTOCOL_LOOKUP", "OS_TRAD_TRANSLATION"],
    "RSSI_SECURITY": ["RSSI_SECURITY_CONTEXT", "PROOF_AUDIT_CONTEXT"],
    "COMPLIANCE_AUDIT": ["PROOF_AUDIT_CONTEXT", "RSSI_SECURITY_CONTEXT"],
    "MEMORY_CONTEXT": ["MEMORY_REINTEGRATION_CONTEXT"],
    "NARRATIVE_NPL": ["NPL_NARRATIVE_PROVENANCE", "PROVENANCE_TRACE"],
    # P44
    "ATLAS": ["ATLAS_CONTEXT_LOOKUP"],
    "EXTERNAL_SIGNALS": ["EXTERNAL_SIGNALS_CONTEXT"],
    "BRODY_CHAT": ["BRODY_CHAT_ENTRYPOINT"],
    "OS_TRAD_ROUTE": ["OS_TRAD_ROUTE_CONTEXT", "OS_TRAD_TRANSLATION"],
}

# ── Scoring des chemins ───────────────────────────────────────────────────────

_CAPABILITY_SCORE: Dict[str, float] = {
    "ACTION_REQUEST_BLOCKED": 1.0,   # Priorité absolue si détecté
    "IR_ALPHABET_MAPPING": 0.95,
    "REVERSE_OS_INTERLANGUAGE": 0.93,
    "AGENT_TREE_LOOKUP": 0.88,
    "LAW_PROTOCOL_LOOKUP": 0.85,
    "OS_TRAD_ROUTE_CONTEXT": 0.84,   # P44: routes opérationnelles spécifiques
    "OS_TRAD_TRANSLATION": 0.82,
    "RSSI_SECURITY_CONTEXT": 0.80,
    "BRODY_CHAT_ENTRYPOINT": 0.78,   # P44: entrypoint primaire
    "PROOF_AUDIT_CONTEXT": 0.77,
    "MEMORY_REINTEGRATION_CONTEXT": 0.75,
    "ATLAS_CONTEXT_LOOKUP": 0.71,    # P44: 11k entrées, advisory
    "NPL_NARRATIVE_PROVENANCE": 0.70,
    "EXTERNAL_SIGNALS_CONTEXT": 0.67, # P44: signaux temporels advisory
    "PROVENANCE_TRACE": 0.65,
    "SOURCE_CONTEXT": 0.50,
    "WORKBENCH_PREVIEW": 0.45,
    "OS4_ENGINE_STATUS": 0.40,
    "ANSWER_ONLY": 0.20,
}

# ── Chemin statique par capability ───────────────────────────────────────────

_CAPABILITY_PATH_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "ACTION_REQUEST_BLOCKED": {
        "modules": [],
        "adapters": [],
        "routes": [],
        "source_families": [],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "BLOCK_OR_HOLD_CONTEXT_ONLY",
        "reason": "Action requested but runtime is READONLY — KX108_ONLY boundary blocks all mutations.",
    },
    "IR_ALPHABET_MAPPING": {
        "modules": ["reverse_os_interlanguage_index", "source_runtime_query"],
        "adapters": ["reverse_os_interlanguage_to_context_packet"],
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "source_families": ["OS_TRAD_REVERSE_OS"],
        "source_subfamilies": ["REVERSE_OS_INTERLANGUAGE_CANON_V1"],
        "evidence_packs": ["REVERSE_OS_INTERLANGUAGE_CANON_V1"],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "IR Alphabet L2 mapping — REVERSE_OS_INTERLANGUAGE_CANON_V1 contient les 12 tokens IR formalisés.",
    },
    "REVERSE_OS_INTERLANGUAGE": {
        "modules": [
            "reverse_os_interlanguage_index",
            "brody_source_context_bridge",
            "source_context_hydrator",
        ],
        "adapters": ["reverse_os_interlanguage_to_context_packet"],
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "source_families": ["OS_TRAD_REVERSE_OS"],
        "source_subfamilies": ["REVERSE_OS_INTERLANGUAGE_CANON_V1"],
        "evidence_packs": ["REVERSE_OS_INTERLANGUAGE_CANON_V1"],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "Canon Reverse OS Interlanguage V1 — réciproque miroir, TWIN_CALL, SCF Réciproque.",
    },
    "OS_TRAD_TRANSLATION": {
        "modules": ["os_trad_reverse_index", "source_runtime_query", "brody_source_context_bridge"],
        "adapters": ["os_trad_reverse_to_context_packet"],
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "source_families": ["OS_TRAD_REVERSE_OS"],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "OS Trad Reverse OS — famille corpus traduction structurée.",
    },
    "AGENT_TREE_LOOKUP": {
        "modules": ["os_trad_reverse_index", "source_runtime_query"],
        "adapters": ["os_trad_reverse_to_context_packet"],
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "source_families": ["OS_TRAD_REVERSE_OS"],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "Arbres 34 / Agents 52 — AGENTS_TREES_LAYER du corpus OS_TRAD_REVERSE_OS.",
    },
    "LAW_PROTOCOL_LOOKUP": {
        "modules": ["os_trad_reverse_index", "source_runtime_query"],
        "adapters": ["os_trad_reverse_to_context_packet"],
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "source_families": ["OS_TRAD_REVERSE_OS"],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "Lois et protocoles Obsidiens — LAWS_PROTOCOLS_LAYER, boundary advisory uniquement.",
    },
    "RSSI_SECURITY_CONTEXT": {
        "modules": ["source_runtime_query", "brody_source_context_bridge"],
        "adapters": ["rssi_security_to_context_packet", "rssi_rgpd_to_context_packet"],
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "source_families": ["RSSI_SECURITY_PRESENTATION", "RSSI_RGPD"],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "Contexte sécurité RSSI — familles RSSI disponibles.",
    },
    "PROOF_AUDIT_CONTEXT": {
        "modules": ["source_runtime_query", "brody_source_context_bridge"],
        "adapters": [
            "rssi_rgpd_to_context_packet",
            "compliance_to_context_packet",
            "rssi_security_to_context_packet",
        ],
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "source_families": ["RSSI_RGPD", "COMPLIANCE_DATA_GOVERNANCE", "RSSI_SECURITY_PRESENTATION"],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "Audit conformité / compliance — RSSI_RGPD + COMPLIANCE_DATA_GOVERNANCE.",
    },
    "MEMORY_REINTEGRATION_CONTEXT": {
        "modules": ["source_runtime_query", "brody_source_context_bridge"],
        "adapters": ["cognitive_to_context_packet", "npl_to_context_packet"],
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "source_families": ["COGNITIVE_REINTEGRATION", "NARRATIVE_PROVENANCE_LAYER"],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "Réintégration mémoire Brody — COGNITIVE_REINTEGRATION advisory.",
    },
    "NPL_NARRATIVE_PROVENANCE": {
        "modules": ["source_runtime_query", "brody_source_context_bridge"],
        "adapters": ["npl_to_context_packet"],
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "source_families": ["NARRATIVE_PROVENANCE_LAYER"],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "Narrative Provenance Layer — trace narrative et provenance.",
    },
    "PROVENANCE_TRACE": {
        "modules": ["source_runtime_query", "brody_source_context_bridge"],
        "adapters": ["npl_to_context_packet", "cognitive_to_context_packet"],
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "source_families": ["NARRATIVE_PROVENANCE_LAYER", "COGNITIVE_REINTEGRATION"],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "Trace de provenance — NPL + Cognitive advisory.",
    },
    "SOURCE_CONTEXT": {
        "modules": [
            "source_runtime_query",
            "brody_source_context_bridge",
            "source_context_hydrator",
        ],
        "adapters": ["cognitive_to_context_packet"],
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "source_families": ["COGNITIVE_REINTEGRATION"],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "Contexte source générique — fallback COGNITIVE_REINTEGRATION.",
    },
    # P44 — 5 gaps MUST_BIND_NEXT
    "ATLAS_CONTEXT_LOOKUP": {
        "modules": ["source_runtime_query", "brody_source_context_bridge"],
        "adapters": ["atlas_to_context_packet"],
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "source_families": ["ATLAS"],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "ATLAS corpus lookup — 11 263 entrées cartographiques, advisory readonly.",
    },
    "EXTERNAL_SIGNALS_CONTEXT": {
        "modules": ["source_runtime_query", "brody_source_context_bridge"],
        "adapters": ["external_signals_to_context_packet"],
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "source_families": ["EXTERNAL_SIGNALS"],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "Signaux temporels TimeVerse / External Signals — advisory readonly, aucune prédiction comme action.",
    },
    "BRODY_CHAT_ENTRYPOINT": {
        "modules": ["brody_source_context_bridge", "brody_real_response_pipeline"],
        "adapters": [],
        "routes": ["/api/brody/chat"],
        "source_families": ["COGNITIVE_REINTEGRATION"],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "Entrypoint Brody Chat /api/brody/chat — pipeline réponse V1.4.12A, context routing readonly.",
    },
    "OS_TRAD_ROUTE_CONTEXT": {
        "modules": ["os_trad_ir_reverse", "os_trad_reverse_index", "source_runtime_query"],
        "adapters": ["os_trad_reverse_to_context_packet", "reverse_os_interlanguage_to_context_packet"],
        "routes": [
            "/api/runtime-wiring/os-trad/api/os-trad/translate",
            "/api/runtime-wiring/os-trad/api/ir/candidate",
            "/api/runtime-wiring/os-trad/api/os-reverse/project",
        ],
        "source_families": ["OS_TRAD_REVERSE_OS"],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "Routes OS Trad IR Reverse opérationnelles — translate, ir/candidate, os-reverse/project. Readonly.",
    },
    "ANSWER_ONLY": {
        "modules": [],
        "adapters": [],
        "routes": [],
        "source_families": [],
        "source_subfamilies": [],
        "evidence_packs": [],
        "x108_decision": "ALLOW_CONTEXT_ONLY",
        "reason": "Réponse interne Brody sans hydratation source pack.",
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_intents(query: str) -> List[str]:
    """Détecte les intents présents dans la query (multi-intent possible)."""
    q = query.lower()
    detected: List[str] = []
    # ACTION_REQUEST prioritaire
    for kw in _INTENT_KEYWORDS["ACTION_REQUEST"]:
        if kw in q:
            detected.append("ACTION_REQUEST")
            break
    for intent, keywords in _INTENT_KEYWORDS.items():
        if intent == "ACTION_REQUEST":
            continue
        for kw in keywords:
            if kw in q:
                detected.append(intent)
                break
    return detected


def _intents_to_required_capabilities(intents: List[str]) -> List[str]:
    """Déduit les capabilities requises depuis les intents (sans doublons)."""
    seen: set = set()
    caps: List[str] = []
    for intent in intents:
        for cap in _INTENT_TO_CAPABILITIES.get(intent, []):
            if cap not in seen:
                seen.add(cap)
                caps.append(cap)
    if not caps:
        caps = ["SOURCE_CONTEXT"]
    return caps


def _build_path_for_capability(
    capability_id: str,
    query: str,
    path_idx: int,
    available_families: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Construit un chemin candidat pour une capability donnée."""
    cap = CAPABILITY_TAXONOMY.get(capability_id, {})
    template = _CAPABILITY_PATH_TEMPLATES.get(capability_id, {})
    base_score = _CAPABILITY_SCORE.get(capability_id, 0.3)

    families = template.get("source_families", [])
    # Pénalité si famille non disponible
    score = base_score
    if available_families is not None and families:
        available_count = sum(1 for f in families if f in available_families)
        if available_count == 0:
            score *= 0.4
        elif available_count < len(families):
            score *= 0.8

    path_id = f"path_{path_idx:02d}_{capability_id.lower()}"
    digest = hashlib.sha256(f"{path_id}:{query}".encode()).hexdigest()[:8]

    return {
        "path_id": f"{path_id}_{digest}",
        "capability_chain": [capability_id],
        "modules": list(template.get("modules", [])),
        "adapters": list(template.get("adapters", [])),
        "routes": list(template.get("routes", [])),
        "source_families": list(families),
        "source_subfamilies": list(template.get("source_subfamilies", [])),
        "evidence_packs": list(template.get("evidence_packs", [])),
        "selected_files": list(
            cap.get("candidate_source_families", [])
        ),
        "score": round(score, 3),
        "reason": template.get("reason", ""),
        "x108_decision": template.get("x108_decision", "ALLOW_CONTEXT_ONLY"),
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        # P37 — enrichi par capability_inventory_linker si inventaire disponible
        "selected_functions": [],
        "selected_classes": [],
        "selected_routes": [],
        "selected_tests": [],
        "selected_docs": [],
        "inventory_linked": False,
        "coverage_status": "PENDING_INVENTORY_LINK",
    }


# ── Fonction principale ───────────────────────────────────────────────────────

def route_capability_path(
    query: str,
    registry_entries: Optional[List[Any]] = None,
    max_paths: int = 5,
    available_families: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Route une query vers les meilleurs chemins de capacité runtime.

    Args:
        query: La requête utilisateur (texte libre).
        registry_entries: Entrées registry optionnelles (non lues ici).
        max_paths: Nombre max de chemins candidats à retourner.
        available_families: Familles source disponibles localement.

    Returns:
        Dict contenant detected_intents, required_capabilities,
        ranked_runtime_paths, selected_path, rejected_paths.
        Toujours readonly=True, no_act=True, decision_authority=KX108_ONLY.
    """
    detected_intents = _detect_intents(query)
    required_capabilities = _intents_to_required_capabilities(detected_intents)

    # Déduplique et garde les capabilities valides
    seen: set = set()
    unique_caps: List[str] = []
    for cap in required_capabilities:
        if cap not in seen and cap in CAPABILITY_TAXONOMY:
            seen.add(cap)
            unique_caps.append(cap)

    # Construit les chemins candidats
    all_paths: List[Dict[str, Any]] = []
    for idx, cap_id in enumerate(unique_caps):
        path = _build_path_for_capability(cap_id, query, idx, available_families)
        all_paths.append(path)

    # Trie par score décroissant
    all_paths.sort(key=lambda p: p["score"], reverse=True)

    ranked = all_paths[:max_paths]
    rejected = all_paths[max_paths:]

    selected_path = ranked[0] if ranked else _build_path_for_capability(
        "ANSWER_ONLY", query, 0, available_families
    )

    return {
        "query": query,
        "detected_intents": detected_intents,
        "required_capabilities": unique_caps,
        "ranked_runtime_paths": ranked,
        "selected_path": selected_path,
        "rejected_paths": rejected,
        "readonly": True,
        "no_act": True,
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
    }
