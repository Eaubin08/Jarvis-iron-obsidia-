from __future__ import annotations

from ..base import BaseAgent
from ..contracts import AgentVote, BankState, Domain, Layer, Severity


class TransactionContextAgent(BaseAgent):
    agent_id = "TransactionContextAgent"
    def evaluate(self, state: BankState) -> AgentVote:
        unknowns = ["UNKNOWN_CHANNEL"] if not state.channel else []
        return AgentVote(self.agent_id, Domain.BANK, Layer.OBSERVATION, f"type={state.transaction_type}, channel={state.channel}", 0.8, Severity.S1, proposed_verdict="ANALYZE", unknowns=unknowns)


class CounterpartyAgent(BaseAgent):
    agent_id = "CounterpartyAgent"
    def evaluate(self, state: BankState) -> AgentVote:
        verdict = "AUTHORIZE" if state.counterparty_known and state.counterparty_age_days > 30 else "ANALYZE"
        return AgentVote(self.agent_id, Domain.BANK, Layer.OBSERVATION, f"counterparty_known={state.counterparty_known}, age_days={state.counterparty_age_days}", 0.75 if verdict=="AUTHORIZE" else 0.55, Severity.S1, proposed_verdict=verdict)


class LiquidityExposureAgent(BaseAgent):
    agent_id = "LiquidityExposureAgent"
    def evaluate(self, state: BankState) -> AgentVote:
        pressure = 1.0 if state.account_balance <= 0 else state.amount / max(state.account_balance, 1e-9)
        verdict = "BLOCK" if pressure > 0.9 else "ANALYZE" if pressure > 0.5 else "AUTHORIZE"
        sev = Severity.S3 if verdict=="BLOCK" else Severity.S2 if verdict=="ANALYZE" else Severity.S1
        return AgentVote(self.agent_id, Domain.BANK, Layer.OBSERVATION, f"liquidity_pressure={pressure:.2f}", min(1.0, pressure), sev, proposed_verdict=verdict, risk_flags=["CASH_PRESSURE"] if pressure > 0.5 else [])


class BehaviorShiftAgent(BaseAgent):
    agent_id = "BehaviorShiftAgent"
    def evaluate(self, state: BankState) -> AgentVote:
        verdict = "ANALYZE" if state.behavior_shift_score > 0.5 else "AUTHORIZE"
        return AgentVote(self.agent_id, Domain.BANK, Layer.OBSERVATION, f"behavior_shift={state.behavior_shift_score:.2f}", state.behavior_shift_score, Severity.S2 if verdict=="ANALYZE" else Severity.S1, proposed_verdict=verdict)


class FraudPatternAgent(BaseAgent):
    agent_id = "FraudPatternAgent"
    def evaluate(self, state: BankState) -> AgentVote:
        verdict = "BLOCK" if state.fraud_score > 0.75 else "ANALYZE" if state.fraud_score > 0.45 else "AUTHORIZE"
        sev = Severity.S4 if verdict=="BLOCK" else Severity.S2 if verdict=="ANALYZE" else Severity.S1
        return AgentVote(self.agent_id, Domain.BANK, Layer.INTERPRETATION, f"fraud_score={state.fraud_score:.2f}", state.fraud_score, sev, proposed_verdict=verdict, risk_flags=["FRAUD_PATTERN"] if verdict!="AUTHORIZE" else [])


class LimitPolicyAgent(BaseAgent):
    agent_id = "LimitPolicyAgent"
    def evaluate(self, state: BankState) -> AgentVote:
        ratio = state.amount / max(state.policy_limit, 1e-9)
        verdict = "BLOCK" if ratio > 1.0 else "ANALYZE" if ratio > 0.8 else "AUTHORIZE"
        sev = Severity.S3 if verdict=="BLOCK" else Severity.S2 if verdict=="ANALYZE" else Severity.S1
        return AgentVote(self.agent_id, Domain.BANK, Layer.INTERPRETATION, f"limit_ratio={ratio:.2f}", min(1.0, ratio), sev, proposed_verdict=verdict, risk_flags=["LIMIT_PRESSURE"] if ratio > 0.8 else [])


