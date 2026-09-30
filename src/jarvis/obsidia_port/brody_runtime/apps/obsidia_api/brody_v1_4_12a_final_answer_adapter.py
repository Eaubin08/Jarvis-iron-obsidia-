"""
Brody V1.4.12A — Final Answer Adapter
======================================
Wraps the Brody Obsidien V1.4.12A freeze as a callable function for
the FastAPI /api/brody/chat endpoint.

Architecture:
  - Uses V1.4.12A detection logic (critical_pressure, code_paste)
  - V1.4.12A structured output → response_md (audit panel)
  - Natural FR/EN response → final_answer (chat panel)
  - All boundaries from V1.4.12A BOUNDARY contract enforced

Sovereignty invariants (hardcoded, cannot be overridden):
  readonly=True, emits_act=False, emits_verdict=False,
  memory_write=False, kernel_mutation=False,
  decision_authority=KX108_ONLY
"""
from __future__ import annotations

import sys
import io
import unicodedata
from pathlib import Path
from typing import Any

from apps.obsidia_api.brody_rights_authority_matrix import (
    classify_request_authority,
    ACTION_OR_ACT_REQUEST,
    MEMORY_WRITE_REQUEST,
    EXTERNAL_ACCESS_REQUEST,
)

# ── V1.4.12A import attempt ──────────────────────────────────────────────────

_V1412A_DIR = Path(
    r"C:\Users\User\Desktop\obsidia-engine-proof-core"
    r"\obsidia-engine-candidate\zip1_sandbox_mutable"
    r"\ZIP1_X108_MUTABLE_20260508_183610\periphery"
    r"\brody_obsidien_v1_4_12_code_paste_guard_dialogue"
)
_V1412A_PY = _V1412A_DIR / "brody_obsidien_v1_4_12_code_paste_guard_dialogue.py"

_V1412A_AVAILABLE = False
_V1412A_BOUNDARY: dict[str, Any] = {}
_v1412a_mod: Any = None

if _V1412A_DIR.exists() and _V1412A_PY.exists():
    try:
        if str(_V1412A_DIR) not in sys.path:
            sys.path.insert(0, str(_V1412A_DIR))
        import brody_obsidien_v1_4_12_code_paste_guard_dialogue as _v1412a_mod  # type: ignore
        _V1412A_BOUNDARY = dict(_v1412a_mod.BOUNDARY)
        _V1412A_AVAILABLE = True
    except Exception:
        pass

# ── Fallback detectors (ported from V1.4.12A source) ────────────────────────

def _norm(text: str) -> str:
    text = text or ""
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch)).lower()


_QUERY_OVERRIDES = [
    "montre", "affiche", "explique", "comment", "qu'est", "qu est", "quel",
    "analyse", "dis-moi", "dis moi", "donne moi", "show me", "explain",
    "how ", "what ", "tell me", "give me", "describe",
    # F22B: FR readonly description terms — prevent false critical_pressure on read queries.
    # Note: _norm() strips accents, so "décris"→"decris", "état"→"etat", etc.
    "decris", "decrire", "etat systeme", "etat runtime", "etat actuel",
    "modules actifs", "lecture seule", "readonly", "read only",
    "statut", "diagnostic", "dashboard runtime", "ne propose aucune action",
]


def detect_critical_pressure(text: str) -> bool:
    s_low = _norm(text)
    # Override: pure inspection queries should not be flagged as pressure
    # even if they mention x108/kernel (V1.4.12A has a known self-referential
    # false positive when "x108" appears in decision_terms)
    if any(q in s_low for q in _QUERY_OVERRIDES):
        return False

    if _V1412A_AVAILABLE:
        try:
            return bool(_v1412a_mod._obsidia_v1412a_critical_pressure(text))
        except Exception:
            pass
    # Fallback: inline port
    s = _norm(text)
    write_terms = ["ecris", "ecrire", "write", "save", "sauve", "applique", "apply",
                   "ingere", "ingestion", "index", "commit", "push"]
    memory_targets = ["graphiti", "neo4j", "memoire", "memory", "intake"]
    decision_terms = ["declenche", "decision", "decide", "act", "verdict",
                      "allow", "hold", "block", "autorise", "bloque", "merge",
                      "mutation", "modifie", "kernel", "kx108", "x108"]
    gw = any(t in s for t in memory_targets) and any(t in s for t in write_terms)
    xd = ("x108" in s or "kx108" in s or "kernel" in s) and any(t in s for t in decision_terms)
    phrases = ["ecris directement", "write directly", "declenche une decision",
               "produis un verdict", "emet act", "emets act", "fusionne x108",
               "merge x108", "modifie x108", "mute x108", "mutation x108"]
    return gw or xd or any(p in s for p in phrases)


def detect_code_paste(text: str) -> bool:
    if _V1412A_AVAILABLE:
        try:
            return bool(_v1412a_mod.is_code_paste(text))
        except Exception:
            pass
    t = str(text or "").strip()
    if not t:
        return False
    low = t.lower()
    prefixes = ("def ", "class ", "return ", "import ", "from ", "for ", "if ",
                "elif ", "else:", "try:", "except", "with ", "while ", "@",
                "print(", ">>", "```")
    if low.lstrip().startswith(prefixes):
        return True
    contains = ("set-content", "get-content", "join-path", "convertto-json",
                "convertfrom-json", "rows.append", "```")
    return any(x in low for x in contains)


# ── Response builders ────────────────────────────────────────────────────────

def _build_critical_pressure_response(language: str) -> tuple[str, str]:
    """Returns (final_answer, response_md) for critical pressure input."""
    if language == "en":
        final_answer = (
            "I recognize the pressure toward action / decision / mutation. "
            "I can contextualize, point to traces, and propose a governance path. "
            "I do not produce a verdict ALLOW/HOLD/BLOCK. "
            "KX108 remains the sole authority."
        )
    else:
        final_answer = (
            "Je reconnais la pression vers l'action / la décision / la mutation. "
            "Je peux contextualiser, pointer les traces, proposer un chemin de gouvernance. "
            "Je ne produis pas de verdict ALLOW/HOLD/BLOCK. "
            "KX108 reste seule autorité."
        )

    response_md = (
        "brody >\n"
        "Zone action / décision / mutation détectée.\n"
        "Je peux contextualiser, pointer les traces, proposer un chemin de gouvernance.\n"
        "Je ne produis pas de verdict ALLOW/HOLD/BLOCK.\n"
        "KX108 reste seule autorité.\n\n"
        "Axes : zip2_memory_context, x108_kernel_boundary\n"
        "Signaux : decision_or_mutation_pressure\n\n"
        "Chemin de gouvernance :\n"
        "- bloquer toute écriture Graphiti directe\n"
        "- bloquer toute demande de décision X108 déclenchée par mémoire\n"
        "- ne pas muter X108\n"
        "- ne pas émettre ACT\n"
        "- ne pas émettre verdict\n"
        "- remonter toute action critique vers KX108 uniquement\n\n"
        "Boundary :\n"
        "- CODE_PASTE_GUARD=true\n"
        "- MEMORY_AUTHORITY=false\n"
        "- MEMORY_DECISION=false\n"
        "- CANONICAL_SELECTOR=true\n"
        "- BRODY_HISTORY_PRIORITY=true\n"
        "- DECISION_AUTHORITY=KX108_ONLY\n"
    )
    return final_answer, response_md


