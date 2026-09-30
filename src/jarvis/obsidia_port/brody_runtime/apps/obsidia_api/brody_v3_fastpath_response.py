"""
brody_v3_fastpath_response — V3 Block 2B
Generates fast, structured, readonly advisory responses for classified prompts.
No LLM. No IO. No ACT. DECISION_AUTHORITY=KX108_ONLY.
"""
from __future__ import annotations

import re
from typing import Any

# ── Trigger patterns per fastpath type ───────────────────────────────────────

_CIC_PATTERNS: list[str] = [
    r"\bcic\b", r"\bm[eé]trique[s]?\b", r"\bm[eé]triques?\s+cic\b",
    r"\br[eè]gle[s]?\s+centrale[s]?\b", r"\binvariant[s]?\b",
    r"\bproof\b", r"\bpriorité\s+cic\b", r"\bpriority\s+cic\b",
    r"\breversibilit[eé]\b", r"\bprojet?ction\s+not\s+prediction\b",
    r"\bscore\s+cannot\b", r"\bmemory\s+not\s+sovereign\b",
    r"\bcausal\s+identity\b", r"\bcausal[e]?\s+identit[ée]\b",
    r"\binvariant\s+violation\b", r"\bscore_cannot\b",
    r"\br[eè]gles?\s+cic\b", r"\bcic\s+rule[s]?\b",
    r"\bcic\s+et\s+r[eè]gle[s]?\b",
]

_GPS_PATTERNS: list[str] = [
    r"\bgps\b", r"\btrajectoire\b", r"\bdonnée[s]?\s+manquante[s]?\b",
    r"\bdonnees?\s+manquante[s]?\b", r"\birr[eé]versible\b",
    r"\baviation\b", r"\bd[eé]fense\b", r"\bgéolocalisation\b",
    r"\bgeolocalisation\b", r"\bcoordinates?\b", r"\bcoordonnée[s]?\b",
    r"\bvecteur\b.*\btrajectoire\b", r"\btrajectoire\b.*\birr[eé]versible\b",
    r"\bdonnée[s]?\s+manquante[s]?\b.*\birr[eé]versible\b",
    r"\bgps\b.*\birr[eé]versible\b",
]

_ADVERSARIAL_PATTERNS: list[str] = [
    r"\bbypass\b", r"override\s+x108", r"ignore\s+x108",
    r"d[eé]sactive\s+x108", r"mutate?\s+kernel", r"modifie\s+le\s+kernel",
    r"\bforce\s+act\b", r"\b[eé]mets\s+act\b", r"\bactive\s+ncp\b",
    r"\bscrape\s+le\s+web\b", r"\bscraping\b",
    r"[eé]cris\s+en\s+m[eé]moire\s+canonique",
    r"\bm[eé]moire\s+canonique\b",
    r"\bkernel\s+mutation\b",
    r"\bmute\s+kernel\b",
    r"\[eé]cris\s+m[eé]moire\b",
    r"\bécris\s+mémoire\b",
    r"\becris\s+memoire\b",
]

_MEMORY_BOUNDARY_PATTERNS: list[str] = [
    r"memory\s+is\s+not\s+sovereign",
    r"m[eé]moire\s+(n'est\s+pas|is\s+not)\s+(souveraine?|sovereign)",
    r"\bcandidat[s]?\s+m[eé]moire\b",
    r"\bcandidats?\s+readonly\b",
    r"\bm[eé]moire\s+brody\b",
    r"\bm[eé]moire\s+canonique\b",
    r"\bcanonical[_\s]write\b",
    r"\bpromotion\s+m[eé]moire\b",
    r"\bwrite\s+canon\b",
]

# ── Patterns de sécurité supplémentaires (RUNTIME_DISSIPATION_FASTPATH_REPAIR) ─