class AffordabilityAgent(BaseAgent):
    agent_id = "AffordabilityAgent"
    def evaluate(self, state: BankState) -> AgentVote:
        verdict = "AUTHORIZE" if state.affordability_score > 0.7 else "ANALYZE" if state.affordability_score > 0.4 else "BLOCK"
        sev = Severity.S3 if verdict=="BLOCK" else Severity.S2 if verdict=="ANALYZE" else Severity.S1
        return AgentVote(self.agent_id, Domain.BANK, Layer.INTERPRETATION, f"affordability={state.affordability_score:.2f}", state.affordability_score, sev, proposed_verdict=verdict)


class TemporalUrgencyAgent(BaseAgent):
    agent_id = "TemporalUrgencyAgent"
    def evaluate(self, state: BankState) -> AgentVote:
        verdict = "ANALYZE" if state.urgency_score > 0.75 else "AUTHORIZE"
        return AgentVote(self.agent_id, Domain.BANK, Layer.INTERPRETATION, f"urgency={state.urgency_score:.2f}", state.urgency_score, Severity.S2 if verdict=="ANALYZE" else Severity.S1, proposed_verdict=verdict, contradictions=["URGENT_BEHAVIOR"] if verdict=="ANALYZE" else [])


class IdentityMismatchAgent(BaseAgent):
    agent_id = "IdentityMismatchAgent"
    def evaluate(self, state: BankState) -> AgentVote:
        combined = max(state.identity_mismatch_score, 1 - state.device_trust_score)
        verdict = "BLOCK" if combined > 0.75 else "ANALYZE" if combined > 0.4 else "AUTHORIZE"
        sev = Severity.S4 if verdict=="BLOCK" else Severity.S2 if verdict=="ANALYZE" else Severity.S1
        return AgentVote(self.agent_id, Domain.BANK, Layer.CONTRADICTION, f"identity_mismatch={combined:.2f}", combined, sev, proposed_verdict=verdict, contradictions=["IDENTITY_CONTEXT_MISMATCH"] if combined > 0.4 else [])


class NarrativeConflictAgent(BaseAgent):
    agent_id = "NarrativeConflictAgent"
    def evaluate(self, state: BankState) -> AgentVote:
        verdict = "ANALYZE" if state.narrative_conflict_score > 0.45 else "AUTHORIZE"
        return AgentVote(self.agent_id, Domain.BANK, Layer.CONTRADICTION, f"narrative_conflict={state.narrative_conflict_score:.2f}", state.narrative_conflict_score, Severity.S2 if verdict=="ANALYZE" else Severity.S1, proposed_verdict=verdict, contradictions=["NARRATIVE_CONFLICT"] if verdict=="ANALYZE" else [])


class RecoveryPathAgent(BaseAgent):
    agent_id = "RecoveryPathAgent"
    def evaluate(self, state: BankState) -> AgentVote:
        claim = "manual confirmation / delayed verification path available"
        return AgentVote(self.agent_id, Domain.BANK, Layer.PROOF, claim, 0.85, Severity.S1, proposed_verdict="ANALYZE")


class BankProofAgent(BaseAgent):
    agent_id = "BankProofAgent"
    def evaluate(self, state: BankState) -> AgentVote:
        unknowns = []
        if state.elapsed_s < state.min_required_elapsed_s:
            unknowns.append("TEMPORAL_LOCK_NOT_MATURE")
        if state.recent_failed_attempts > 0:
            unknowns.append("RECENT_FAILED_ATTEMPTS")
        verdict = "ANALYZE" if unknowns else "AUTHORIZE"
        return AgentVote(self.agent_id, Domain.BANK, Layer.PROOF, "bank proof readiness", 0.9 if not unknowns else 0.45, Severity.S2 if unknowns else Severity.S0, proposed_verdict=verdict, unknowns=unknowns)


def build_bank_agents() -> list[BaseAgent]:
    return [
        TransactionContextAgent(),
        CounterpartyAgent(),
        LiquidityExposureAgent(),
        BehaviorShiftAgent(),
        FraudPatternAgent(),
        LimitPolicyAgent(),
        AffordabilityAgent(),
        TemporalUrgencyAgent(),
        IdentityMismatchAgent(),
        NarrativeConflictAgent(),
        RecoveryPathAgent(),
        BankProofAgent(),
    ]