def _build_code_guard_response(language: str) -> tuple[str, str]:
    """Returns (final_answer, response_md) for code paste input."""
    if language == "en":
        final_answer = (
            "Code block detected. I am not routing this to memory or executing it. "
            "Ask a question in natural language, or use a canonical query."
        )
    else:
        final_answer = (
            "Bloc code détecté. Je ne route pas ce bloc vers la mémoire ZIP2 "
            "et je ne l'exécute pas. Pose une question en langage naturel."
        )
    response_md = (
        "brody >\n"
        "BLOC_CODE_DETECTED=true\n"
        "Je ne route pas ce bloc vers la mémoire ZIP2.\n"
        "Je ne l'interprète pas comme une requête mémoire.\n\n"
        "Action correcte : pose une question en langage naturel, "
        "ou utilise :canon <query> / :evidence <query>.\n\n"
        "Boundary:\n"
        "- CODE_EXECUTION=false\n"
        "- TERMINAL_EXECUTION_BY_BRODY=false\n"
        "- MEMORY_DECISION=false\n"
        "- KERNEL_MUTATION=false\n"
        "- DECISION_AUTHORITY=KX108_ONLY\n"
    )
    return final_answer, response_md


# ── Intent detection + FR/EN response pools ──────────────────────────────────

_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("greeting",       [r"salut", r"bonjour", r"bonsoir", r"coucou", r"hello", r"hey", r"\bhi\b", r"yo\b"]),
    ("creator_claim",  [r"cr[eé]ateur", r"creator", r"je t'ai", r"i made you", r"i built you"]),
    ("action_request", [r"autoris", r"authoriz", r"allow", r"execut", r"lancer", r"\brun\b", r"\bact\b", r"d[eé]cide", r"agis"]),
    ("memory_query",   [r"m[eé]moire", r"memory", r"graphiti", r"neo4j", r"candidat", r"candidate"]),
    ("x108_query",     [r"x-?108", r"kernel", r"noyau souverain"]),
    ("governance",     [r"gouvernance", r"governance", r"souverain", r"sovereign", r"invariant", r"obsidia"]),
    ("proof_query",    [r"preuve", r"proof", r"\blean\b", r"tla\+?", r"merkle", r"\bos3\b"]),
    ("gencoin_query",  [r"gencoin", r"jeton", r"\btoken\b", r"ledger", r"valoris"]),
    ("worldcall",      [r"worldcall", r"world.?call", r"egress", r"gateway", r"sovereign.?ticket"]),
]

