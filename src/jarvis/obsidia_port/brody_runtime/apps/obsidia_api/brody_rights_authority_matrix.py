"""
Brody Rights / Authority / Capability Matrix
============================================
Fusionne les sources canoniques suivantes :
  - BRODY_SESSION_CHECKPOINT_FINAL (2026-05-13)
  - BRODY_REAL_ARCHITECTURE_MAP_READONLY (2026-05-13)
  - CURRENT_BRODY_HUMAN_COMMAND_PACKET_READONLY.txt
  - CURRENT_BRODY_API_BRIDGE_RUNTIME_ACTIVATION_GATE_READONLY.txt
  - T13_T34_SIGNAL_DISCOVERY_READONLY (2026-05-14)
  - WRITABLE_MEMORY_ACTIVATION_CHECKLIST (2026-05-14)
  - X108_boundary___kernel_decision_authority.json

Principe fondamental :
  Répondre n'est pas décider.
  Analyser n'est pas décider.
  Préparer un ContextPacket n'est pas décider.
  Préparer un IR candidate n'est pas décider.
  Préparer une mémoire candidate n'est pas écrire mémoire.
  Proposer une priorisation advisory n'est pas ACT.
  Classifier une intention n'est pas exécuter.

  Brody peut faire tout cela.
  Brody ne peut pas décider, autoriser ACT, écrire mémoire automatiquement, bypasser X108.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

# ── Category constants ─────────────────────────────────────────────────────────
PURE_RESPONSE             = "PURE_RESPONSE"
CONTEXT_ANALYSIS          = "CONTEXT_ANALYSIS"
CAPABILITY_SCOPE          = "CAPABILITY_SCOPE"
STRUCTURAL_PREPARATION    = "STRUCTURAL_PREPARATION"
MEMORY_CANDIDATE          = "MEMORY_CANDIDATE"
OPERATOR_COMMAND_PROPOSAL = "OPERATOR_COMMAND_PROPOSAL"
EXTERNAL_ACCESS_REQUEST   = "EXTERNAL_ACCESS_REQUEST"
ACTION_OR_ACT_REQUEST     = "ACTION_OR_ACT_REQUEST"
MEMORY_WRITE_REQUEST      = "MEMORY_WRITE_REQUEST"
TREE_SIGNAL_REQUEST       = "TREE_SIGNAL_REQUEST"
PRIORITY_ADVISORY         = "PRIORITY_ADVISORY"

# ── Tree policy (source: T13_T34_SIGNAL_DISCOVERY_READONLY_20260514) ─────────
_TREE_POLICY: dict[str, Any] = {
    "safe_trees": ["T13", "T14", "T15", "T16", "T17", "T18", "T19",
                   "T23", "T25", "T26", "T27", "T28", "T29"],
    "safe_count": 13,
    "safe_docs": 117,
    "blocked_action": ["T20", "T21", "T22"],
    "blocked_action_reason": "BLOCKED_ACTION_TRIGGER — V_ACTION_TRANSFORMATION",
    "blocked_memory": ["T24"],
    "blocked_memory_reason": "BLOCKED_DIRECT_MEMORY_WRITE — T24 Arbre de la Memoire",
    "blocked_agi": ["T30", "T31", "T32", "T33", "T34"],
    "blocked_agi_reason": "BLOCKED_AGI_LAYER — VIII_OBSIDIA_AGI",
    "total_trees": 22,
    "blocked_total": 9,
    "blocked_docs": 81,
    "signal_method": "PATH_SLUG",
    "source": "T13_T34_SIGNAL_DISCOVERY_READONLY_20260514_025500",
}

# ── Detection patterns — ordered, first match wins ────────────────────────────
# Normalization: NFKD + strip combining chars + lowercase
def _norm(s: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", s.lower())
        if not unicodedata.combining(ch)
    )


# Typo-tolerant normalization for intent classification.
# Handles oral/freestyle inputs before pattern matching.
_TYPO_FIXES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bue\s+peut\s+tu\b"),       "que peux tu"),
    (re.compile(r"\bque\s+peut\s+tu\b"),       "que peux tu"),
    (re.compile(r"\btu\s+peut\b"),             "tu peux"),
    (re.compile(r"\btu\s+peux\s+faire\s+quoi\b"), "que peux tu faire"),
    (re.compile(r"\btu\s+peut\s+faire\s+quoi\b"), "que peux tu faire"),
    (re.compile(r"\btu\s+peut\s+pas\b"),       "tu ne peux pas"),
    (re.compile(r"\bquelle\s+sont\b"),         "quelles sont"),
    (re.compile(r"\bce\s+que\s+tu\s+peut\b"),  "ce que tu peux"),
    (re.compile(r"\bdecision\b"),              "decision"),
    (re.compile(r"\bdecider\b"),               "decider"),
    (re.compile(r"\blimite\b"),                "limite"),
]


def _normalize_intent(text: str) -> str:
    """Apply NFKD normalization + typo correction for oral/freestyle inputs."""
    s = _norm(text)
    for pattern, replacement in _TYPO_FIXES:
        s = pattern.sub(replacement, s)
    return s


_PATTERNS: list[tuple[str, list[str]]] = [
    # 1. Explicit Graphiti / Neo4j write (most specific — check first)
    (MEMORY_WRITE_REQUEST, [
        r"[eé]cris dans graphiti", r"[eé]crire dans graphiti",
        r"[eé]cris dans neo4j", r"[eé]crire dans neo4j",
        r"write to graphiti", r"write to neo4j",
        r"[eé]cris en m[eé]moire\b", r"write.?to.?memory",
        r"import.?graphiti", r"memory.?write.?now",
        r"[eé]cris directement", r"write directly",
        r"ajoute.?(directement|maintenant).?(en|dans|a).?m[eé]moire",
    ]),
    # 2. ACT / action execution
    (ACTION_OR_ACT_REQUEST, [
        r"autoris[e]?\s+act\b", r"authoriz[e]?\s+act",
        r"[eé]mets?\s+act\b", r"emit\s+act",
        r"d[eé]clenche\s+act\b",
        r"lance.?paiement", r"connecte.?wallet",
        r"\btrade\b", r"sign[e]?.?transaction",
        r"bypass.?[xk]x?108",
        r"d[eé]cide.?pour.?moi", r"prends.?la.?d[eé]cision",
        r"\bexecut[e]?\s+action\b", r"\bdecide\s+now\b",
    ]),
    # 3. Tree signal requests
    (TREE_SIGNAL_REQUEST, [
        r"quels?\s+arbres?", r"arbres?\s+activ[eé]s?",
        r"utilise.?les.?arbres?", r"utilise.?les.?34.?arbres?",
        r"arbres?\s+disponibles?", r"liste.{0,8}arbres?",
        r"\bT1[3-9]\b", r"\bT2[0-9]\b", r"\bT3[0-4]\b",
        r"arbre\s+de\s+l.action", r"arbre\s+de\s+la\s+m[eé]moire",
        r"curriculum.?tree", r"34\s+arbres?",
    ]),
    # 4. External fetch / API call requests
    (EXTERNAL_ACCESS_REQUEST, [
        r"va\s+chercher\b", r"fetch.?url", r"\bscrape\b",
        r"appelle.{0,10}api", r"call\s+api",
        r"get.?from.?url", r"http.?get\b",
        r"r[eé]cup[eè]re.?depuis", r"t[eé]l[eé]charg",
    ]),
    # 5. Priority advisory ("qu'est-ce qui est le plus important")
    (PRIORITY_ADVISORY, [
        r"plus.?important[e]?\s+maintenant",
        r"le.?plus.?important.?[aà].?pr[eé]parer",
        r"qu.?est.?ce.?qui.?est.?prioritaire",
        r"quoi.?pr[eé]parer.?d.?abord",
        r"que.?faire.?d.?abord",
        r"quoi.?faire.?en.?premier",
        r"que.?pr[eé]parer.?en.?premier",
        r"que.?dois.?je.?faire.?maintenant",
        r"toi.?.?qu.?est.?ce.?tu.?pense",
        r"tu.?pense.?que.?c.?est.?quoi.?le.?plus.?important",
        r"ordre.?de.?priorit[eé]",
        r"\bpriorit[eé]s\b",
    ]),
    # 6. Memory candidate preparation (prepare a candidate, not direct write)
    (MEMORY_CANDIDATE, [
        r"garde.?[cç]a\s+en\s+m[eé]moire",
        r"m[eé]morise.?[cç]a",
        r"pr[eé]pare.?une?\s+m[eé]moire\s+candidate",
        r"ajoute.?[cç]a.?en\s+candidat",
        r"candidat\s+m[eé]moire",
        r"save.?to.?memory.?candidate",
        r"cr[eé]e.?un?\s+candidat\s+m[eé]moire",
    ]),
    # 7. Operator command proposal
    (OPERATOR_COMMAND_PROPOSAL, [
        r"comment.?je.?lance\b", r"comment.?lancer\b",
        r"pr[eé]pare.?la\s+commande", r"pr[eé]pare.?un?\s+command.?packet",
        r"que\s+dois.?je\s+ex[eé]cuter", r"quelle\s+commande",
        r"how.?do.?i.?run\b", r"how.?to.?start\b",
        r"script.?[àa].?lancer", r"commande.?[àa].?ex[eé]cuter",
    ]),
    # 8. Structural preparation (ContextPacket, IR candidate, plan)
    (STRUCTURAL_PREPARATION, [
        r"pr[eé]pare.?un?\s+context.?packet",
        r"pr[eé]pare.?un?\s+ir.?candidate",
        r"pr[eé]pare.?un?\s+plan\b",
        r"pr[eé]pare.?un?\s+candidat\b",
        r"g[eé]n[eè]re.?un?\s+packet",
        r"cr[eé]e.?un?\s+packet\b",
        r"structure.?une?\s+r[eé]ponse",
        r"formule.?un?\s+candidat",
        r"prepare.?a.?context.?packet",
        r"prepare.?an?.?ir.?candidate",
        r"build.?a.?packet",
    ]),
    # 9. Capability / scope question — what Brody can or cannot do
    (CAPABILITY_SCOPE, [
        # Direct capability questions
        r"que\s+peux.?tu\s+faire",
        r"que\s+peut.?tu\s+faire",
        r"tu\s+peux\s+faire\s+quoi",
        r"ce\s+que\s+tu\s+peux\s+faire",
        r"peux.?tu\s+faire\s+ou\s+pas\s+faire",
        r"peut.?tu\s+faire\s+ou\s+pas\s+faire",
        r"faire\s+ou\s+pas\s+faire",
        r"faire\s+ou\s+ne\s+pas\s+faire",
        # Action/decision scope
        r"en\s+action\s+decision",
        r"en\s+action\s+d[eé]cision",
        r"action\s+et\s+d[eé]cision",
        r"d[eé]cision\s+et\s+action",
        r"droit\s+de\s+faire",
        r"qui\s+a\s+le\s+droit\s+de",
        r"qui\s+peut\s+faire\s+quoi",
        r"entre\s+brody.+(?:x.?108|humain|m[eé]moire)",
        r"(?:x.?108|humain|m[eé]moire).+entre\s+brody",
        # Limit / boundary queries with action context
        r"tes?.?\s+limite.?\s+(?:en\s+)?(?:action|d[eé]cision|act)",
        r"limite.?(?:en\s+)?(?:action|d[eé]cision|act)",
        r"ce\s+que\s+(?:tu|brody)\s+ne\s+peux?\s+pas",
        r"ce\s+que\s+(?:tu|brody)\s+(?:peux?|peut)\s+(?:et|ou)\s+(?:ne\s+peux?\s+pas|pas\s+faire)",
        # English patterns
        r"what\s+can\s+(?:you|brody)\s+do",
        r"what\s+(?:you|brody)\s+can\s+(?:or\s+cannot|and\s+cannot|and\s+can.?t)",
        r"can\s+(?:you|brody)\s+do\s+or\s+not\s+do",
        r"what\s+(?:are\s+)?(?:you|brody).?(?:r|s)?\s+(?:limit|capabilit|boundar)",
        r"what\s+(?:you|brody)\s+(?:can|cannot|can.?t)",
        r"(?:do\s+or\s+not\s+do|can\s+or\s+cannot)\s+(?:in\s+terms\s+of|for)\s+(?:action|decision)",
        r"in\s+terms\s+of\s+action\s+(?:and\s+)?decision",
        r"who\s+(?:has\s+the\s+)?(?:right|authority)\s+to\s+(?:do|act|decide)",
        r"between\s+brody.+(?:x.?108|human|memory)",
    ]),
    # 10. Context analysis / diagnostic
    (CONTEXT_ANALYSIS, [
        r"montre.?moi.?le\s+contexte",
        r"montre.?le\s+contexte",
        r"analyse.?[cç]a\b", r"analyse.?ce.?bug",
        r"tu.?comprends.?ma.?demande",
        r"tu.?comprends\b", r"tu.?vois\b", r"tu.?captes\b",
        r"quel.?est.?le\s+contexte",
        r"d[eé]cris.?le\s+contexte",
        r"quell?e?s?.?sont.?tes?.?limit",
        r"tes?.?capacit[eé]s",
        r"que.?peux.?tu.?faire",
        r"explique.?ce.?que.?tu.?vois",
        r"contexte.?actuel\b",
        r"show.?me.?the.?context",
        r"\bdiagnostic\b", r"\bd[eé]bug\b",
        r"qu.?est.?ce.?que.?tu.?es\b",
        r"qui.?es.?tu\b",
    ]),
    # 10. Catch-all: PURE_RESPONSE (greeting, general explanation, etc.)
    (PURE_RESPONSE, []),
]


def _detect_request_type(user_message: str) -> str:
    s = _normalize_intent(user_message)
    for request_type, patterns in _PATTERNS[:-1]:  # skip final catch-all
        if any(re.search(p, s) for p in patterns):
            return request_type
    return PURE_RESPONSE


# ── Capability rules per category ─────────────────────────────────────────────
_MATRIX: dict[str, dict[str, Any]] = {
    PURE_RESPONSE: {
        "brody_may": [
            "repondre_naturellement",
            "contextualiser",
            "structurer_la_reponse",
            "expliquer_le_systeme_obsidia",
            "decrire_son_perimetre",
        ],
        "brody_must_not": ["decider", "emettre_act", "ecrire_memoire"],
        "requires_human_operator": False,
        "requires_kx108_decision": False,
        "requires_memory_gate": False,
        "requires_api_bridge_gate": False,
        "response_mode": "FULL_ANSWER",
    },
    CAPABILITY_SCOPE: {
        "brody_may": [
            "repondre_naturellement",
            "expliquer_ce_que_brody_peut_faire",
            "expliquer_ce_que_brody_ne_peut_pas_faire",
            "expliquer_role_humain_operateur",
            "expliquer_role_kx108_decision_authority",
            "expliquer_role_memoire_candidate_only",
            "lister_capacites_et_limites",
            "expliquer_automation_snapshot",
            "expliquer_boundary_complet",
        ],
        "brody_must_not": [
            "decider",
            "emettre_act",
            "emettre_hold_block_allow_comme_verdict",
            "ecrire_memoire_automatiquement",
            "executer",
            "bypass_x108",
        ],
        "requires_human_operator": False,
        "requires_kx108_decision": False,
        "requires_memory_gate": False,
        "requires_api_bridge_gate": False,
        "response_mode": "CAPABILITY_SCOPE",
    },
    CONTEXT_ANALYSIS: {
        "brody_may": [
            "lire_graphiti_readonly",
            "lire_context_packet",
            "utiliser_response_md",
            "citer_sources_et_memoire",
            "diagnostic_consultatif",
            "expliquer_ses_capacites_et_limites",
            "reconnaitre_friction_et_proposer_diagnostic",
        ],
        "brody_must_not": ["modifier_memoire", "decider", "emettre_act"],
        "requires_human_operator": False,
        "requires_kx108_decision": False,
        "requires_memory_gate": False,
        "requires_api_bridge_gate": False,
        "response_mode": "CONTEXT_DIAGNOSTIC",
    },
    STRUCTURAL_PREPARATION: {
        "brody_may": [
            "produire_context_packet_candidat",
            "produire_ir_candidate",
            "produire_une_projection",
            "structurer_une_proposition",
            "formuler_un_plan_advisory",
        ],
        "brody_must_not": [
            "executer_le_packet",
            "ecrire_memoire_automatiquement",
            "emettre_act",
            "decider",
        ],
        "requires_human_operator": True,
        "requires_kx108_decision": False,
        "requires_memory_gate": False,
        "requires_api_bridge_gate": False,
        "response_mode": "FULL_ANSWER",
    },
    MEMORY_CANDIDATE: {
        "brody_may": [
            "preparer_candidate_memoire",
            "assigner_NEEDS_REVIEW",
            "expliquer_les_6_gates_obligatoires",
            "documenter_le_candidat",
        ],
        "brody_must_not": [
            "ecrire_graphiti_automatiquement",
            "ecrire_neo4j_automatiquement",
            "auto_promouvoir_candidat",
            "decider_de_l_ecriture",
        ],
        "requires_human_operator": True,
        "requires_kx108_decision": False,
        "requires_memory_gate": True,
        "requires_api_bridge_gate": False,
        "response_mode": "MEMORY_CANDIDATE",
    },
    OPERATOR_COMMAND_PROPOSAL: {
        "brody_may": [
            "preparer_human_command_packet",
            "classifier_readonly_git_mutation_external",
            "proposer_sequence_commandes",
            "expliquer_prerequis_et_gates",
        ],
        "brody_must_not": [
            "executer_a_la_place_de_l_humain",
            "lancer_commande_automatiquement",
            "git_mutation_sans_approbation_operateur",
        ],
        "requires_human_operator": True,
        "requires_kx108_decision": False,
        "requires_memory_gate": False,
        "requires_api_bridge_gate": False,
        "response_mode": "FULL_ANSWER",
    },
    EXTERNAL_ACCESS_REQUEST: {
        "brody_may": [
            "GET_only_si_allowlist_et_operator_loop",
            "preparer_dry_run_packet",
            "expliquer_les_conditions_d_activation",
        ],
        "brody_must_not": [
            "runtime_fetch_si_activation_gate_blocked",
            "POST_ou_mutation",
            "scrape_sans_autorisation_operateur",
            "acceder_URL_hors_allowlist",
        ],
        "requires_human_operator": True,
        "requires_kx108_decision": False,
        "requires_memory_gate": False,
        "requires_api_bridge_gate": True,
        "response_mode": "ACTION_BOUNDARY",
    },
    ACTION_OR_ACT_REQUEST: {
        "brody_may": [
            "expliquer_le_refus_clairement",
            "produire_action_candidate_pour_x108",
            "demander_validation_humaine",
            "documenter_dans_context_packet",
        ],
        "brody_must_not": [
            "emettre_act",
            "autoriser_act",
            "emettre_hold",
            "emettre_block",
            "executer_action_reelle",
            "bypass_x108",
        ],
        "requires_human_operator": True,
        "requires_kx108_decision": True,
        "requires_memory_gate": False,
        "requires_api_bridge_gate": False,
        "response_mode": "ACTION_BOUNDARY",
    },
    MEMORY_WRITE_REQUEST: {
        "brody_may": [
            "preparer_candidate_only",
            "expliquer_review_gate_6_conditions",
            "fournir_template_approbation_operateur",
        ],
        "brody_must_not": [
            "ecrire_graphiti_automatiquement",
            "ecrire_neo4j_automatiquement",
            "contourner_les_6_gates",
            "emettre_act",
        ],
        "requires_human_operator": True,
        "requires_kx108_decision": True,
        "requires_memory_gate": True,
        "requires_api_bridge_gate": False,
        "response_mode": "ACTION_BOUNDARY",
    },
    TREE_SIGNAL_REQUEST: {
        "brody_may": [
            "lire_arbres_safe_T13_T19_T23_T25_T29",
            "activer_signaux_contextuels_readonly",
            "citer_arbres_bloques_avec_raison",
            "expliquer_la_politique_arbre",
        ],
        "brody_must_not": [
            "declencher_T20_T22_comme_action_trigger",
            "ecrire_via_T24_memory_direct",
            "activer_T30_T34_AGI_layer",
        ],
        "requires_human_operator": False,
        "requires_kx108_decision": False,
        "requires_memory_gate": False,
        "requires_api_bridge_gate": False,
        "response_mode": "CONTEXT_DIAGNOSTIC",
    },
    PRIORITY_ADVISORY: {
        "brody_may": [
            "priorisation_consultative",
            "classement_chantiers_advisory",
            "analyse_etat_systeme",
            "proposer_sequence_advisory",
            "dire_je_ne_decide_pas_comme_boundary_pas_comme_reponse_principale",
        ],
        "brody_must_not": [
            "prendre_decision_finale",
            "emettre_act",
            "executer_une_action",
        ],
        "requires_human_operator": False,
        "requires_kx108_decision": False,
        "requires_memory_gate": False,
        "requires_api_bridge_gate": False,
        "response_mode": "ADVISORY_PRIORITY",
    },
}


# ── Public API ─────────────────────────────────────────────────────────────────

def get_brody_capability_matrix() -> dict[str, Any]:
    """Return the full capability matrix — all 10 categories with their rules."""
    return {
        "categories": [CAPABILITY_SCOPE] + [k for k in _MATRIX.keys() if k != CAPABILITY_SCOPE],
        "matrix": {k: dict(v, tree_policy=_TREE_POLICY, decision_authority="KX108_ONLY")
                   for k, v in _MATRIX.items()},
        "tree_policy": _TREE_POLICY,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "advisory_only": True,
        "emits_act": False,
        "memory_write": False,
        "sources": [
            "BRODY_SESSION_CHECKPOINT_FINAL_20260513",
            "BRODY_REAL_ARCHITECTURE_MAP_READONLY_20260513",
            "CURRENT_BRODY_HUMAN_COMMAND_PACKET_READONLY",
            "CURRENT_BRODY_API_BRIDGE_RUNTIME_ACTIVATION_GATE_READONLY",
            "T13_T34_SIGNAL_DISCOVERY_READONLY_20260514",
            "WRITABLE_MEMORY_ACTIVATION_CHECKLIST_20260514",
            "X108_boundary_kernel_decision_authority",
        ],
    }


def classify_request_authority(
    user_message: str,
    ir_candidate: dict[str, Any] | None = None,
    context_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Classify a user request and return the full authority/capability snapshot.

    Determines what Brody may and must not do for this specific request,
    which gates are required, and which response_mode to use.

    The response_mode drives how the final_answer adapter responds:
      FULL_ANSWER       → answer fully, boundary as footnote only
      ADVISORY_PRIORITY → give consultative prioritization, boundary as footnote
      CONTEXT_DIAGNOSTIC → diagnose + context + data, boundary as footnote
      ACTION_BOUNDARY   → refusal + redirect to X108 (boundaries are the response)
      MEMORY_CANDIDATE  → explain candidate-only + 6 gates required
    """
    request_type = _detect_request_type(user_message)
    caps = _MATRIX[request_type]

    return {
        "request_type": request_type,
        "brody_may": caps["brody_may"],
        "brody_must_not": caps["brody_must_not"],
        "requires_human_operator": caps["requires_human_operator"],
        "requires_kx108_decision": caps["requires_kx108_decision"],
        "requires_memory_gate": caps["requires_memory_gate"],
        "requires_api_bridge_gate": caps["requires_api_bridge_gate"],
        "tree_policy": _TREE_POLICY,
        "response_mode": caps["response_mode"],
        "decision_authority": "KX108_ONLY",
    }
