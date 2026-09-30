from __future__ import annotations

from ..base import BaseAgent
from ..contracts import AgentVote, Domain, DomainAggregate, Layer, Severity


class BaseMetaAgent(BaseAgent):
    def evaluate(self, aggregate: DomainAggregate) -> AgentVote:
        raise NotImplementedError


class UnknownsAgent(BaseMetaAgent):
    agent_id = "UnknownsAgent"
    def evaluate(self, aggregate: DomainAggregate) -> AgentVote:
        sev = Severity.S2 if aggregate.unknowns else Severity.S0
        return AgentVote(self.agent_id, Domain.META, Layer.CONTRADICTION, f"unknowns={len(aggregate.unknowns)}", 0.9 if aggregate.unknowns else 0.3, sev, proposed_verdict="HOLD" if aggregate.unknowns else aggregate.market_verdict, unknowns=list(aggregate.unknowns))


class ConflictResolutionAgent(BaseMetaAgent):
    agent_id = "ConflictResolutionAgent"
    def evaluate(self, aggregate: DomainAggregate) -> AgentVote:
        sev = Severity.S3 if aggregate.contradictions else Severity.S0
        return AgentVote(self.agent_id, Domain.META, Layer.CONTRADICTION, f"contradictions={len(aggregate.contradictions)}", 0.95 if aggregate.contradictions else 0.2, sev, proposed_verdict="HOLD" if aggregate.contradictions else aggregate.market_verdict, contradictions=list(aggregate.contradictions))


class PolicyScopeAgent(BaseMetaAgent):
    agent_id = "PolicyScopeAgent"
    def evaluate(self, aggregate: DomainAggregate) -> AgentVote:
        blocked = any(flag in {"LIMIT_PRESSURE", "MERCHANT_POLICY_CONSTRAINT"} for flag in aggregate.risk_flags)
        return AgentVote(self.agent_id, Domain.META, Layer.CONTRADICTION, "policy scope validation", 0.9 if blocked else 0.4, Severity.S3 if blocked else Severity.S1, proposed_verdict="BLOCK" if blocked else aggregate.market_verdict)


class TicketReadinessAgent(BaseMetaAgent):
    agent_id = "TicketReadinessAgent"
    def evaluate(self, aggregate: DomainAggregate) -> AgentVote:
        ready = not aggregate.unknowns and not aggregate.contradictions
        return AgentVote(self.agent_id, Domain.META, Layer.PROOF, "ticket readiness", 0.9 if ready else 0.35, Severity.S0 if ready else Severity.S2, proposed_verdict=aggregate.market_verdict, unknowns=[] if ready else ["TICKET_NOT_READY"])


class TraceIntegrityAgent(BaseMetaAgent):
    agent_id = "TraceIntegrityAgent"
    def evaluate(self, aggregate: DomainAggregate) -> AgentVote:
        ready = len(aggregate.agent_votes) >= 3 and len(aggregate.evidence_refs) >= 1
        return AgentVote(self.agent_id, Domain.META, Layer.PROOF, f"trace_evidence={len(aggregate.evidence_refs)}", 0.9 if ready else 0.4, Severity.S0 if ready else Severity.S2, proposed_verdict=aggregate.market_verdict, unknowns=[] if ready else ["TRACE_INCOMPLETE"])


class AttestationReadinessAgent(BaseMetaAgent):
    agent_id = "AttestationReadinessAgent"
    def evaluate(self, aggregate: DomainAggregate) -> AgentVote:
        ready = "proof_ready" in aggregate.extra_metrics
        return AgentVote(self.agent_id, Domain.META, Layer.PROOF, "attestation readiness", 0.85 if ready else 0.4, Severity.S0 if ready else Severity.S2, proposed_verdict=aggregate.market_verdict, unknowns=[] if ready else ["ATTESTATION_NOT_READY"])


class HumanOverrideEligibilityAgent(BaseMetaAgent):
    agent_id = "HumanOverrideEligibilityAgent"
    def evaluate(self, aggregate: DomainAggregate) -> AgentVote:
        eligible = aggregate.market_verdict in {"ANALYZE", "WAIT", "REVIEW", "HOLD"} or aggregate.confidence < 0.65
        return AgentVote(self.agent_id, Domain.META, Layer.PROOF, f"human_override={eligible}", 0.9 if eligible else 0.5, Severity.S1, proposed_verdict=aggregate.market_verdict)


class SeverityClassifierAgent(BaseMetaAgent):
    agent_id = "SeverityClassifierAgent"
    def evaluate(self, aggregate: DomainAggregate) -> AgentVote:
        score = 0
        score += len(aggregate.unknowns)
        score += len(aggregate.contradictions) * 2
        score += len(aggregate.risk_flags)
        severity = Severity.S4 if score >= 5 else Severity.S3 if score >= 3 else Severity.S2 if score >= 1 else Severity.S0
        return AgentVote(self.agent_id, Domain.META, Layer.PROOF, f"severity_classified={severity.value}", min(1.0, 0.4 + score * 0.1), severity, proposed_verdict=aggregate.market_verdict)


class ReplayConsistencyAgent(BaseMetaAgent):
    agent_id = "ReplayConsistencyAgent"
    def evaluate(self, aggregate: DomainAggregate) -> AgentVote:
        deterministic = aggregate.extra_metrics.get("deterministic", True)
        return AgentVote(self.agent_id, Domain.META, Layer.PROOF, f"deterministic={deterministic}", 0.9 if deterministic else 0.4, Severity.S0 if deterministic else Severity.S2, proposed_verdict=aggregate.market_verdict)


class ProofConsistencyAgent(BaseMetaAgent):
    agent_id = "ProofConsistencyAgent"
    def evaluate(self, aggregate: DomainAggregate) -> AgentVote:
        coherent = bool(aggregate.market_verdict) and aggregate.confidence >= 0.0
        return AgentVote(self.agent_id, Domain.META, Layer.PROOF, "payload/ticket/trace/severity coherence", 0.95 if coherent else 0.2, Severity.S0 if coherent else Severity.S3, proposed_verdict=aggregate.market_verdict)


def build_meta_agents() -> list[BaseMetaAgent]:
    return [
        UnknownsAgent(),
        ConflictResolutionAgent(),
        PolicyScopeAgent(),
        TicketReadinessAgent(),
        TraceIntegrityAgent(),
        AttestationReadinessAgent(),
        HumanOverrideEligibilityAgent(),
        SeverityClassifierAgent(),
        ReplayConsistencyAgent(),
        ProofConsistencyAgent(),
    ]