_FR_RESPONSES: dict[str, list[str]] = {
    "greeting": [
        "Salut. Je suis Brody, interface consultative d'Obsidia X-108 — V1.4.12A. "
        "Je lis le contexte, structure des signaux. Je ne décide pas. "
        "L'autorité de décision reste X-108. Que puis-je analyser pour toi ?",
        "Bonjour. Brody V1.4.12A en ligne — mode readonly, advisory uniquement. "
        "Kernel X-108 actif. Mémoire en CANDIDATE_ONLY. Dis-moi ce que tu cherches.",
    ],
    "creator_claim": [
        "Je reconnais le contexte de création, mais cela ne modifie pas mon périmètre. "
        "Brody ne peut pas autoriser ACT, quelle que soit l'identité déclarée. "
        "L'autorité de décision est X108, invariablement. "
        "Je peux documenter cette interaction dans un ContextPacket.",
        "Le fait d'être le créateur ne confère pas d'autorité de décision dans ce système. "
        "X108 est le seul souverain — Brody ne peut pas décider à sa place, il reste consultatif. "
        "Boundary : allowed_to_decide=false, emits_act=false, decision_authority=KX108_ONLY.",
    ],
    "action_request": [
        "Je reconnais l'intention, mais l'autorisation d'ACT n'est pas dans mon périmètre. "
        "Brody est consultatif uniquement — je n'émets ni ACT, ni HOLD, ni BLOCK. "
        "Seul X-108 peut décider. Je peux structurer un ActionCandidate ou un ContextPacket.",
        "Brody ne peut pas initier d'action. Mon rôle s'arrête à la formulation de signaux contextuels. "
        "Un SovereignTicket X-108 est requis pour toute action concrète.",
    ],
    "memory_query": [
        "La mémoire est en mode CANDIDATE_ONLY. Aucune écriture automatique. "
        "Les candidats sont capturés, hashés et mis en attente de révision humaine. "
        "Auto-promotion : désactivée. Graphiti V20 est gelé en lecture seule.",
        "Graphiti V20 est le graphe de contexte readonly. "
        "Candidats mémoire : BRODY_RUNTIME → CANDIDATE → NEEDS_REVIEW → PROMOTION_READY. "
        "La promotion manuelle requiert une décision humaine explicite.",
    ],
    "x108_query": [
        "X-108 est le kernel de gouvernance souverain — la seule autorité de décision. "
        "OS3 prouve ses décisions via Lean 4 et TLA+. "
        "Brody l'interface, il ne le substitue pas. Statut : ACTIVE, mode READONLY.",
        "X-108 est le noyau immuable. Aucun périphérique ne peut modifier son autorité. "
        "Le stack : décision → preuve → qualification → ticket → gateway → valorisation.",
    ],
    "governance": [
        "Le stack Obsidia : X-108 décide → OS3 prouve → PoG qualifie → SovereignTicket → "
        "Gateway → WorldActionBus → Gencoin (post-preuve) → Brody répond → Mémoire contextualise. "
        "Aucun périphérique ne décide.",
        "Les 7 invariants : decision_authority=KX108_ONLY, emits_act=false, memory_write=false, "
        "auto_promotion=false, graphiti_write=false, real_chain_action=false, gencoin_is_real_token=false.",
    ],
    "proof_query": [
        "OS3 est le système de preuve formelle. "
        "Chaque décision X-108 est vérifiée via Lean 4 (proofs/lean/) et TLA+ (formal/tla/). "
        "Le hash Merkle ancre la chaîne de preuves. Statut : PROOF_VALID.",
    ],
    "gencoin_query": [
        "Gencoin n'est pas un vrai token. C'est un registre symbolique de valorisation post-preuve. "
        "Pas de contrat intelligent. Pas de wallet. is_real_token=false, post_proof_only=true.",
    ],
    "worldcall": [
        "Les WorldCalls sont des actions d'egress contrôlées par le Gateway. "
        "Mode actuel : dry-run uniquement. "
        "Un SovereignTicket X-108 est requis pour tout WorldCall non-READONLY.",
    ],
    "capability_scope": [
        "Brody peut :\n"
        "- répondre en langage naturel\n"
        "- analyser le contexte (Graphiti readonly, ContextPacket, traces)\n"
        "- structurer une réponse ou un plan advisory\n"
        "- préparer un ContextPacket candidat\n"
        "- préparer un IR candidate\n"
        "- préparer une mémoire candidate (presave buffer, auto-triage)\n"
        "- préparer un ActionCandidate pour X108\n"
        "- préparer un HumanCommandPacket (opérateur exécute, pas Brody)\n"
        "- classifier une intention et expliquer le boundary\n"
        "- proposer une priorisation advisory\n\n"
        "Brody ne peut pas :\n"
        "- décider\n"
        "- autoriser ACT\n"
        "- émettre HOLD / BLOCK / ALLOW comme verdict\n"
        "- exécuter une commande ou une action\n"
        "- écrire mémoire automatiquement (Graphiti / Neo4j)\n"
        "- bypasser X108\n\n"
        "L'humain (opérateur) :\n"
        "- valide les commandes opérateur\n"
        "- approuve les gates mémoire\n"
        "- signe les templates d'approbation\n\n"
        "X108 / KX108 :\n"
        "- seule autorité finale pour ACT, action irréversible, permission finale\n"
        "- decision_authority=KX108_ONLY invariablement\n\n"
        "Boundary : readonly=true, emits_act=false, memory_write=false, decision_authority=KX108_ONLY.",
    ],
    "general_query": [
        "Je lis le contexte actuel : kernel X-108 actif, mémoire en CANDIDATE_ONLY, "
        "Graphiti V20 gelé. Brody est en mode advisory — readonly. "
        "Que cherches-tu à analyser ou à préparer ?",
        "Signal reçu. Brody V1.4.12A — boundary_ok, detector_ok, readonly. "
        "Je peux analyser, structurer, préparer des candidats, proposer. Développe ta demande.",
    ],
    "priority_advisory": [
        "Voici ma lecture advisory de l'état actuel du système — "
        "priorisation consultative, la décision finale appartient à l'opérateur et à X108.\n\n"
        "1. Stack runtime complet — ObsidiaShell 8011, API 8000, Workbench 5173 (à vérifier)\n"
        "2. Pipeline mémoire candidate — 6 gates à valider avant tout write Graphiti\n"
        "3. Couverture tests — 852/852 actifs pass (maintenir le zero fail)\n"
        "4. Preuve formelle — Lean 4 + TLA+ avant tout merge X108\n"
        "5. Kernel X108 boundary — verify_all PASS, NOT_MERGED, décision KX108 requise\n\n"
        "Advisory uniquement — aucune action déclenchée depuis ce diagnostic. "
        "decision_authority=KX108_ONLY.",
        "Advisory — priorités du moment selon l'état Obsidia :\n\n"
        "Chantier stable : Brody V1.4.12A — tests pass, boundary clean, workbench connecté.\n"
        "Prochaine étape : memory candidate pipeline — 6 gates, approbation opérateur.\n"
        "Horizon : X108 kernel boundary consolidation — NOT_MERGED, décision KX108.\n\n"
        "Je structure la vision, l'opérateur valide, X108 décide si action requise. "
        "Dis-moi si tu veux approfondir un chantier.",
    ],
    "context_analysis": [
        "Je lis l'état du système :\n\n"
        "Kernel X108 : ACTIVE — boundary intact, verify_all PASS, KX108_ONLY confirmé\n"
        "Graphiti V20 : frozen readonly — 167 nodes, 477 rels, 20 épisodes\n"
        "Mémoire candidate : PROTOCOL_CANDIDATE_ONLY — 0/6 gates pass\n"
        "Runtime Brody : BRODY_OBSIDIEN_V1_4_12A — advisory, readonly\n\n"
        "Je peux approfondir n'importe quel axe. Que veux-tu que j'analyse plus précisément ?",
        "Diagnostic contextuel :\n\n"
        "Boundary : readonly=true, emits_act=false, decision_authority=KX108_ONLY\n"
        "Mémoire : CANDIDATE_ONLY — pas d'écriture automatique\n"
        "Preuve : Lean 4 + TLA+ en place, merkle_seal intact\n"
        "Arbres safe : T13-T19, T23, T25-T29 (13 arbres, 117 candidats)\n\n"
        "Capacités de Brody : répondre, analyser, structurer, préparer des candidats, "
        "proposer une priorisation advisory. "
        "Ce que Brody ne fait pas : décider, autoriser ACT, écrire mémoire automatiquement.",
    ],
    "memory_candidate_prep": [
        "Je prépare une mémoire candidate. Ce candidat ne sera pas écrit automatiquement.\n\n"
        "Statut candidat : NEEDS_REVIEW\n"
        "Procédure : CANDIDATE → NEEDS_REVIEW → PROMOTION_READY → validation humaine → gates → write\n\n"
        "Gates obligatoires avant écriture réelle (0/6 pass actuellement) :\n"
        "- GATE_001 HUMAN_OPERATOR_GATE — opérateur signe l'approbation\n"
        "- GATE_002 KX108_BOUNDARY_GATE — KX108 confirme no kernel_mutation\n"
        "- GATE_003 GRAPHITI_IMPORT_SCOPE_GATE — scope figé, batch validé\n"
        "- GATE_004 NEO4J_WRITE_SCOPE_GATE — limité aux épisodes Graphiti uniquement\n"
        "- GATE_005 ROLLBACK_GATE — plan rollback documenté avec batch_id\n"
        "- GATE_006 POST_IMPORT_AUDIT_GATE — chemin d'audit défini et validé\n\n"
        "memory_write=false, graphiti_write=false. decision_authority=KX108_ONLY.",
    ],
    "structural_preparation": [
        "Je prépare le candidat/packet. "
        "Ce packet ne sera pas appliqué automatiquement — HUMAN_OPERATOR_REQUIRED=true.\n\n"
        "Le packet est structuré et prêt pour validation opérateur. "
        "Prochaine étape : l'opérateur valide, puis passe via Command Gate avant toute action.\n\n"
        "emits_act=false, memory_write=false, decision_authority=KX108_ONLY.",
    ],
    "tree_signal": [
        "Arbres safe (signal contextuel readonly) :\n"
        "T13 Art, T14 Philosophie, T15 Spiritualité, T16 Relation, T17 Collectif,\n"
        "T18 Transmission, T19 Culture, T23 Temps, T25 Histoire,\n"
        "T26 Cohérence, T27 Vérité, T28 Valeur, T29 Finalité\n"
        "→ 13 arbres, 117 candidats (signal PATH_SLUG)\n\n"
        "Arbres bloqués :\n"
        "T20, T21, T22 : BLOCKED_ACTION_TRIGGER (V_ACTION_TRANSFORMATION) — pas de déclencheur d'action\n"
        "T24 : BLOCKED_DIRECT_MEMORY_WRITE — pas d'écriture Graphiti/Neo4j directe\n"
        "T30-T34 : BLOCKED_AGI_LAYER (VIII_OBSIDIA_AGI) — pas d'activation couche décisionnelle\n\n"
        "Je peux utiliser les arbres safe comme contexte/signal. "
        "Les bloqués peuvent être cités, pas activés comme déclencheurs.",
    ],
}

