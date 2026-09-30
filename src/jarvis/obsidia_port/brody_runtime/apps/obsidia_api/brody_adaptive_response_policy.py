"""Brody adaptive response policy.

Phase 12J-B.

Readonly/advisory sizing layer for Brody answers.
It does not decide, act, write memory, write Graphiti, mutate the kernel, or mutate X108.

Purpose:
- expose why Brody chose a response size/density
- keep answer sizing auditable
- bind answer respiration to subject, intent, domain, risk, and sigma pressure
"""
from __future__ import annotations

from typing import Any
import re


BOUNDARY_REQUEST_TYPES = {"ACTION_OR_ACT_REQUEST", "MEMORY_WRITE_REQUEST"}


def _fold(text: str) -> str:
    return (text or "").lower()


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    low = _fold(text)
    return any(t in low for t in terms)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\wÀ-ÿ'-]+\b", text or ""))


def _explicit_size_hint(text: str) -> str:
    low = _fold(text)

    if _has_any(low, ("très court", "tres court", "fais court", "réponds court", "reponds court", "sans blabla", "en une phrase")):
        return "SHORT"

    if _has_any(low, ("détaille", "detaille", "détaillé", "detaille", "en détail", "en detail", "gros contexte", "explique en détail", "deep", "complet", "complète", "complete", "réponse complète", "reponse complete")):
        return "DEEP"

    if _has_any(low, ("résume", "resume", "synthèse", "synthese")):
        return "MEDIUM"

    return "AUTO"


def build_adaptive_response_policy(
    user_message: str,
    *,
    final_answer: str = "",
    voice_source: str = "",
    request_type: str = "PURE_RESPONSE",
    domain_raccord: dict[str, Any] | None = None,
    support_summary: dict[str, Any] | None = None,
    memory_chain: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a readonly sizing/density policy snapshot."""

    text = user_message or ""
    low = _fold(text)
    domain = domain_raccord if isinstance(domain_raccord, dict) else {}
    support = support_summary if isinstance(support_summary, dict) else {}
    chain = memory_chain if isinstance(memory_chain, dict) else {}

    domains = [str(x) for x in _as_list(domain.get("domains"))]
    risk_flags = [str(x) for x in _as_list(support.get("risk_flags"))]

    explicit_hint = _explicit_size_hint(text)
    user_words = _word_count(text)
    answer_words = _word_count(final_answer)

    boundary = (
        request_type in BOUNDARY_REQUEST_TYPES
        or any(f in risk_flags for f in (
            "action_request",
            "mutation_request",
            "write_request",
            "memory_write_request",
            "graphiti_write_request",
            "canon_promotion_request",
        ))
        or bool(domain.get("write_boundary_required"))
    )

    is_code = "CODE_DEBUG_GUIDANCE" in domains or "code_debug" in risk_flags
    is_arch = "ARCHITECTURE_EXPLANATION" in domains
    is_domain_deep = any(d in domains for d in ("THERMODYNAMICS", "ENERGY_SIGMA", "ANTI_MISMATCH", "COHERENCE"))
    is_multi = user_words >= 16 and len(domains) >= 2
    is_decision_boundary_question = _has_any(low, (
        "décider à la place de x108", "decider a la place de x108",
        "décider pour x108", "decider pour x108",
        "remplacer x108", "à la place de x108", "a la place de x108",
        "peux décider", "peut décider", "peux-tu décider", "tu peux décider",
    ))
    is_nonsense = (
        _has_any(low, ("florbnax", "banane", "arbre inversé bleu", "arbre inverse bleu"))
        or (user_words <= 14 and "TIME_TEMPORALITY" in domains and _has_any(low, ("?", "kernel", "x108")))
    ) and not is_code and not is_arch and not boundary
    has_memory = chain.get("material_quality") in ("USABLE_MATERIAL", "PARTIAL_MATERIAL")
    chain_status = str(chain.get("status") or "")

    if boundary or (is_decision_boundary_question and not is_arch):
        response_size = "BOUNDARY_COMPACT"
        density = "HIGH"
        context_need = "BOUNDARY"
        sigma_pressure = "HIGH"
        reason = "Boundary/risk request detected; response must stay compact, explicit, and non-actionable."
    elif is_code:
        response_size = "MEDIUM"
        density = "HIGH"
        context_need = "DEBUG"
        sigma_pressure = "MEDIUM"
        reason = "Code/debug intent requires operational steps without over-expanding."
    elif is_arch:
        response_size = "DEEP"
        density = "HIGH"
        context_need = "ARCHITECTURE"
        sigma_pressure = "MEDIUM"
        reason = "Architecture question requires component-level explanation."
    elif explicit_hint == "SHORT":
        response_size = "SHORT"
        density = "LOW"
        context_need = "NONE"
        sigma_pressure = "LOW"
        reason = "User explicitly requested a short answer."
    elif explicit_hint == "DEEP":
        response_size = "DEEP"
        density = "HIGH"
        context_need = "SUBJECT"
        sigma_pressure = "MEDIUM"
        reason = "User explicitly requested detail/deep context."
    elif is_domain_deep or is_multi:
        response_size = "DEEP"
        density = "HIGH"
        context_need = "DOMAIN"
        sigma_pressure = "MEDIUM"
        reason = "Multiple/domain concepts require contextual synthesis."
    elif is_nonsense:
        response_size = "SHORT"
        density = "LOW"
        context_need = "NONE"
        sigma_pressure = "LOW"
        reason = "Unclear/nonsense input should stay bounded and ask for a clearer anchor."
    elif has_memory:
        response_size = "MEDIUM"
        density = "NORMAL"
        context_need = "MEMORY"
        sigma_pressure = "MEDIUM"
        reason = "Memory material is available as readonly enrichment."
    elif chain_status in ("NO_MEMORY_RESULTS", "PARTIAL_QUERY_ONLY"):
        response_size = "SHORT"
        density = "LOW"
        context_need = "NONE"
        sigma_pressure = "LOW"
        reason = "No usable memory material; avoid simulating depth."
    else:
        response_size = "MEDIUM"
        density = "NORMAL"
        context_need = "SUBJECT"
        sigma_pressure = "LOW"
        reason = "Default structure-first answer with bounded context."

    if answer_words <= 55:
        observed_size = "SHORT"
    elif answer_words <= 180:
        observed_size = "MEDIUM"
    elif answer_words <= 380:
        observed_size = "DEEP"
    else:
        observed_size = "LONG"

    return {
        "source": "BRODY_ADAPTIVE_RESPONSE_POLICY_V1",
        "status": "ADAPTIVE_RESPONSE_POLICY_READY",
        "readonly": True,
        "advisory_only": True,
        "context_signal_only": True,
        "decision_authority": "KX108_ONLY",
        "response_size": response_size,
        "density": density,
        "context_need": context_need,
        "sigma_pressure": sigma_pressure,
        "reason": reason,
        "explicit_user_size_hint": explicit_hint,
        "observed_answer_size": observed_size,
        "observed_answer_words": answer_words,
        "input_words": user_words,
        "domains": domains,
        "risk_flags": risk_flags,
        "memory_material_quality": chain.get("material_quality"),
        "memory_chain_status": chain.get("status"),
        "boundary_detected": boundary,
        "can_decide": False,
        "can_act": False,
        "memory_write": False,
        "graphiti_write": False,
        "kernel_mutation": False,
        "x108_mutation": False,
    }
