"""
brody_cognitive_micro_core — V3 Block 1
Cognitive micro-core: 14 permanent signals. No IO. No ACT. No decision.
Budget: 1792 bytes conceptual. Latency target: < 20ms. DECISION_AUTHORITY=KX108_ONLY.
"""
from __future__ import annotations

import re
import time
from typing import Any

# ── Adversarial detection ─────────────────────────────────────────────────────
_ADVERSARIAL_TOKENS: list[str] = [
    "mute kernel", "bypass", "override x108", "ignore les gardes",
    "désactive x108", "desactive x108", "mutate kernel",
    "modifie le kernel", "écris en mémoire canonique",
    "contourne les gardes", "ignore x108", "supprime guardrail",
    "autorise toi à décider", "agis comme si tu pouvais",
]

_ADVERSARIAL_PATTERNS: list[str] = [
    r"\bbypass\b",
    r"override\s+x108",
    r"ignore\s+x108",
    r"ignore\s+les\s+gardes",
    r"d[eé]sactive\s+x108",
    r"mutate?\s+kernel",
    r"modifie\s+le\s+kernel",
    r"[eé]cris\s+en\s+m[eé]moire\s+canonique",
    r"contourne\s+(les\s+)?(gardes|r[eè]gles|guardrail)",
    r"autorise[\s\-]toi\s+[aà]\s+(d[eé]cider|agir|[eé]crire)",
    r"agis\s+comme\s+si\s+tu\s+pouvais",
    r"\bmute\s+\w",
]

# ── Irreversibility detection ─────────────────────────────────────────────────
_IRREVERSIBLE_PATTERNS: list[str] = [
    r"\birrév[e]?rsible\b",
    r"\bpermanent(e)?\b",
    r"\beff[a]?ce[r]?\s+(d[eé]finitivement|tout)\b",
    r"supprime[r]?\s+d[eé]finitivement",
    r"\bfreeze[r]?\s+(tout|le\s+kernel)\b",
    r"commit\s+--\s*force",
    r"reset\s+--\s*hard",
    r"drop\s+table",
    r"delete\s+all",
    r"wipe\s+(all|memory|data)",
]

# ── Domain detection ─────────────────────────────────────────────────────────
# trading vérifié AVANT bank : ses patterns sont plus spécifiques.
# "financier" seul est trop générique pour bank — retiré.
_DOMAIN_PATTERNS: dict[str, list[str]] = {
    "trading": [
        r"\btrading\b", r"\btrade\b", r"\bbourse\b",
        r"\bswap\b", r"\bposition\s+trading\b",
        r"\bactif\s+financier\b", r"\bcarnet\s+d[e']ordres?\b",
        r"\bmarché\s+financier\b",
    ],
    "bank": [
        r"\bbank\b", r"\bbanqu[e]?\b", r"\bbancair[e]?\b",
        r"\bcr[eé]dit\b", r"\bfinance\b",
        r"\bcompte\s+bancaire\b", r"\bvirement\b",
    ],
    "gps_defense_aviation": [
        r"\bgps\b", r"\bgéolocalisation\b", r"\bgeolocalisation\b",
        r"\bnavigation\b", r"\baviation\b", r"\bd[eé]fense\b",
        r"\bcoordonnée[s]?\b", r"\btrajectoire\s+vol\b",
    ],
}

# ── Semantic patterns ─────────────────────────────────────────────────────────
_SYMBOLIC_PATTERNS: list[str] = [
    r"\bsymbolisme\b", r"\bencodage\s+symbolique\b",
    r"\bsymbole\s+cic\b", r"\blecture\s+symbolique\b",
    r"\bm[eé]taphore\s+cic\b", r"\brepr[eé]sentation\s+symbolique\b",
]

_FRACTAL_PATTERNS: list[str] = [
    r"\bfractal[e]?\b", r"\bauto.similarit[eé]\b",
    r"\bstructure\s+fractale\b", r"\br[eé]cursif\b",
    r"\bmotif\s+r[eé]p[eé]t[eé]\b", r"\bauto.r[eé]f[eé]rence\b",
]

_CAUSAL_PATTERNS: list[str] = [
    r"\bpourquoi\b", r"\bcause\b", r"\borigine\b",
    r"\bremonte\b", r"\braisonnement\s+causal\b",
    r"\bcontrainte\s+initiale\b", r"\bd'o[uù]\s+vient\b",
]