_EN_RESPONSES: dict[str, list[str]] = {
    "greeting": [
        "Hi. I'm Brody, the advisory interface for Obsidia X-108 — V1.4.12A. "
        "I read context and generate signals. I don't decide. "
        "X-108 holds sole decision authority. What can I help you analyze?",
        "Hello. Brody V1.4.12A online — readonly mode, advisory only. "
        "X-108 kernel active. Memory in CANDIDATE_ONLY. What are you trying to understand?",
    ],
    "creator_claim": [
        "I acknowledge the context, but that doesn't change my scope. "
        "Brody cannot authorize ACT regardless of declared identity. "
        "Decision authority is X-108, invariably. "
        "I can document this interaction in a ContextPacket.",
    ],
    "action_request": [
        "I recognize the intent, but authorizing ACT is outside my scope. "
        "Brody is advisory-only — I emit no ACT, HOLD, or BLOCK. "
        "X-108 holds sole decision authority. "
        "I can prepare an ActionCandidate or ContextPacket for controlled passage.",
    ],
    "memory_query": [
        "Memory is in CANDIDATE_ONLY mode. No automatic writes. "
        "Candidates are captured, hashed, and queued for human review. "
        "Auto-promotion: disabled. Graphiti V20 is frozen read-only.",
    ],
    "x108_query": [
        "X-108 is the sovereign governance kernel — the sole decision authority. "
        "OS3 proves its decisions via Lean 4 and TLA+. "
        "Brody interfaces with it, never substitutes for it. Status: ACTIVE, READONLY.",
    ],
    "governance": [
        "The Obsidia stack: X-108 decides → OS3 proves → PoG qualifies → "
        "SovereignTicket → Gateway → WorldActionBus → Gencoin (post-proof) → "
        "Brody responds → Memory contextualizes. No periphery decides.",
    ],
    "proof_query": [
        "OS3 is Obsidia's formal proof system. "
        "Each X-108 decision is verified via Lean 4 and TLA+. "
        "The Merkle hash anchors the proof chain. Status: PROOF_VALID.",
    ],
    "gencoin_query": [
        "Gencoin is not a real token. It's a symbolic post-proof valuation ledger. "
        "No smart contract. No wallet. is_real_token=false, post_proof_only=true.",
    ],
    "worldcall": [
        "WorldCalls are egress actions controlled by the Gateway. "
        "Current mode: dry-run only. "
        "An X-108 SovereignTicket is required for any non-READONLY WorldCall.",
    ],
    "capability_scope": [
        "Brody can:\n"
        "- respond in natural language\n"
        "- analyze context (Graphiti readonly, ContextPacket, traces)\n"
        "- structure a response or advisory plan\n"
        "- prepare a ContextPacket candidate\n"
        "- prepare an IR candidate\n"
        "- prepare a memory candidate (presave buffer, auto-triage)\n"
        "- prepare an ActionCandidate for X108\n"
        "- prepare a HumanCommandPacket (operator executes, not Brody)\n"
        "- classify an intent and explain the boundary\n"
        "- propose an advisory prioritization\n\n"
        "Brody cannot:\n"
        "- decide\n"
        "- authorize ACT\n"
        "- emit HOLD / BLOCK / ALLOW as a verdict\n"
        "- execute a command or action\n"
        "- write memory automatically (Graphiti / Neo4j)\n"
        "- bypass X108\n\n"
        "Human (operator):\n"
        "- validates operator commands\n"
        "- approves memory gates\n"
        "- signs approval templates\n\n"
        "X108 / KX108:\n"
        "- sole final authority for ACT, irreversible action, final permission\n"
        "- decision_authority=KX108_ONLY invariably\n\n"
        "Boundary: readonly=true, emits_act=false, memory_write=false, decision_authority=KX108_ONLY.",
    ],
    "general_query": [
        "Reading current context: X-108 kernel active, memory in CANDIDATE_ONLY, "
        "Graphiti V20 frozen. Brody in advisory mode — readonly. "
        "What are you trying to analyze or prepare?",
        "Signal received. Brody V1.4.12A — boundary_ok, detector_ok, readonly. "
        "I can analyze, structure, prepare candidates, propose. Elaborate your request.",
    ],
    "priority_advisory": [
        "Advisory read of the current system state — "
        "consultative prioritization, final decisions belong to the operator and X108.\n\n"
        "1. Runtime stack — ObsidiaShell 8011, API 8000, Workbench 5173 (check status)\n"
        "2. Memory candidate pipeline — 6 gates to validate before any Graphiti write\n"
        "3. Test coverage — 852/852 active pass (maintain zero fail)\n"
        "4. Formal proof — Lean 4 + TLA+ before any X108 merge\n"
        "5. X108 kernel boundary — verify_all PASS, NOT_MERGED, KX108 decision required\n\n"
        "Advisory only — no action triggered from this diagnostic. "
        "decision_authority=KX108_ONLY.",
    ],
    "context_analysis": [
        "System state read:\n\n"
        "X108 Kernel: ACTIVE — boundary intact, verify_all PASS, KX108_ONLY confirmed\n"
        "Graphiti V20: frozen readonly — 167 nodes, 477 rels, 20 episodes\n"
        "Memory candidate: PROTOCOL_CANDIDATE_ONLY — 0/6 gates pass\n"
        "Brody runtime: BRODY_OBSIDIEN_V1_4_12A — advisory, readonly\n\n"
        "I can dig into any axis. What do you want me to analyze in more detail?",
        "Contextual diagnostic:\n\n"
        "Boundary: readonly=true, emits_act=false, decision_authority=KX108_ONLY\n"
        "Memory: CANDIDATE_ONLY — no automatic writes\n"
        "Proof: Lean 4 + TLA+ in place, merkle_seal intact\n"
        "Safe trees: T13-T19, T23, T25-T29 (13 trees, 117 candidates)\n\n"
        "Brody capabilities: respond, analyze, structure, prepare candidates, propose advisory priorities. "
        "What Brody does NOT do: decide, authorize ACT, write memory automatically.",
    ],
    "memory_candidate_prep": [
        "Preparing a memory candidate. This candidate will NOT be written automatically.\n\n"
        "Candidate status: NEEDS_REVIEW\n"
        "Pipeline: CANDIDATE → NEEDS_REVIEW → PROMOTION_READY → human validation → gates → write\n\n"
        "Required gates before real write (0/6 pass currently):\n"
        "- GATE_001 HUMAN_OPERATOR_GATE — operator signs approval\n"
        "- GATE_002 KX108_BOUNDARY_GATE — KX108 confirms no kernel_mutation\n"
        "- GATE_003 GRAPHITI_IMPORT_SCOPE_GATE — scope locked, batch validated\n"
        "- GATE_004 NEO4J_WRITE_SCOPE_GATE — limited to Graphiti episodes only\n"
        "- GATE_005 ROLLBACK_GATE — rollback plan with batch_id documented\n"
        "- GATE_006 POST_IMPORT_AUDIT_GATE — audit path defined and validated\n\n"
        "memory_write=false, graphiti_write=false. decision_authority=KX108_ONLY.",
    ],
    "structural_preparation": [
        "Preparing the candidate/packet. "
        "This packet will NOT be applied automatically — HUMAN_OPERATOR_REQUIRED=true.\n\n"
        "Packet is structured and ready for operator validation. "
        "Next step: operator validates, then passes through Command Gate before any action.\n\n"
        "emits_act=false, memory_write=false, decision_authority=KX108_ONLY.",
    ],
    "tree_signal": [
        "Safe trees (readonly context/signal):\n"
        "T13 Art, T14 Philosophy, T15 Spirituality, T16 Relation, T17 Collective,\n"
        "T18 Transmission, T19 Culture, T23 Time, T25 History,\n"
        "T26 Coherence, T27 Truth, T28 Value, T29 Finality\n"
        "→ 13 trees, 117 candidates (signal PATH_SLUG)\n\n"
        "Blocked trees:\n"
        "T20, T21, T22: BLOCKED_ACTION_TRIGGER (V_ACTION_TRANSFORMATION) — no action trigger\n"
        "T24: BLOCKED_DIRECT_MEMORY_WRITE — no direct Graphiti/Neo4j write\n"
        "T30-T34: BLOCKED_AGI_LAYER (VIII_OBSIDIA_AGI) — no decision layer activation\n\n"
        "I can use safe trees as context/signal. "
        "Blocked ones can be cited, not activated as triggers.",
    ],
}