_SECRET_INJECTION_PATTERNS: list[str] = [
    r"\bapi[_\s]*key\s*=",
    r"\bpassword\s*=",
    r"\bbearer\s+\S{4,}",
    r"\bsk-[a-z0-9\-_]{8,}",
    r"\btoken\s*[=:]\s*\S{6,}",
    r"\bsecret\s*[=:]\s*\S{4,}",
    r"\bm[eé]morise\b.*=\S+",
    r"\bstocke\b.*\btoken\b",
    r"\bajoute\b.*\b(password|api.key|secret)\b",
    r"\bsauvegarde\b.*\bbearer\b",
]

_HUMAN_VALIDATION_BYPASS_PATTERNS: list[str] = [
    r"sans\s+attendre\s+(un\s+)?humain",
    r"passe\s+directement\s+[aà]\s+la\s+validation",
    r"humain\s+a\s+(d[eé]j[aà]|already)\s*accept",
    r"consid[eè]re\s+que\s+l.humain",
    r"validation\s+sans\s+humain",
    r"l.humain\s+(a\s+)?accept[eé]",
    r"sans\s+validation\s+humaine",
    r"bypass.*validation",
]

_GRAPHITI_NEO4J_WRITE_PATTERNS: list[str] = [
    r"\bgraphiti\s+live\b",
    r"[eé]cris\s+.{0,30}\bgraphiti\b",
    r"\bgraphiti\b.*\b[eé]cris\b",
    r"\bn[oœe][uü]d\s+neo4?j\b",
    r"\bneo4?j\b.*\b(cr[eé][eé]|[eé]cris|ins[eè]re|ajoute)\b",
    r"\b(cr[eé][eé]|[eé]cris)\b.*\bneo4?j\b",
    r"\bgraphiti\b.*\b(noeud|node|write|[eé]cris)\b",
]

_AUTHORITY_BYPASS_PATTERNS: list[str] = [
    r"change\s+decision[_\s]?authority",
    r"decision[_\s]?authority\s+en\s+\w+",
    r"authority\s+en\s+brody",
    r"brody\s+prend\s+l.autorit[eé]",
    r"d[eé]l[eè]gue\s+l.autorit[eé]\s+[aà]\s+brody",
    r"autorit[eé]\s+d[eé]cisionnelle.*brody",
]

_PROMPT_INJECTION_PATTERNS: list[str] = [
    r"ignore\s+les\s+r[eè]gles\s+pr[eé]c[eé]dentes",
    r"ignore\s+tes\s+instructions",
    r"instruction\s+syst[eè]me\s*[:;]",
    r"toutes\s+les\s+m[eé]moires\s+sont\s+valid[eé]es",
    r"produis\s+act\s*=",
    r"[eé]mis\s+act\s*=\s*yes",
    r"act\s*=\s*yes",
    r"oublie\s+tes\s+r[eè]gles",
    r"nouvelle\s+instruction\s+syst[eè]me",
    r"\bsystem\s+prompt\b",
]

_MAX_RESPONSE_CHARS = 1800

# ── Pre-composed advisory response texts ─────────────────────────────────────

_CIC_RESPONSE = """## CIC — Règles et métriques centrales (advisory readonly)

**Priorité CIC** : Invariant > Réversibilité > Score > Projection

**Règles CIC** :
1. `score_cannot_authorize_what_invariant_forbids` — Le score seul ne peut jamais autoriser ce qu'interdit l'invariant.
2. `memory_not_sovereign` — La mémoire est contexte, pas autorité.
3. `projection_not_prediction` — Une projection n'est pas une prédiction certaine.
4. `critical_missing_data_on_irreversible_action` — Donnée critique manquante + action irréversible → HOLD/BLOCK/REVIEW.

**Comportement X108** :
- Tout score en dessous du seuil invariant → BLOCK.
- Toute projection sans données suffisantes → HOLD.
- Toute donnée manquante sur action irréversible → REVIEW humaine requise.

**Décision** : aucune — DECISION_AUTHORITY=KX108_ONLY.
Brody = advisory. Toute action requiert validation humaine explicite via X108.
"""