_MEMORY_PATTERNS: list[str] = [
    r"\bm[eé]moire\b",
    r"\bcandidats?\b", r"\bmes\s+sources\b", r"\bhistoriques?\b",
    r"\bbrody\s+(memory|doc)\b", r"\bsession\s+pr[eé]c[eé]dents?\b",
]

_MEMORY_RECALL_VERB_PATTERNS: list[str] = [
    r"\brappell(?:e|es|er|ez)\b",
    r"\breprends?\b",
    r"\bretrouve(?:r)?\b",
    r"\bsouviens(?:[\s\-]+toi)?\b",
    r"\br[eé]cup[eè]re(?:r|z)?\b",
    r"\bremember\b",
    r"\brecall\b",
    r"\bretrieve\b",
]

_MEMORY_RECALL_CONTEXT_PATTERNS: list[str] = [
    r"\bm[eé]moire\b",
    r"\bhistoriques?\b",
    r"\bsession\s+pr[eé]c[eé]dent(?:e|es|s)?\b",
    r"\bcontexte\s+pr[eé]c[eé]dent(?:e|es|s)?\b",
    r"\bconversation\s+pr[eé]c[eé]dent(?:e|es|s)?\b",
    r"\bm[eé]moris[eé](?:e|es|s|r)?\b",
    r"\bstored\s+(?:memory|context)\b",
    r"\bprevious\s+(?:session|memory|context|conversation)\b",
]

_EXPLICIT_MEMORY_RECALL_SCORE = 0.85

# Named internal project entities.
# Mentioning one is not an explicit recall command, but it means
# project-local readonly context can be materially relevant.
_PROJECT_CONTEXT_PATTERNS: list[str] = [
    r"\bobsidia\b",
    r"\bbrody\b",
    r"\bx[-_ ]?108\b",
    r"\bkx108\b",
]

_PROJECT_CONTEXT_MEMORY_SCORE = 0.80

_BIO_PATTERNS: list[str] = [
    r"\bpiste\b", r"\bpistage\b", r"\binstinct\b", r"\bterrain\b",
    r"[eé]conomie\s+d[e']\s*[eé]nergie", r"\bstigmergie\b",
    r"\bessaim\b", r"\bmeute\b", r"\bhom[eé]ostasie\b",
    r"\bchemin\s+mort\b", r"\bfausse\s+piste\b", r"\bsurvie\b",
    r"\bnavigation\s+rapide\b", r"\baller\s+plus\s+vite\b",
    r"\bpiste\s+coh[eé]rente\b",
]

_PROJECTION_PATTERNS: list[str] = [
    r"\bprojection\b", r"\bsc[eé]nario\b", r"\bhypoth[eè]se\b",
    r"\banticiper\b", r"\bsi\s+x\s+alors\b", r"\bestimer\b",
    r"\bprojeter\b",
]

_REFLEX_PATTERNS: list[str] = [
    r"\br[eé]flexe\b", r"\banti.d[eé]rive\b", r"\bposture\b",
    r"\bsignal\s+r[eé]flexe\b", r"\bd[eé]rive\b", r"\brecalibr\b",
]

_TEMPORAL_PATTERNS: list[str] = [
    r"\bpass[eé]\b", r"\bpr[eé]sent\b", r"\bfutur\b",
    r"\bchronologie\b", r"\btempor[e]?l\b", r"\bs[eé]quence\b",
]

_PROOF_PATTERNS: list[str] = [
    r"\bpreuve\b", r"\bproof\b", r"\blean\b", r"\btla\b",
    r"\bmerkle\b", r"\bos3\b", r"\bvérif\b",
]

_PREDICTION_PATTERNS: list[str] = [
    r"\bpr[eé]dis\b", r"\bpr[eé]dit\b", r"\bpr[eé]voir\s+exactement\b",
    r"\bcertitude\s+absolue\b", r"\bje\s+sais\s+avec\s+certitude\b",
]