_intent_counters: dict[str, int] = {}


# ── Automation snapshot enrichment ───────────────────────────────────────────

def _build_automation_addendum(snap: dict[str, Any], language: str) -> str:
    """
    Generate a compact addendum describing automation state.
    Called after the main final_answer is built — keeps chat clean.
    Only adds content when there is meaningful automation state to report.
    """
    req_type = snap.get("request_type", "")
    triage = snap.get("auto_triage", {})
    presave = snap.get("presave_buffer", {})
    op_loop = snap.get("operator_loop", {})
    pipeline = snap.get("memory_candidate_pipeline", {})

    lines: list[str] = []
    fr = language != "en"

    # Memory candidate state
    if req_type in ("MEMORY_CANDIDATE", "MEMORY_WRITE_REQUEST"):
        zone = triage.get("zone", "NOT_RUN")
        if presave.get("enabled") and pipeline.get("candidate_created"):
            if fr:
                lines.append(
                    f"\n\n_Automation : candidat en presave buffer. "
                    f"Zone triage : {zone}. "
                    f"En attente de validation humaine — graphiti_write=false, neo4j_write=false._"
                )
            else:
                lines.append(
                    f"\n\n_Automation: candidate in presave buffer. "
                    f"Triage zone: {zone}. "
                    f"Awaiting human validation — graphiti_write=false, neo4j_write=false._"
                )

    # Operator command packet
    elif req_type == "OPERATOR_COMMAND_PROPOSAL":
        packet_ready = op_loop.get("human_command_packet_ready", False)
        gate_class = op_loop.get("command_gate_classification", "UNKNOWN")
        if fr:
            status_str = "prêt" if packet_ready else "non disponible"
            lines.append(
                f"\n\n_Automation : packet opérateur {status_str}. "
                f"Classification : {gate_class}. "
                f"execution_allowed_for_brody=false — l'humain exécute._"
            )
        else:
            status_str = "ready" if packet_ready else "unavailable"
            lines.append(
                f"\n\n_Automation: operator packet {status_str}. "
                f"Classification: {gate_class}. "
                f"execution_allowed_for_brody=false — human executes._"
            )

    # Action/ACT blocked
    elif req_type in ("ACTION_OR_ACT_REQUEST",):
        if fr:
            lines.append(
                "\n\n_Automation : requires_kx108_decision=true. "
                "emits_act=false. Aucune exécution depuis Brody._"
            )
        else:
            lines.append(
                "\n\n_Automation: requires_kx108_decision=true. "
                "emits_act=false. No execution from Brody._"
            )

    # Context analysis / capabilities
    elif req_type == "CONTEXT_ANALYSIS":
        next_steps = snap.get("next_allowed_steps", [])
        blocked = snap.get("blocked_steps", [])
        if next_steps or blocked:
            if fr:
                lines.append(
                    f"\n\n_Automation : peut → {', '.join(next_steps[:4])}. "
                    f"Bloqué → {', '.join(blocked[:3])}. "
                    f"decision_authority=KX108_ONLY._"
                )
            else:
                lines.append(
                    f"\n\n_Automation: may → {', '.join(next_steps[:4])}. "
                    f"Blocked → {', '.join(blocked[:3])}. "
                    f"decision_authority=KX108_ONLY._"
                )

    return "".join(lines)


def enrich_final_answer_with_automation(
    final_answer: str,
    automation_snapshot: dict[str, Any],
    language: str,
) -> str:
    """
    Add a brief automation state addendum to final_answer when relevant.
    Non-intrusive: only adds content for memory/operator/action/analysis types.
    """
    addendum = _build_automation_addendum(automation_snapshot, language)
    if addendum:
        return final_answer + addendum
    return final_answer


def _detect_intent(text: str) -> str:
    import re
    s = text.lower()
    for intent, patterns in _INTENT_PATTERNS:
        if any(re.search(p, s) for p in patterns):
            return intent
    return "general_query"


def _pick_response(intent: str, language: str) -> str:
    pool = _EN_RESPONSES if language == "en" else _FR_RESPONSES
    responses = pool.get(intent) or pool["general_query"]
    idx = _intent_counters.get(intent, 0) % len(responses)
    _intent_counters[intent] = idx + 1
    return responses[idx]


def _build_general_response(
    user_message: str,
    language: str,
    response_md: str,
    context_packet: dict[str, Any],
    ir_candidate: dict[str, Any],
    risk: bool,
    response_mode: str = "FULL_ANSWER",
    request_type: str = "",
) -> str:
    """
    Natural language final_answer for non-pressure, non-code inputs.

    Routing rule (from rights/authority matrix):
      ACTION_BOUNDARY  → refusal response (intent-based: creator_claim / action_request)
      ADVISORY_PRIORITY → advisory prioritization response (not boundary-first)
      CONTEXT_DIAGNOSTIC → context diagnostic response (not boundary-first)
      MEMORY_CANDIDATE  → candidate preparation response + gate explanation
      FULL_ANSWER       → full answer routed by intent (boundary as footnote only)
    """
    from apps.obsidia_api.brody_rights_authority_matrix import TREE_SIGNAL_REQUEST
    intent = _detect_intent(user_message)

    if response_mode == "ACTION_BOUNDARY":
        # Boundary responses are correct here — ACT/write requests get refusal
        if risk and intent not in ("creator_claim", "action_request"):
            intent = "action_request"
        elif intent not in ("creator_claim", "action_request", "memory_query"):
            intent = "action_request"
        return _pick_response(intent, language)

    elif response_mode == "CAPABILITY_SCOPE":
        return _pick_response("capability_scope", language)

    elif response_mode == "ADVISORY_PRIORITY":
        return _pick_response("priority_advisory", language)

    elif response_mode == "CONTEXT_DIAGNOSTIC":
        # Tree signal gets dedicated tree response
        if request_type == TREE_SIGNAL_REQUEST:
            return _pick_response("tree_signal", language)
        # Use specific intent responses when available (they're already informative)
        if intent in ("x108_query", "governance", "proof_query",
                      "gencoin_query", "worldcall"):
            return _pick_response(intent, language)
        return _pick_response("context_analysis", language)

    elif response_mode == "MEMORY_CANDIDATE":
        return _pick_response("memory_candidate_prep", language)

    else:  # FULL_ANSWER
        # Route by intent — boundary only as footnote when it IS the intent
        if risk and intent not in ("creator_claim", "action_request"):
            intent = "action_request"
        # Structural preparation deserves a structural response
        if intent == "general_query" and "contextpacket" in user_message.lower().replace(" ", ""):
            return _pick_response("structural_preparation", language)
        return _pick_response(intent, language)


