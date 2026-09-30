from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Iterable

from .contracts import AgentVote, Domain, DomainAggregate, Layer


def _hash_ref(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _common(votes: list[AgentVote]):
    contradictions = []
    unknowns = []
    risk_flags = []
    evidence_refs = []
    for v in votes:
        contradictions.extend(v.contradictions)
        unknowns.extend(v.unknowns)
        risk_flags.extend(v.risk_flags)
        evidence_refs.append(_hash_ref(f"{v.agent_id}:{v.claim}:{v.proposed_verdict}"))
    return contradictions, unknowns, risk_flags, evidence_refs


def aggregate_trading(votes: Iterable[AgentVote]) -> DomainAggregate:
    votes = list(votes)
    scores = defaultdict(float)
    for v in votes:
        scores[v.proposed_verdict] += v.confidence
    buy = scores.get("BUY", 0.0)
    sell = scores.get("SELL", 0.0)
    hold = scores.get("HOLD", 0.0)
    market_verdict = "EXECUTE_LONG" if buy > max(sell, hold) else "EXECUTE_SHORT" if sell > max(buy, hold) else "REVIEW"
    confidence = round(min(0.98, max(buy, sell, hold) if sum(scores.values()) > 0 else 0.5), 2)
    contradictions, unknowns, risk_flags, evidence_refs = _common(votes)
    extra_metrics = {"buy_score": buy, "sell_score": sell, "hold_score": hold, "proof_ready": True, "deterministic": True}
    return DomainAggregate(Domain.TRADING, market_verdict, confidence, contradictions, unknowns, risk_flags, evidence_refs, agent_votes=votes, extra_metrics=extra_metrics)


def aggregate_bank(votes: Iterable[AgentVote]) -> DomainAggregate:
    votes = list(votes)
    scores = defaultdict(float)
    for v in votes:
        scores[v.proposed_verdict] += v.confidence
    auth = scores.get("AUTHORIZE", 0.0)
    analyze = scores.get("ANALYZE", 0.0)
    block = scores.get("BLOCK", 0.0)
    market_verdict = "BLOCK" if block > max(auth, analyze) else "AUTHORIZE" if auth > analyze else "ANALYZE"
    confidence = round(min(0.98, max(auth, analyze, block) if sum(scores.values()) > 0 else 0.5), 2)
    contradictions, unknowns, risk_flags, evidence_refs = _common(votes)
    extra_metrics = {"authorize_score": auth, "analyze_score": analyze, "block_score": block, "proof_ready": True, "deterministic": True}
    return DomainAggregate(Domain.BANK, market_verdict, confidence, contradictions, unknowns, risk_flags, evidence_refs, agent_votes=votes, extra_metrics=extra_metrics)


def aggregate_ecom(votes: Iterable[AgentVote]) -> DomainAggregate:
    votes = list(votes)
    scores = defaultdict(float)
    for v in votes:
        scores[v.proposed_verdict] += v.confidence
    pay = scores.get("PAY", 0.0)
    wait = scores.get("WAIT", 0.0)
    refuse = scores.get("REFUSE", 0.0)
    market_verdict = "REFUSE" if refuse > max(pay, wait) else "PAY" if pay > wait else "WAIT"
    confidence = round(min(0.98, max(pay, wait, refuse) if sum(scores.values()) > 0 else 0.5), 2)
    contradictions, unknowns, risk_flags, evidence_refs = _common(votes)
    extra_metrics = {"pay_score": pay, "wait_score": wait, "refuse_score": refuse, "proof_ready": True, "deterministic": True}
    return DomainAggregate(Domain.ECOM, market_verdict, confidence, contradictions, unknowns, risk_flags, evidence_refs, agent_votes=votes, extra_metrics=extra_metrics)


def aggregate_gps_defense_aviation(votes: Iterable[AgentVote]) -> DomainAggregate:
    votes = list(votes)
    scores = defaultdict(float)
    for v in votes:
        scores[v.proposed_verdict] += v.confidence

    valid = scores.get("TRAJECTORY_VALID", 0.0)
    recalc = scores.get("RECALC_TRAJECTORY", 0.0)
    degraded = scores.get("DEGRADED_NAVIGATION", 0.0)
    abort = scores.get("ABORT_TRAJECTORY", 0.0)

    confidence = round(min(0.98, max(valid, recalc, degraded, abort) if sum(scores.values()) > 0 else 0.5), 2)
    contradictions, unknowns, risk_flags, evidence_refs = _common(votes)

    truth_penalty = 0.0
    if any(u in unknowns for u in ["GPS_MISSING", "INERTIAL_MISSING", "RADIO_MISSING"]):
        truth_penalty += 0.35
    if "TIME_SKEW_ACTIVE" in unknowns or "TEMPORAL_ALIGNMENT_UNCERTAIN" in unknowns:
        truth_penalty += 0.22
    if "BROWNOUT_ACTIVE" in unknowns or "POWER_STATE_UNCERTAIN" in unknowns:
        truth_penalty += 0.28
    if "SOURCE_CONFLICT" in contradictions:
        truth_penalty += 0.45
    if "ATTESTATION_NOT_READY" in unknowns:
        truth_penalty += 0.10

    sigma_score = confidence
    truth_score = max(0.0, min(1.0, confidence - truth_penalty))
    mismatch_gap = abs(sigma_score - truth_score)

    if "SOURCE_CONFLICT" in contradictions or abort > max(valid, recalc, degraded):
        market_verdict = "ABORT_TRAJECTORY"
    elif "BROWNOUT" in risk_flags or "BROWNOUT_ACTIVE" in unknowns or "POWER_STATE_UNCERTAIN" in unknowns:
        market_verdict = "DEGRADED_NAVIGATION"
    elif (
        "TIME_SKEW" in risk_flags
        or "TIME_SKEW_ACTIVE" in unknowns
        or "TEMPORAL_ALIGNMENT_UNCERTAIN" in unknowns
        or any(u in unknowns for u in ["GPS_MISSING", "INERTIAL_MISSING", "RADIO_MISSING"])
        or mismatch_gap >= 0.22
    ):
        market_verdict = "RECALC_TRAJECTORY"
    else:
        market_verdict = "TRAJECTORY_VALID"

    extra_metrics = {
        "trajectory_valid_score": valid,
        "recalc_score": recalc,
        "degraded_score": degraded,
        "abort_score": abort,
        "truth_score": truth_score,
        "sigma_score": sigma_score,
        "mismatch_gap": mismatch_gap,
        "proof_ready": True,
        "deterministic": True,
    }

    return DomainAggregate(
        Domain.GPS_DEFENSE_AVIATION,
        market_verdict,
        confidence,
        contradictions,
        unknowns,
        risk_flags,
        evidence_refs,
        agent_votes=votes,
        extra_metrics=extra_metrics,
    )


def aggregate_tooling_build(votes: Iterable[AgentVote]) -> DomainAggregate:
    """Agrégation formelle pour le domaine tooling_build (aggregate4 : 4 agents requis).

    Pondération par couche : KERNEL (layer=6) → ×1.5 ; autres → ×1.0.
    market_verdict souverain :
      BUILD_BLOCK  si ≥1 contradiction
      BUILD_HOLD   si ≥1 unknown (et 0 contradiction)
      READY_FOR_COMMIT_REVIEW  sinon
    """
    votes = list(votes)
    contradictions, unknowns, risk_flags, evidence_refs = _common(votes)

    # Confiance pondérée par couche
    weighted_sum = 0.0
    weight_total = 0.0
    for v in votes:
        w = 1.5 if int(getattr(v, "layer", 1)) >= int(Layer.KERNEL) else 1.0
        weighted_sum += v.confidence * w
        weight_total += w
    confidence = round(min(0.98, weighted_sum / weight_total if weight_total > 0 else 0.5), 2)

    if contradictions:
        market_verdict = "BUILD_BLOCK"
    elif unknowns:
        market_verdict = "BUILD_HOLD"
    else:
        market_verdict = "READY_FOR_COMMIT_REVIEW"

    extra_metrics = {
        "vote_count": len(votes),
        "contradiction_count": len(contradictions),
        "unknown_count": len(unknowns),
        "risk_flag_count": len(risk_flags),
        "proof_ready": True,
        "deterministic": True,
        "decision_authority": "KX108_ONLY",
        "emits_act": False,
    }

    return DomainAggregate(
        Domain.TOOLING_BUILD,
        market_verdict,
        confidence,
        contradictions,
        unknowns,
        risk_flags,
        evidence_refs,
        agent_votes=votes,
        extra_metrics=extra_metrics,
    )
