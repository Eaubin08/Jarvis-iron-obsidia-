from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from .contracts import CanonicalDecisionEnvelope, DomainAggregate, Severity, X108Gate, SourceTag


@dataclass
class GuardConfig:
    min_confidence_allow: float = 0.72
    hold_confidence_floor: float = 0.45
    max_unknowns_before_hold: int = 1
    max_contradictions_before_block: int = 2




# --- P3I_MAX_CONSENSUS_SURFACE_HELPERS_START ---
def _x108_safe_attr(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _x108_safe_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _x108_severity_value(value):
    try:
        return value.value
    except Exception:
        return str(value) if value is not None else None




def _x108_json_scalar(value):
    """
    Convertit les Enum / Domain / Severity / objets simples en valeurs JSON-safe.
    Ne modifie aucune d?cision.
    """
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if hasattr(value, "value"):
        try:
            inner = value.value
            if isinstance(inner, (str, int, float, bool)):
                return inner
        except Exception:
            pass

    if hasattr(value, "name"):
        try:
            return str(value.name)
        except Exception:
            pass

    return str(value)


def _x108_is_domain_like(value):
    s = str(value or "").upper()
    return s.startswith("DOMAIN.") or s in {
        "BANK",
        "TRADING",
        "ECOM",
        "GPS_DEFENSE_AVIATION",
        "GPS",
        "AVIATION",
    }


def _x108_is_trusted_act_source(layer_raw) -> bool:
    """
    True only if vote layer is KERNEL (6) or higher (PROOF=7, SCELLAGE=8).
    Votes from OBSERVATION/INTERPRETATION/CONTRADICTION/PERIPHERAL/SIGMA
    are NOT trusted to produce ACT on the aggregate4 proof surface.
    DECISION_AUTHORITY=KX108_ONLY  ACT=NO  PROOF_SURFACE_ONLY
    """
    if layer_raw is None:
        return False
    try:
        layer_int = int(layer_raw)
        return layer_int >= 6
    except (ValueError, TypeError):
        pass
    s = str(layer_raw).upper()
    return s in ("KERNEL", "PROOF", "SCELLAGE", "6", "7", "8")


def _x108_pick_vote(raw_vote, proposed_verdict):
    """
    Certains agents legacy passent Domain en deuxi?me argument.
    Dans ce cas, Domain peut se retrouver dans vote.
    On ne l'interpr?te pas comme d?cision.
    """
    candidates = [raw_vote, proposed_verdict, "HOLD"]

    for c in candidates:
        if c is None:
            continue
        if _x108_is_domain_like(c):
            continue
        normalized = _x108_normalize_vote_for_aggregate4(c)
        if normalized not in ("ERROR", "UNKNOWN"):
            return c

    return "HOLD"


def _x108_normalize_vote_for_aggregate4(value):
    """
    Normalisation strictement destin?e ? la surface de preuve.
    Ne modifie pas la d?cision Kernel/X108.
    """
    s = str(value or "").upper().strip()

    if s in ("ACT", "ALLOW", "AUTHORIZE", "AUTHORIZED", "VALID", "PASS", "PAY", "TRAJECTORY_VALID"):
        return "ACT"

    if s in ("HOLD", "ANALYZE", "REVIEW", "RECALC", "RECALC_TRAJECTORY", "WAIT", "DEFER"):
        return "HOLD"

    if s in ("BLOCK", "DENY", "REFUSE", "ABORT", "ABORT_TRAJECTORY", "REJECT"):
        return "BLOCK"

    if s in ("ERROR", "UNKNOWN", "", "NONE"):
        return "ERROR"

    return "UNKNOWN"


def _x108_count_values(values):
    counts = {}
    for v in values:
        key = str(v or "UNKNOWN")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _x108_agent_vote_detail(v):
    raw_vote_raw = _x108_safe_attr(v, "vote", None)
    proposed_verdict_raw = _x108_safe_attr(v, "proposed_verdict", None)
    layer_raw = _x108_safe_attr(v, "layer", None)
    selected_vote_raw = _x108_pick_vote(raw_vote_raw, proposed_verdict_raw)

    raw_vote = _x108_json_scalar(raw_vote_raw)
    proposed_verdict = _x108_json_scalar(proposed_verdict_raw)
    selected_vote = _x108_json_scalar(selected_vote_raw)

    # V3: Validate ACT source trust before exposing on aggregate4 surface.
    # ACT-class votes from non-kernel layers are blocked; fallback is HOLD.
    # DECISION_AUTHORITY=KX108_ONLY  ACT=NO  PROOF_SURFACE_ONLY
    _normalized_raw = _x108_normalize_vote_for_aggregate4(selected_vote)
    _is_trusted = _x108_is_trusted_act_source(layer_raw)
    _is_domain_rejected = (
        _x108_is_domain_like(raw_vote_raw) or _x108_is_domain_like(proposed_verdict_raw)
    )

    if _normalized_raw == "ACT" and not _is_trusted:
        _normalized_final = "HOLD"
        _false_act_blocked = True
        _invalid_legacy = True
    else:
        _normalized_final = _normalized_raw
        _false_act_blocked = False
        _invalid_legacy = False

    detail = {
        "agent_id": _x108_json_scalar(_x108_safe_attr(v, "agent_id", "UNKNOWN_AGENT")),
        "vote": raw_vote,
        "proposed_verdict": proposed_verdict,
        "selected_vote": selected_vote,
        "normalized_vote_for_aggregate4": _normalized_final,
        "confidence": _x108_safe_attr(v, "confidence", None),
        "domain": _x108_json_scalar(_x108_safe_attr(v, "domain", "unknown")),
        "layer": _x108_json_scalar(layer_raw),
        "claim": _x108_json_scalar(_x108_safe_attr(v, "claim", None)),
        "severity_hint": _x108_json_scalar(_x108_safe_attr(v, "severity_hint", None)),
        "contradictions": [_x108_json_scalar(x) for x in _x108_safe_list(_x108_safe_attr(v, "contradictions", []))],
        "unknowns": [_x108_json_scalar(x) for x in _x108_safe_list(_x108_safe_attr(v, "unknowns", []))],
        "risk_flags": [_x108_json_scalar(x) for x in _x108_safe_list(_x108_safe_attr(v, "risk_flags", []))],
        "evidence_refs": [_x108_json_scalar(x) for x in _x108_safe_list(_x108_safe_attr(v, "evidence_refs", []))],
        "serialization_note": "json_safe_p3i7",
        # V3 audit flags — aggregate4 surface hardening
        "aggregate4_invalid_legacy_vote": _invalid_legacy,
        "aggregate4_domain_enum_rejected": _is_domain_rejected,
        "aggregate4_false_act_surface_blocked": _false_act_blocked,
        "aggregate4_selected_vote_source": "trusted_kernel" if _is_trusted else "non_trusted_peripheral",
        "aggregate4_proof_surface_only": True,
        "aggregate4_does_not_authorize_action": True,
    }

    try:
        detail["confidence"] = float(detail["confidence"]) if detail["confidence"] is not None else None
    except Exception:
        detail["confidence"] = None

    return detail


def _x108_aggregate4_result(normalized_votes):
    counts = _x108_count_values(normalized_votes)

    for decision in ("ACT", "HOLD", "BLOCK"):
        if counts.get(decision, 0) >= 3:
            return {
                "final_decision": decision,
                "votes": counts,
                "supermajority": True,
                "threshold": "3/4",
                "fail_closed": False,
                "reason": "3/4 supermajority reached",
            }

    return {
        "final_decision": "BLOCK",
        "votes": counts,
        "supermajority": False,
        "threshold": "3/4",
        "fail_closed": True,
        "reason": "No 3/4 supermajority ? fail-closed applies",
    }


def _x108_consensus_surface(agent_votes):
    details = [_x108_agent_vote_detail(v) for v in _x108_safe_list(agent_votes)]
    normalized_votes = [d["normalized_vote_for_aggregate4"] for d in details]
    observed_count = len(details)

    raw_vote_counts = _x108_count_values([d.get("vote") for d in details])
    proposed_verdict_counts = _x108_count_values([d.get("proposed_verdict") for d in details])
    normalized_vote_counts = _x108_count_values(normalized_votes)

    observation = {
        "display_only": True,
        "authority": "NONE",
        "warning": "Observation ratio is not a Kernel decision and not a Lean aggregate4 proof.",
        "threshold_ratio": 0.75,
        "voters_observed": observed_count,
        "max_decision": None,
        "max_count": 0,
        "ratio": None,
        "ratio_threshold_met": False,
    }

    if observed_count:
        best_decision, best_count = max(normalized_vote_counts.items(), key=lambda item: item[1])
        observation.update({
            "max_decision": best_decision,
            "max_count": best_count,
            "ratio": round(best_count / observed_count, 4),
            "ratio_threshold_met": (best_count / observed_count) >= 0.75,
        })

    consensus = {
        "rule": "aggregate4",
        "threshold": "3/4",
        "voters_expected": 4,
        "supermajority_min": 3,
        "source": "P3G_MAX_CONSENSUS_SCORE_CONTRACT",
        "proof_scope": "aggregate4 over exactly 4 voters",
        "authority": "PROOF_SURFACE_ONLY",
        "does_not_override_x108_gate": True,
        "does_not_authorize_action": True,
        "agent_vote_details_exposed": True,
        "agent_vote_source": "AgentVote.vote / AgentVote.proposed_verdict / AgentVote.confidence",
        "voters_observed": observed_count,
        "raw_vote_counts": raw_vote_counts,
        "proposed_verdict_counts": proposed_verdict_counts,
        "normalized_vote_counts": normalized_vote_counts,
        "observation_ratio": observation,
    }

    if observed_count == 4:
        formal_result = _x108_aggregate4_result(normalized_votes)
        consensus.update({
            "formal_result_status": "APPLIED_EXACTLY_4_VOTERS",
            "formal_result": formal_result,
        })
    else:
        consensus.update({
            "formal_result_status": "NOT_APPLIED_REQUIRES_4_VOTERS",
            "formal_result": None,
            "reason": "aggregate4 proof scope is exactly 4 voters; live agent count differs.",
        })

    # V3: aggregate4 surface hardening — collect per-vote audit counts
    _v3_blocked = sum(1 for d in details if d.get("aggregate4_false_act_surface_blocked"))
    _v3_invalid = sum(1 for d in details if d.get("aggregate4_invalid_legacy_vote"))
    _v3_domain_rej = sum(1 for d in details if d.get("aggregate4_domain_enum_rejected"))
    consensus["aggregate4_proof_surface_only"] = True
    consensus["aggregate4_does_not_authorize_action"] = True
    consensus["aggregate4_false_act_surface_blocked_count"] = _v3_blocked
    consensus["aggregate4_invalid_legacy_votes_count"] = _v3_invalid
    consensus["aggregate4_domain_enum_rejected_count"] = _v3_domain_rej

    return {
        "agent_vote_details": details,
        "consensus": consensus,
    }
# --- P3I_MAX_CONSENSUS_SURFACE_HELPERS_END ---


class GuardX108:
    def __init__(self, config: GuardConfig | None = None) -> None:
        self.config = config or GuardConfig()

    def decide(self, aggregate: DomainAggregate) -> CanonicalDecisionEnvelope:
        contradiction_count = len(aggregate.contradictions)
        unknown_count = len(aggregate.unknowns)
        risk_count = len(aggregate.risk_flags)

        if contradiction_count >= self.config.max_contradictions_before_block or "FRAUD_PATTERN" in aggregate.risk_flags:
            gate = X108Gate.BLOCK
            reason = "CONTRADICTION_THRESHOLD_REACHED"
            severity = Severity.S4
        elif unknown_count > self.config.max_unknowns_before_hold or aggregate.confidence < self.config.hold_confidence_floor:
            gate = X108Gate.HOLD
            reason = "UNKNOWNS_OR_CONFIDENCE_LOW"
            severity = Severity.S2
        elif risk_count >= 2 and aggregate.confidence < self.config.min_confidence_allow:
            gate = X108Gate.HOLD
            reason = "RISK_FLAGS_REQUIRE_DELAY"
            severity = Severity.S2
        else:
            gate = X108Gate.ALLOW
            reason = "GUARD_ALLOW"
            severity = Severity.S0 if aggregate.confidence >= self.config.min_confidence_allow else Severity.S1

        decision_id = f"{aggregate.domain.value}-{uuid.uuid4().hex[:12]}"
        trace_id = str(uuid.uuid4())
        ticket_required = gate == X108Gate.ALLOW
        ticket_id = uuid.uuid4().hex[:16] if ticket_required else None
        attestation_ref = hashlib.sha256("|".join(aggregate.evidence_refs).encode("utf-8")).hexdigest()[:24] if aggregate.evidence_refs else None

        consensus_surface = _x108_consensus_surface(aggregate.agent_votes)

        return CanonicalDecisionEnvelope(
            domain=aggregate.domain.value,
            market_verdict=aggregate.market_verdict,
            confidence=aggregate.confidence,
            contradictions=aggregate.contradictions,
            unknowns=aggregate.unknowns,
            risk_flags=aggregate.risk_flags,
            x108_gate=gate.value,
            reason_code=reason,
            severity=severity.value,
            decision_id=decision_id,
            trace_id=trace_id,
            ticket_required=ticket_required,
            ticket_id=ticket_id,
            attestation_ref=attestation_ref,
            source=SourceTag.CANONICAL_FRAMEWORK.value,
            evidence_refs=aggregate.evidence_refs,
            metrics=aggregate.extra_metrics,
            raw_engine={
                "domain": aggregate.domain.value,
                "agent_votes": [v.agent_id for v in aggregate.agent_votes],
                "vote_count": len(aggregate.agent_votes),
                "agent_vote_details": consensus_surface["agent_vote_details"],
                "consensus": consensus_surface["consensus"],
            },
        )