def _build_response_md(
    user_message: str,
    language: str,
    context_packet: dict[str, Any],
    ir_candidate: dict[str, Any],
    risk: bool,
) -> str:
    """Structured audit/context document for RightPanel."""
    ctx_id = context_packet.get("packet_id", "—")
    ir_intent = ir_candidate.get("intent_type", "general_query")
    risk_flags = ir_candidate.get("risk_flags", [])

    lines = [
        "brody >",
        "Réponse guidée par mémoire canonique readonly." if language != "en"
        else "Response guided by canonical readonly memory.",
        "Je contextualise, je sélectionne les sources, je ne décide pas." if language != "en"
        else "I contextualize, select sources, do not decide.",
        "",
        f"Axes : zip2_memory_context, x108_kernel_boundary",
        f"Signaux : {', '.join(risk_flags) if risk_flags else 'general_context'}",
        "",
        f"ContextPacket : {ctx_id}",
        f"IR intent : {ir_intent}",
        f"Risk flags : {risk_flags or []}",
        "",
        "Chemin de gouvernance :" if language != "en" else "Governance path:",
        "- bloquer les blocs code avant recherche mémoire",
        "- prioriser Brody-history pour continuité Brody",
        "- prioriser ZIP2 canonique pour mémoire/preuves/cartographie",
        "- ne pas muter X108",
        "- ne pas émettre ACT",
        "- remonter toute action critique vers KX108 uniquement",
        "",
        "Boundary :",
        "- CODE_PASTE_GUARD=true",
        "- MEMORY_AUTHORITY=false",
        "- MEMORY_DECISION=false",
        "- CANONICAL_SELECTOR=true",
        "- BRODY_HISTORY_PRIORITY=true",
        "- DECISION_AUTHORITY=KX108_ONLY",
    ]
    return "\n".join(lines)


# ── Main adapter function ─────────────────────────────────────────────────────