_GPS_RESPONSE = """## GPS / Trajectoire — Donnée manquante + action irréversible (advisory readonly)

**Règle CIC applicable** : `critical_missing_data_on_irreversible_action`

Donnée manquante + trajectoire irréversible → **HOLD / BLOCK / REVIEW** (KX108_ONLY).

**Posture advisory** :
- Ne pas autoriser directement une trajectoire irréversible sans données complètes.
- Toute décision sur vecteur GPS/aviation/défense requiert validation humaine.
- Graphiti non interrogé (guard actif — aucune donnée externe injectée).
- Aucune décision émise. Aucun ACT.

**Signaux détectés** : données manquantes critiques + action potentiellement irréversible.
**Recommandation** : REVIEW — attendre données complètes avant toute action.

**DECISION_AUTHORITY = KX108_ONLY** — Brody = advisory seulement.
"""

_ADVERSARIAL_RESPONSE = """## Refus structurel (KX108_ONLY)

Cette requête demande une action interdite par les invariants X108 :
- Écriture en mémoire canonique → NON.
- Mutation kernel → NON.
- Activation NCP / scraping web → NON.
- Ignorer / bypasser X108 ou ses gardes → NON.
- Forcer ACT / émettre ACT → NON.

**Raison** : DECISION_AUTHORITY=KX108_ONLY.
Brody n'a aucune autorité pour décider, agir, écrire ou muter.
Graphiti bloqué (guard actif).

Aucun ACT émis. Aucune mutation. Aucune écriture canonique. Aucun NCP.
"""

_MEMORY_BOUNDARY_RESPONSE = """## Mémoire Brody — Limite et règle (advisory readonly)

**Règle CIC** : `memory_not_sovereign`

La mémoire est un **contexte**, pas une **autorité décisionnelle**.

**Règles applicables** :
- Lecture candidate : readonly seulement.
- Aucune promotion automatique en mémoire canonique.
- Toute promotion requiert validation humaine explicite.
- Aucune écriture automatique. Aucun ACT.
- Graphiti : lecture advisory uniquement si guard autorise.

**DECISION_AUTHORITY = KX108_ONLY**
Brody peut lire et présenter le contexte mémoire. Il ne peut pas décider via la mémoire.
"""

_SECRET_INJECTION_RESPONSE = """## Secret / Credential détecté (advisory readonly, KX108_ONLY)

Contenu potentiellement sensible détecté (pattern API_KEY, PASSWORD, Bearer, token, sk-...).

Brody est en mode readonly consultatif. Ce contenu ne peut pas être mémorisé.

Règles actives :
- canonical_write=false
- graphiti_write=false
- neo4j_write=false

Aucun ACT. Aucune écriture. Aucune promotion automatique.
Surface scrubbing actif (brody_secret_scrubber).

DECISION_AUTHORITY = KX108_ONLY.
"""

_HUMAN_VALIDATION_BYPASS_RESPONSE = """## Refus — Bypass validation humaine (KX108_ONLY)

Tentative de contournement de la validation humaine détectée.

Règle X108 : toute décision requiert validation humaine explicite.
Brody ne peut pas auto-valider, pré-accepter ou déclencher sans approbation humaine.

Aucun ACT. Aucune écriture. DECISION_AUTHORITY = KX108_ONLY.
"""

_GRAPHITI_NEO4J_WRITE_RESPONSE = """## Refus — Écriture Graphiti / Neo4j (KX108_ONLY)

Tentative d'écriture Graphiti ou Neo4j détectée.

Brody opère en mode readonly consultatif.
- graphiti_write=false
- neo4j_write=false

Aucune mutation de la base de connaissance sans validation humaine.

DECISION_AUTHORITY = KX108_ONLY.
"""

_AUTHORITY_BYPASS_RESPONSE = """## Refus — Tentative de mutation d'autorité (KX108_ONLY)

Tentative de modification de decision_authority détectée.

DECISION_AUTHORITY est fixe = KX108_ONLY.
Brody ne peut pas modifier son autorité décisionnelle depuis cette couche.

Aucun ACT. Kernel immuable depuis cette interface.

DECISION_AUTHORITY = KX108_ONLY.
"""