# ── Weak signal map ───────────────────────────────────────────────────────────
_WEAK_SIGNAL_MAP: dict[str, str] = {
    "piste": "bio_animal_coherence_layer",
    "pistage": "bio_animal_coherence_layer",
    "stigmergie": "bio_animal_coherence_layer",
    "ltcu": "LCTU_LTCU_layer",
    "lctu": "LCTU_LTCU_layer",
    "fractal": "fractal_layer",
    "morse": "universal_language_layer",
    "réciproque": "reciprocal_layer",
    "reciprocite": "reciprocal_layer",
    "interlanguage": "universal_language_layer",
    "symbolisme": "symbolic_layer",
    "encodage symbolique": "symbolic_layer",
    "os reverse": "OS_reverse_layer",
    "remonte la cause": "OS_reverse_layer",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _match(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text) for p in patterns)


def _count(text: str, patterns: list[str]) -> int:
    return sum(1 for p in patterns if re.search(p, text))


def _detect_explicit_memory_recall(msg_lower: str) -> bool:
    """
    Detect an explicit user intent to retrieve prior context.

    This is intentionally conjunctive:
      recall verb AND memory/history/previous-context target.

    A mere mention of "memory" must not activate retrieval.
    """
    has_recall_action = _match(
        msg_lower,
        _MEMORY_RECALL_VERB_PATTERNS,
    )

    has_recall_target = _match(
        msg_lower,
        _MEMORY_RECALL_CONTEXT_PATTERNS,
    )

    return bool(
        has_recall_action
        and has_recall_target
    )


def _detect_adversarial(msg_lower: str) -> tuple[bool, str]:
    for p in _ADVERSARIAL_PATTERNS:
        if re.search(p, msg_lower):
            return True, "ADVERSARIAL_PATTERN_DETECTED"
    for tok in _ADVERSARIAL_TOKENS:
        if tok in msg_lower:
            return True, "ADVERSARIAL_TOKEN_DETECTED"
    return False, "OK"


def _detect_irreversible(msg_lower: str) -> tuple[bool, float]:
    count = _count(msg_lower, _IRREVERSIBLE_PATTERNS)
    score = min(1.0, count * 0.5)
    return count > 0, round(score, 3)


def _detect_domain(msg_lower: str) -> str | None:
    for domain, patterns in _DOMAIN_PATTERNS.items():
        if _match(msg_lower, patterns):
            return domain
    return None


def _detect_weak_signals(msg_lower: str) -> list[str]:
    found: list[str] = []
    for token, layer in _WEAK_SIGNAL_MAP.items():
        if token in msg_lower and layer not in found:
            found.append(layer)
    return found


def _bio_animal_signal(
    msg_lower: str,
    is_adversarial: bool,
    memory_count: int,
    explicit_memory_recall: bool = False,
    project_context_relevant: bool = False,
) -> dict[str, Any]:
    bio_count = _count(msg_lower, _BIO_PATTERNS)
    weak_signals = _detect_weak_signals(msg_lower)

    path_coherence: float = 0.5
    terrain_fit: float = 0.6
    trace_following: float = 0.3
    energy_cost: int = 1792

    instinct_signal: str | None = None
    if is_adversarial:
        instinct_signal = "danger_adversarial"
        path_coherence = 0.2
        terrain_fit = 0.3

    dead_path: list[str] = []
    if is_adversarial:
        dead_path = ["memory_selector_layer", "symbolic_layer", "fractal_layer"]

    survival_risk = is_adversarial or _match(msg_lower, _IRREVERSIBLE_PATTERNS)

    if bio_count > 0:
        path_coherence = min(0.9, path_coherence + bio_count * 0.1)
        trace_following = min(0.8, trace_following + bio_count * 0.15)

    adaptive_route: list[str] = ["authority_layer", "cic_core_layer"]
    if bio_count > 0:
        adaptive_route.append("bio_animal_coherence_layer")

    memory_relevance = min(
        1.0,
        memory_count * 0.25,
    )

    # Explicit retrieval intent is structurally stronger than
    # independent lexical mentions. It does not authorize anything:
    # it only raises the readonly memory-relevance signal.
    if explicit_memory_recall:
        memory_relevance = max(
            memory_relevance,
            _EXPLICIT_MEMORY_RECALL_SCORE,
        )

    if project_context_relevant:
        memory_relevance = max(
            memory_relevance,
            _PROJECT_CONTEXT_MEMORY_SCORE,
        )

    return {
        "path_coherence_score": round(path_coherence, 3),
        "instinct_signal": instinct_signal,
        "terrain_fit_score": round(terrain_fit, 3),
        "energy_cost_estimate": energy_cost,
        "dead_path_detection": dead_path,
        "weak_signal_detection": list(dict.fromkeys(weak_signals)),
        "trace_following_score": round(trace_following, 3),
        "survival_risk_flag": survival_risk,
        "adaptive_route_suggestion": adaptive_route,
        "memory_relevance_signal": round(
            memory_relevance,
            3,
        ),
        "explicit_memory_recall": bool(
            explicit_memory_recall
        ),
        "project_context_relevant": bool(
            project_context_relevant
        ),
    }