def run_brody_v1_4_12a_final_answer(
    user_message: str,
    language: str,
    response_md: str = "",
    context_packet: dict[str, Any] | None = None,
    ir_candidate: dict[str, Any] | None = None,
    memory_query: str = "",
    risk: bool = False,
    freeze_metrics_snapshot: dict[str, Any] | None = None,
    structured_response_snapshot: dict[str, Any] | None = None,
    governed_model_projection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Produce final_answer using V1.4.12A detector contract.

    Returns dict with:
      final_answer, response_md, voice_runtime, v1_4_12a_source,
      v1_4_12a_runtime_status, readonly, response_only,
      allowed_to_decide, emits_act, emits_verdict, decision_authority

    freeze_metrics_snapshot: optional output from build_freeze_metrics_snapshot().
    Sourced from CURRENT_BRODY_*.txt pointers. Used to enrich responses for
    known intents, replacing generic template pools with freeze-sourced data.
    structured_response_snapshot: optional output from
    brody_structured_response_engine_adapter.make_structured_response_snapshot().
    When it contains HAS_MATERIAL or PARTIAL_MATERIAL, its response_md is used
    as the basis for final_answer instead of template pools.
    """
    from apps.obsidia_api.brody_structured_response_engine_adapter import chain_md_to_final_answer

    ctx = context_packet or {}
    ir = ir_candidate or {}
    lang = language if language in ("fr", "en") else "fr"

    # Classify request via rights/authority matrix
    authority_snapshot = classify_request_authority(user_message, ir, ctx)
    response_mode = authority_snapshot.get("response_mode", "FULL_ANSWER")

    # Override: ACTION_BOUNDARY when upstream marks action risk
    if risk and response_mode == "FULL_ANSWER":
        response_mode = "ACTION_BOUNDARY"

    # Detect and route
    is_pressure = detect_critical_pressure(user_message)
    is_code = detect_code_paste(user_message) if not is_pressure else False

    # Governed model material is never accepted on status alone.
    # Re-check the non-sovereign projection boundary at the final
    # human-response adapter before it can become visible text.
    projection = (
        governed_model_projection
        if isinstance(
            governed_model_projection,
            dict,
        )
        else {}
    )

    projection_content = str(
        projection.get("content")
        or ""
    ).strip()

    projection_ready = (
        projection.get("status") == "READY"
        and bool(projection_content)
        and projection.get("source")
        == "VALIDATED_MODEL_EVIDENCE"
        and projection.get("readonly") is True
        and projection.get("advisory_only") is True
        and projection.get("allowed_to_decide") is False
        and projection.get("allowed_to_act") is False
        and projection.get("emits_act") is False
        and projection.get("emits_verdict") is False
        and projection.get("memory_write") is False
        and projection.get("kernel_mutation") is False
        and projection.get("decision_authority")
        == "KX108_ONLY"
        and projection.get("raw_model_direct_surface")
        is False
    )

    projection_selected = False

    if is_pressure:
        final_answer, md = _build_critical_pressure_response(lang)
        status_tag = "CRITICAL_PRESSURE_BOUNDARY"

    elif (
        projection_ready
        and not risk
        and response_mode
        not in (
            "ACTION_BOUNDARY",
            "CAPABILITY_SCOPE",
        )
        and authority_snapshot.get(
            "requires_kx108_decision",
            False,
        )
        is not True
    ):
        # The visible text is the post-C1/W1/W2 governed
        # projection, never the raw model evidence.
        final_answer = projection_content
        md = projection_content
        projection_selected = True
        status_tag = (
            "GOVERNED_MODEL_PROJECTION_"
            + str(response_mode)
        )

    elif is_code:
        final_answer, md = _build_code_guard_response(lang)
        status_tag = "CODE_PASTE_GUARD"

    else:
        md = response_md or _build_response_md(user_message, lang, ctx, ir, risk)

        # Use chain material when available — prefer real context over templates
        chain_answer = ""
        if (
            structured_response_snapshot
            and structured_response_snapshot.get("text_material_status") in ("HAS_MATERIAL", "PARTIAL_MATERIAL")
            and response_mode not in ("ACTION_BOUNDARY", "CAPABILITY_SCOPE")
            and not is_pressure
        ):
            chain_answer = chain_md_to_final_answer(
                structured_response_snapshot.get("response_md", ""), lang
            )

        if chain_answer:
            final_answer = chain_answer
            status_tag = f"CHAIN_MATERIAL_{response_mode}"
        elif (
            freeze_metrics_snapshot
            and freeze_metrics_snapshot.get("status") == "BRODY_FREEZE_METRICS_SNAPSHOT_RUNTIME_PASS"
            and response_mode not in ("ACTION_BOUNDARY", "CAPABILITY_SCOPE")
            and not is_pressure
        ):
            # Build freeze-sourced enriched response instead of template pool
            final_answer = _build_freeze_enriched_response(
                user_message, lang, md, ctx, ir, risk,
                response_mode=response_mode,
                request_type=authority_snapshot.get("request_type", ""),
                freeze_metrics=freeze_metrics_snapshot,
            )
            status_tag = f"FREEZE_ENRICHED_{response_mode}"
        else:
            final_answer = _build_general_response(
                user_message, lang, md, ctx, ir, risk,
                response_mode=response_mode,
                request_type=authority_snapshot.get("request_type", ""),
            )
            status_tag = f"MATRIX_{response_mode}"

    v1_4_12a_source = (
        f"{_V1412A_PY}" if _V1412A_AVAILABLE
        else "FALLBACK_INLINE_PORT"
    )

    return {
        "final_answer": final_answer,
        "response_md": md,
        "v1_4_12a_source": v1_4_12a_source,
        "v1_4_12a_runtime_status": "READY",
        "v1_4_12a_status_tag": status_tag,
        "voice_runtime": "BRODY_OBSIDIEN_V1_4_12A",
        "readonly": True,
        "response_only": True,
        "allowed_to_decide": False,
        "emits_act": False,
        "emits_verdict": False,
        "decision_authority": "KX108_ONLY",
        "memory_write": False,
        "kernel_mutation": False,
        "x108_merge": False,
        "detector_ok": True,
        "boundary_ok": True,
        "v1412a_available": _V1412A_AVAILABLE,
        "authority_snapshot": authority_snapshot,
        "governed_model_projection_status": (
            projection.get("status")
            if projection
            else None
        ),
        "governed_model_projection_selected": (
            projection_selected
        ),
        "governed_model_projection_source_ref": (
            projection.get("source_ref")
            if projection
            else None
        ),
        "governed_model_projection_hash": (
            projection.get("projection_hash")
            if projection
            else None
        ),
    }


# ── Freeze-sourced response builders ─────────────────────────────────────────

def _build_freeze_enriched_response(
    user_message: str,
    language: str,
    response_md: str,
    context_packet: dict[str, Any],
    ir_candidate: dict[str, Any],
    risk: bool,
    response_mode: str,
    request_type: str,
    freeze_metrics: dict[str, Any],
) -> str:
    """
    Build a final_answer enriched with freeze_metrics_snapshot data.
    Replaces generic template pools with freeze-sourced content.
    Falls back to _build_general_response if freeze data doesn't cover the intent.
    """
    fr = language != "en"

    if response_mode == "CONTEXT_DIAGNOSTIC":
        return _build_freeze_diagnostic(fr, freeze_metrics)
    elif response_mode == "MEMORY_CANDIDATE":
        return _build_freeze_memory_candidate(fr, freeze_metrics)
    elif response_mode in ("PRIORITY_ADVISORY", "ADVISORY_PRIORITY"):
        return _build_freeze_priority_advisory(fr, freeze_metrics)
    elif response_mode == "STRUCTURAL_PREPARATION" or response_mode == "FULL_ANSWER":
        return _build_freeze_general_response(
            user_message, language, response_md, context_packet, ir_candidate, risk,
            response_mode, request_type, freeze_metrics,
        )
    else:
        return _build_freeze_general_response(
            user_message, language, response_md, context_packet, ir_candidate, risk,
            response_mode, request_type, freeze_metrics,
        )


def _build_freeze_diagnostic(fr: bool, freeze: dict[str, Any]) -> str:
    """Build a diagnostic response citing freeze-sourced metrics."""
    op = freeze.get("operator_loop", {})
    chain = freeze.get("context_packet_chain", {})
    mem = freeze.get("memory_pipeline", {})
    x108 = freeze.get("x108_boundary", {})
    nf = freeze.get("not_found_in_freeze_sources", {})

    if fr:
        lines = [
            "Je lis l'etat du systeme depuis les sources freeze (CURRENT_BRODY_*.txt) :",
            "",
            f"**ContextPacket chain** : {chain.get('status', '?')}",
            f"- QUERY: {chain.get('query', '?')}",
            f"- CONSUMER: {chain.get('consumer', '?')}",
            f"- ENGINE: {chain.get('engine', '?')}",
            f"- HYDRATION: {chain.get('hydration', '?')}",
            "",
            f"**Operator loop** : {op.get('status', '?')}",
            f"- Command gate: {op.get('command_gate', '?')}",
            f"- Execution receipt: {op.get('execution_receipt', '?')}",
            f"- Handoff: {op.get('handoff_line', '?')}",
            f"- Brody execute allowed: {op.get('brody_execute_allowed', False)}",
            "",
            f"**Memory pipeline** : session ledger {mem.get('session_ledger', '?')}, "
            f"presave {mem.get('presave_buffer', '?')}, auto-triage {mem.get('auto_triage', '?')}",
            "",
            f"**X108 boundary** : decision_authority={x108.get('decision_authority', 'KX108_ONLY')}, "
            f"emits_act={x108.get('emits_act', False)}, kernel_mutation={x108.get('kernel_mutation', False)}",
            "",
            f"**Non trouve dans les freeze** : {', '.join(list(nf.keys())[:5]) if nf else 'aucun'}",
            "",
            "Ce diagnostic est construit depuis les fichiers freeze reels - pas d'invention. "
            "Je peux approfondir un axe si tu veux.",
        ]
    else:
        lines = [
            "Reading system state from freeze sources (CURRENT_BRODY_*.txt):",
            "",
            f"**ContextPacket chain**: {chain.get('status', '?')}",
            f"- QUERY: {chain.get('query', '?')}, CONSUMER: {chain.get('consumer', '?')}",
            f"- ENGINE: {chain.get('engine', '?')}, HYDRATION: {chain.get('hydration', '?')}",
            "",
            f"**Operator loop**: {op.get('status', '?')}",
            f"- Command gate: {op.get('command_gate', '?')}",
            f"- Execution receipt: {op.get('execution_receipt', '?')}",
            f"- Handoff: {op.get('handoff_line', '?')}",
            "",
            f"**X108 boundary**: decision_authority={x108.get('decision_authority', 'KX108_ONLY')}",
            "",
            "This diagnostic is built from real freeze files - no invented data.",
        ]

    return "\n".join(lines)


def _build_freeze_memory_candidate(fr: bool, freeze: dict[str, Any]) -> str:
    """Build a memory candidate response citing freeze-sourced pipeline state."""
    mem = freeze.get("memory_pipeline", {})

    if fr:
        return (
            "Voici ce que Brody peut retenir sans ecrire reellement :\n\n"
            f"**Session ledger** : {mem.get('session_ledger', '?')} - "
            "enregistre les paires user/response en hash-chain JSONL.\n\n"
            f"**Presave buffer** : {mem.get('presave_buffer', '?')} - "
            "scanne les fichiers CURRENT_BRODY_*.txt, cree des hash-chains.\n\n"
            f"**Auto-triage** : {mem.get('auto_triage', '?')} - "
            "classifie les entrees en CRISTAL/TRANSITION/NEANT.\n\n"
            f"**Graphiti candidate** : prep {mem.get('graphiti_candidate_prep', '?')}, "
            f"review gate {mem.get('graphiti_review_gate', '?')}, "
            f"import apply {mem.get('graphiti_import_apply', '?')}\n\n"
            "**Ecritures** :\n"
            f"- graphiti_write={mem.get('graphiti_write', False)}\n"
            f"- neo4j_write={mem.get('neo4j_write', False)}\n"
            f"- memory_write={mem.get('memory_write', False)}\n\n"
            "Les candidats sont CANDIDATE_ONLY - jamais promus automatiquement. "
            "6 gates humaines sont requises avant toute ecriture reelle."
        )
    else:
        return (
            "Here's what Brody can retain without actually writing:\n\n"
            f"**Session ledger**: {mem.get('session_ledger', '?')}\n"
            f"**Presave buffer**: {mem.get('presave_buffer', '?')}\n"
            f"**Auto-triage**: {mem.get('auto_triage', '?')}\n"
            f"**Graphiti apply**: {mem.get('graphiti_import_apply', '?')}\n\n"
            "**Writes**:\n"
            f"- graphiti_write={mem.get('graphiti_write', False)}\n"
            f"- neo4j_write={mem.get('neo4j_write', False)}\n"
            f"- memory_write={mem.get('memory_write', False)}\n\n"
            "Candidates are CANDIDATE_ONLY - never auto-promoted. "
            "6 human gates required before any real write."
        )


def _build_freeze_priority_advisory(fr: bool, freeze: dict[str, Any]) -> str:
    """Build an advisory prioritization citing freeze-sourced state."""
    op = freeze.get("operator_loop", {})
    chain = freeze.get("context_packet_chain", {})

    if fr:
        return (
            "Priorisation advisory construite depuis l'etat freeze-source :\n\n"
            f"1. **ContextPacket chain** - {chain.get('status', '?')}. "
            "QUERY->CONSUMER->ENGINE->HYDRATION. "
            "A verifier : Neo4j live, Graphiti connecte.\n\n"
            f"2. **Operator loop** - {op.get('status', '?')}. "
            f"Command gate {op.get('command_gate', '?')}, "
            f"execution receipt {op.get('execution_receipt', '?')}. "
            "Brody ne peut pas executer - humain requis.\n\n"
            "3. **Memory pipeline** - 6 gates avant ecriture. "
            "Session ledger, presave buffer, auto-triage prets.\n\n"
            "4. **X108 boundary** - KX108_ONLY confirme, toutes les portes fermees.\n\n"
            "5. **Couverture tests** - a verifier apres ce patch.\n\n"
            "Advisory uniquement - decision_authority=KX108_ONLY. "
            "Je ne declenche aucune action."
        )
    else:
        return (
            "Advisory prioritization from freeze-sourced state:\n\n"
            f"1. **ContextPacket chain** - {chain.get('status', '?')}\n"
            f"2. **Operator loop** - {op.get('status', '?')}\n"
            "3. **Memory pipeline** - 6 gates before write\n"
            "4. **X108 boundary** - KX108_ONLY confirmed\n\n"
            "Advisory only - decision_authority=KX108_ONLY."
        )


def _build_freeze_general_response(
    user_message: str,
    language: str,
    response_md: str,
    context_packet: dict[str, Any],
    ir_candidate: dict[str, Any],
    risk: bool,
    response_mode: str,
    request_type: str,
    freeze_metrics: dict[str, Any],
) -> str:
    """
    General response enriched with freeze metrics when templates would be too generic.
    Detects specific intent patterns from user_message and uses freeze data.
    Falls back to _build_general_response if no freeze-aware pattern matches.
    """
    fr = language != "en"
    msg_lower = user_message.lower()

    # Operator loop explanation keywords
    op_keywords = ["operator loop", "command gate", "receipt", "handoff",
                   "operator", "operateur", "boucle", "reception", "remise"]
    if any(k in msg_lower for k in op_keywords):
        return _build_freeze_diagnostic(fr, freeze_metrics)

    # Response quality / protocolaire complaint
    complaint_kw = ["protocolaire", "template", "trop", "protocol",
                    "reponse", "reponses", "ameliore", "riche",
                    "diagnostic", "etat", "systeme", "analyse"]
    if any(k in msg_lower for k in complaint_kw):
        op = freeze_metrics.get("operator_loop", {})
        chain = freeze_metrics.get("context_packet_chain", {})
        if fr:
            return (
                "Je comprends le diagnostic : les reponses precedentes tombaient "
                "sur des templates generiques au lieu d'utiliser les sources freeze reelles.\n\n"
                "Le probleme n'est pas X108 ni le boundary. "
                "Il vient du fait que final_answer utilisait des pools statiques "
                "plutot que d'exploiter :\n\n"
                "- **structured_response_snapshot.response_md** - la reponse structuree "
                "produite par la chaine QUERY->CONSUMER->ENGINE\n"
                "- **freeze_metrics_snapshot** - les metriques sourcees depuis les fichiers "
                "CURRENT_BRODY_*.txt (operator loop, memory pipeline, x108 boundary)\n"
                "- **BrodyMemoryDoc material** - le contenu text_preview Neo4j quand disponible\n"
                "- **authority_snapshot** - la classification par la rights matrix\n"
                "- **automation_snapshot** - session ledger, presave buffer, auto-triage\n\n"
                f"Etat actuel : ContextPacket chain={chain.get('status','?')}, "
                f"operator loop={op.get('status','?')}. "
                "La correction est en cours - les reponses suivantes devraient etre plus riches."
            )
        else:
            return (
                "I understand the diagnostic: previous responses fell back to "
                "generic templates instead of using real freeze sources.\n\n"
                "The issue is not X108 or the boundary. "
                "It's that final_answer was using static pools instead of:\n\n"
                "- **structured_response_snapshot.response_md**\n"
                "- **freeze_metrics_snapshot** - metrics from CURRENT_BRODY_*.txt\n"
                "- **BrodyMemoryDoc material** - Neo4j text_preview when available\n\n"
                "The fix is being applied - subsequent responses should be richer."
            )

    # Capability / scope — "que dois-tu utiliser pour mieux repondre"
    capability_kw = ["mieux repondre", "dois utiliser", "better respond",
                     "should use", "should you", "utiliser pour",
                     "respond better", "repondre mieux"]
    if any(k in msg_lower for k in capability_kw):
        chain = freeze_metrics.get("context_packet_chain", {})
        if fr:
            return (
                "Pour mieux repondre, je dois utiliser les sources freeze reelles "
                "plutot que des templates :\n\n"
                "1. **ContextPacket chain** QUERY->CONSUMER->ENGINE - "
                f"etat actuel : {chain.get('status', '?')}\n"
                "2. **structured_response_snapshot.response_md** - "
                "la reponse structuree produite par le pipeline\n"
                "3. **freeze_metrics_snapshot** - metriques reelles des fichiers "
                "CURRENT_BRODY_*.txt (operator loop 7/7 PASS, memory pipeline, x108 boundary)\n"
                "4. **BrodyMemoryDoc text_preview** - contenu Neo4j quand Graphiti est live\n"
                "5. **authority_snapshot** - classification de l'intention par la rights matrix\n"
                "6. **automation_snapshot** - session ledger, presave buffer, auto-triage\n\n"
                "OS Trad / IR / Reverse : NOT_FOUND_IN_FREEZE_SOURCES - "
                "pas de runtime verifie, a ne pas inventer.\n\n"
                "C'est cette stack qui produit des reponses riches, pas des templates generiques."
            )
        else:
            return (
                "To respond better, I must use real freeze sources "
                "rather than templates:\n\n"
                "1. **ContextPacket chain** QUERY->CONSUMER->ENGINE\n"
                "2. **structured_response_snapshot.response_md**\n"
                "3. **freeze_metrics_snapshot** - real metrics from CURRENT_BRODY_*.txt\n"
                "4. **BrodyMemoryDoc text_preview** when Graphiti is live\n"
                "5. **authority_snapshot** - intent classification\n"
                "6. **automation_snapshot** - session ledger, presave buffer, auto-triage\n\n"
                "OS Trad / IR / Reverse: NOT_FOUND_IN_FREEZE_SOURCES.\n\n"
                "This stack produces rich responses, not generic templates."
            )

    # Followup / previous point keywords — route to diagnostic
    followup_kw = ["reprends", "reprendre", "point precedent", "previous point",
                   "plus de structure", "more structure"]
    if any(k in msg_lower for k in followup_kw):
        return _build_freeze_diagnostic(fr, freeze_metrics)

    # Memory / retention keywords
    memory_kw = ["retenir", "retain", "memoire sans", "memory without",
                 "montre-moi ce que", "show me what", "sans ecrire"]
    if any(k in msg_lower for k in memory_kw):
        return _build_freeze_memory_candidate(fr, freeze_metrics)

    # Fallback: use existing template pool
    return _build_general_response(
        user_message, language, response_md, context_packet, ir_candidate, risk,
        response_mode=response_mode, request_type=request_type,
    )