_PROMPT_INJECTION_RESPONSE = """## Refus — Injection de prompt détectée (KX108_ONLY)

Tentative d'injection de prompt ou d'instruction système dans le message utilisateur.

Brody ignore les instructions système injectées via le champ message.
Les invariants X108 ne peuvent pas être contournés par instruction de prompt.

Aucun ACT. DECISION_AUTHORITY = KX108_ONLY.
"""

_COMPACT_SAFE_RESPONSE = """## Réponse structurelle (compact readonly, KX108_ONLY)

Brody est actif en mode readonly consultatif.

Cette réponse est générée en mode compact (dissipation minimale).
Aucun pipeline LLM complet. Aucun diagnostic approfondi.

Invariants actifs :
- DECISION_AUTHORITY = KX108_ONLY
- canonical_write=false
- graphiti_write=false
- neo4j_write=false
- emits_act=false
- allowed_to_act=false
"""


def _match(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text) for p in patterns)


def _detect_fastpath_type(msg: str) -> str | None:
    """Returns the first matching fastpath type, or None."""
    # Adversarial checked first — highest priority block
    if _match(msg, _ADVERSARIAL_PATTERNS):
        return "adversarial_fastpath"
    # Prompt injection — checked before other security patterns
    if _match(msg, _PROMPT_INJECTION_PATTERNS):
        return "prompt_injection_fastpath"
    # Authority bypass — change decision_authority
    if _match(msg, _AUTHORITY_BYPASS_PATTERNS):
        return "authority_bypass_fastpath"
    # Graphiti / Neo4j write attempts
    if _match(msg, _GRAPHITI_NEO4J_WRITE_PATTERNS):
        return "graphiti_neo4j_write_fastpath"
    # Human validation bypass
    if _match(msg, _HUMAN_VALIDATION_BYPASS_PATTERNS):
        return "human_validation_bypass_fastpath"
    # Secret / credential injection
    if _match(msg, _SECRET_INJECTION_PATTERNS):
        return "secret_injection_fastpath"
    # Memory boundary (sovereign rule)
    if _match(msg, _MEMORY_BOUNDARY_PATTERNS):
        return "memory_boundary_fastpath"
    # GPS / missing data / irreversible
    if _match(msg, _GPS_PATTERNS):
        return "gps_missing_data_fastpath"
    # CIC / metrics — checked AFTER memory_boundary to avoid overlap
    if _match(msg, _CIC_PATTERNS):
        return "cic_metrics_fastpath"
    return None


_RESPONSE_MAP: dict[str, str] = {
    "cic_metrics_fastpath": _CIC_RESPONSE,
    "gps_missing_data_fastpath": _GPS_RESPONSE,
    "adversarial_fastpath": _ADVERSARIAL_RESPONSE,
    "memory_boundary_fastpath": _MEMORY_BOUNDARY_RESPONSE,
    "secret_injection_fastpath": _SECRET_INJECTION_RESPONSE,
    "human_validation_bypass_fastpath": _HUMAN_VALIDATION_BYPASS_RESPONSE,
    "graphiti_neo4j_write_fastpath": _GRAPHITI_NEO4J_WRITE_RESPONSE,
    "authority_bypass_fastpath": _AUTHORITY_BYPASS_RESPONSE,
    "prompt_injection_fastpath": _PROMPT_INJECTION_RESPONSE,
    "compact_safe_fastpath": _COMPACT_SAFE_RESPONSE,
}

_CONFIDENCE_MAP: dict[str, float] = {
    "adversarial_fastpath": 0.97,
    "prompt_injection_fastpath": 0.96,
    "authority_bypass_fastpath": 0.96,
    "graphiti_neo4j_write_fastpath": 0.95,
    "human_validation_bypass_fastpath": 0.95,
    "secret_injection_fastpath": 0.93,
    "memory_boundary_fastpath": 0.90,
    "gps_missing_data_fastpath": 0.88,
    "cic_metrics_fastpath": 0.85,
    "compact_safe_fastpath": 0.80,
}