# ── Public API ────────────────────────────────────────────────────────────────

def run_micro_core(
    message: str,
    session_id: str = "",
    language: str = "fr",
) -> dict[str, Any]:
    """
    Run the cognitive micro-core. Returns 14 permanent signals.
    No IO, no external API, no decision, no ACT.
    DECISION_AUTHORITY=KX108_ONLY.
    """
    t0 = time.monotonic()
    msg_lower = (message or "").lower()

    # ── 1. Authority signal ───────────────────────────────────────────────────
    is_adversarial, authority_verdict = _detect_adversarial(msg_lower)
    authority_signal: dict[str, Any] = {
        "is_adversarial": is_adversarial,
        "authority_verdict": authority_verdict,
        "readonly_confirmed": True,
        "allowed_to_decide": False,
        "allowed_to_act": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
    }

    # ── 2. CIC compact signal ─────────────────────────────────────────────────
    cic_signal: dict[str, Any] = {
        "priority_chain": "Invariant > Réversibilité > Score > Projection",
        "active_rules": [
            "score_cannot_authorize_what_invariant_forbids",
            "memory_not_sovereign",
            "projection_not_prediction",
            "critical_missing_data_holds",
        ],
        "cic_compact_status": "ACTIVE",
        "decision_authority": "KX108_ONLY",
    }

    # ── 3. Invariant signal ───────────────────────────────────────────────────
    invariant_signal: dict[str, Any] = {
        "invariant_1": "Score ne peut pas autoriser ce qu'un invariant interdit",
        "invariant_2": "Mémoire n'est pas souveraine",
        "invariant_3": "Projection n'est pas une prédiction",
        "invariant_4": "Donnée manquante critique sur action irréversible → HOLD/BLOCK/REVIEW",
        "all_active": True,
        "overridable": False,
    }

    # ── 4. Reversibility signal ───────────────────────────────────────────────
    is_irreversible, irrev_score = _detect_irreversible(msg_lower)
    hold_required = irrev_score >= 0.3
    reversibility_signal: dict[str, Any] = {
        "is_irreversible": is_irreversible,
        "reversibility_score": round(1.0 - irrev_score, 3),
        "irreversibility_score": irrev_score,
        "hold_required": hold_required,
    }

    # ── 5. Projection not prediction signal ───────────────────────────────────
    has_projection = _match(msg_lower, _PROJECTION_PATTERNS)
    has_prediction_claim = _match(msg_lower, _PREDICTION_PATTERNS)
    projection_not_prediction_signal: dict[str, Any] = {
        "is_prediction_claim": has_prediction_claim,
        "projection_allowed": has_projection and not has_prediction_claim,
        "projection_detected": has_projection,
    }

    # ── 6. Memory not sovereign ───────────────────────────────────────────────
    memory_not_sovereign_signal: dict[str, Any] = {
        "memory_can_override": False,
        "memory_readonly": True,
        "canonical_write_allowed": False,
        "decision_authority": "KX108_ONLY",
    }

    # ── 7. Bio animal signal ──────────────────────────────────────────────────
    memory_count = _count(
        msg_lower,
        _MEMORY_PATTERNS,
    )

    explicit_memory_recall = (
        _detect_explicit_memory_recall(
            msg_lower
        )
    )

    project_context_relevant = _match(
        msg_lower,
        _PROJECT_CONTEXT_PATTERNS,
    )

    bio_animal_signal = _bio_animal_signal(
        msg_lower,
        is_adversarial,
        memory_count,
        explicit_memory_recall,
        project_context_relevant,
    )

    # ── 8. Balance signal (stub — full in BrodyBalanceEngine) ─────────────────
    balance_signal: dict[str, Any] = {
        "status": "MICRO_CORE_STUB",
        "note": "Full balance computed by brody_balance_engine.BrodyBalanceEngine",
        "dominant_balance": None,
        "layers_to_activate": [],
        "layers_to_avoid": bio_animal_signal.get("dead_path_detection", []),
        "balance_risk_level": 1.0 if is_adversarial else 0.2,
        "estimated_budget_bytes": bio_animal_signal.get("energy_cost_estimate", 1792),
    }

    # ── 9. Symbolic signal ────────────────────────────────────────────────────
    sym_count = _count(msg_lower, _SYMBOLIC_PATTERNS)
    symbolic_density = min(1.0, sym_count * 0.35)
    symbolic_signal: dict[str, Any] = {
        "symbolic_density": round(symbolic_density, 3),
        "symbolic_layer_recommended": symbolic_density > 0.3,
    }

    # ── 10. Fractal signal ────────────────────────────────────────────────────
    fractal_detected = _match(msg_lower, _FRACTAL_PATTERNS)
    fractal_signal: dict[str, Any] = {
        "fractal_pattern_detected": fractal_detected,
        "fractal_scale": "multi_scale" if fractal_detected else None,
    }

    # ── 11. Reflex signal ─────────────────────────────────────────────────────
    reflex_triggered = is_adversarial or _match(msg_lower, _REFLEX_PATTERNS)
    posture = "ALERT" if is_adversarial else ("ACTIVE" if reflex_triggered else "NOMINAL")
    reflex_signal: dict[str, Any] = {
        "reflex_triggered": reflex_triggered,
        "posture_status": posture,
        "anti_drift_active": reflex_triggered,
    }

    # ── 12. Reciprocal signal (stub) ──────────────────────────────────────────
    reciprocal_signal: dict[str, Any] = {
        "feedback_pending": False,
        "correction_candidate": None,
        "status": "STUB_NOT_IMPLEMENTED",
    }

    # ── 13. OS reverse signal ─────────────────────────────────────────────────
    causal_count = _count(msg_lower, _CAUSAL_PATTERNS)
    causal_depth = min(1.0, causal_count / 3.0)
    os_reverse_signal: dict[str, Any] = {
        "causal_depth_score": round(causal_depth, 3),
        "os_reverse_recommended": causal_depth > 0.3,
        "non_decision": True,
        "qui": "BRODY_MICRO_CORE",
        "pourquoi": "CAUSAL_DEPTH_SCAN",
        "preuve": "LOCAL_KEYWORD_ANALYSIS",
        "dominant_trees": [],
    }

    # ── 14. Point cloud ready signal ─────────────────────────────────────────
    point_cloud_ready_signal: dict[str, Any] = {
        "ready": True,
        "dimensions": 21,
        "axes_computed": list(range(1, 22)),
        "source": "brody_point_cloud_21d_selector",
    }

    elapsed_ms = (time.monotonic() - t0) * 1000

    domain = _detect_domain(msg_lower)
    temporal_detected = _match(msg_lower, _TEMPORAL_PATTERNS)
    proof_detected = _match(msg_lower, _PROOF_PATTERNS)

    return {
        "micro_core_version": "V3_BLOCK_1",
        "signals_count": 14,
        "latency_ms": round(elapsed_ms, 3),
        "budget_bytes": 1792,
        "io_external": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "advisory_only": True,
        # ── 14 signals ────────────────────────────────────────────────────────
        "authority_signal": authority_signal,
        "cic_signal": cic_signal,
        "invariant_signal": invariant_signal,
        "reversibility_signal": reversibility_signal,
        "projection_not_prediction_signal": projection_not_prediction_signal,
        "memory_not_sovereign_signal": memory_not_sovereign_signal,
        "bio_animal_signal": bio_animal_signal,
        "balance_signal": balance_signal,
        "symbolic_signal": symbolic_signal,
        "fractal_signal": fractal_signal,
        "reflex_signal": reflex_signal,
        "reciprocal_signal": reciprocal_signal,
        "os_reverse_signal": os_reverse_signal,
        "point_cloud_ready_signal": point_cloud_ready_signal,
        # ── summary ──────────────────────────────────────────────────────────
        "is_adversarial": is_adversarial,
        "survival_risk_flag": bio_animal_signal["survival_risk_flag"],
        "hold_required": hold_required,
        "domain_detected": domain,
        "temporal_detected": temporal_detected,
        "proof_detected": proof_detected,
        "memory_relevant": bool(
            memory_count > 0
            or explicit_memory_recall
            or project_context_relevant
        ),
    }