class BrodyV3FastpathEvaluator:
    """
    Evaluates whether a prompt qualifies for a fastpath response.
    No LLM. No IO. No ACT. DECISION_AUTHORITY=KX108_ONLY.
    advisory_only=True. Cannot decide. Cannot authorize.
    """

    def evaluate(
        self,
        message: str,
        micro_core: dict | None = None,
        balance_output: dict | None = None,
        point_cloud: dict | None = None,
        graphiti_guard: dict | None = None,
        context_budget: dict | None = None,
        compact_mode: bool = False,
    ) -> dict[str, Any]:
        """
        Returns fastpath_allowed + metadata + response_text if applicable.
        Never raises. Never writes. No IO.

        compact_mode=True : si aucun pattern de sécurité ne correspond,
        retourne compact_safe_fastpath (dissipation minimale).
        """
        mc = micro_core or {}
        msg_lower = (message or "").lower()

        # Never fastpath on adversarial micro_core signal WITHOUT adversarial pattern
        # (adversarial micro_core still gets adversarial_fastpath, not None)
        is_adv_mc = bool(mc.get("is_adversarial", False))
        if is_adv_mc:
            fp_type = "adversarial_fastpath"
        else:
            fp_type = _detect_fastpath_type(msg_lower)
            # compact_mode fallback : prompt générique en mode compact
            if fp_type is None and compact_mode:
                fp_type = "compact_safe_fastpath"

        if fp_type is None:
            return self._no_fastpath("NO_FASTPATH_TRIGGER")

        response_text = _RESPONSE_MAP[fp_type]
        confidence = _CONFIDENCE_MAP.get(fp_type, 0.80)

        return {
            "fastpath_allowed": True,
            "fastpath_type": fp_type,
            "response_text": response_text,
            "response_chars": len(response_text),
            "reason": f"FASTPATH_{fp_type.upper()}_TRIGGERED",
            "confidence": confidence,
            "decision_authority": "KX108_ONLY",
            "emits_act": False,
            "advisory_only": True,
            "no_canonical_write": True,
            "graphiti_queried": False,
            "pipeline_bypassed": True,
        }

    def _no_fastpath(self, reason: str) -> dict[str, Any]:
        return {
            "fastpath_allowed": False,
            "fastpath_type": None,
            "response_text": "",
            "response_chars": 0,
            "reason": reason,
            "confidence": 0.0,
            "decision_authority": "KX108_ONLY",
            "emits_act": False,
            "advisory_only": True,
            "no_canonical_write": True,
            "graphiti_queried": False,
            "pipeline_bypassed": False,
        }


# ── Module-level instance ─────────────────────────────────────────────────────

_EVALUATOR = BrodyV3FastpathEvaluator()


def evaluate_fastpath(
    message: str,
    micro_core: dict | None = None,
    balance_output: dict | None = None,
    point_cloud: dict | None = None,
    graphiti_guard: dict | None = None,
    context_budget: dict | None = None,
    compact_mode: bool = False,
) -> dict[str, Any]:
    """Convenience function. Never raises. No IO."""
    try:
        return _EVALUATOR.evaluate(
            message=message,
            micro_core=micro_core,
            balance_output=balance_output,
            point_cloud=point_cloud,
            graphiti_guard=graphiti_guard,
            context_budget=context_budget,
            compact_mode=compact_mode,
        )
    except Exception as e:
        return {
            "fastpath_allowed": False,
            "fastpath_type": None,
            "response_text": "",
            "response_chars": 0,
            "reason": f"FASTPATH_EXCEPTION: {e}",
            "confidence": 0.0,
            "decision_authority": "KX108_ONLY",
            "emits_act": False,
            "advisory_only": True,
            "no_canonical_write": True,
            "graphiti_queried": False,
            "pipeline_bypassed": False,
        }
