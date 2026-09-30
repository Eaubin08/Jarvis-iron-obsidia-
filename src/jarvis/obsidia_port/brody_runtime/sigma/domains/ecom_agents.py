from __future__ import annotations

from ..base import BaseAgent
from ..contracts import AgentVote, Domain, EcomState, Layer, Severity


class TrafficQualityAgent(BaseAgent):
    agent_id = "TrafficQualityAgent"
    def evaluate(self, state: EcomState) -> AgentVote:
        verdict = "PAY" if state.traffic_quality > 0.7 else "WAIT" if state.traffic_quality > 0.4 else "REFUSE"
        sev = Severity.S2 if verdict=="REFUSE" else Severity.S1
        return AgentVote(self.agent_id, Domain.ECOM, Layer.OBSERVATION, f"traffic_quality={state.traffic_quality:.2f}", state.traffic_quality, sev, proposed_verdict=verdict)


class BasketIntentAgent(BaseAgent):
    agent_id = "BasketIntentAgent"
    def evaluate(self, state: EcomState) -> AgentVote:
        verdict = "PAY" if state.basket_intent_score > 0.7 else "WAIT" if state.basket_intent_score > 0.4 else "REFUSE"
        return AgentVote(self.agent_id, Domain.ECOM, Layer.OBSERVATION, f"basket_intent={state.basket_intent_score:.2f}", state.basket_intent_score, Severity.S1, proposed_verdict=verdict)


class OfferHealthAgent(BaseAgent):
    agent_id = "OfferHealthAgent"
    def evaluate(self, state: EcomState) -> AgentVote:
        verdict = "REFUSE" if not state.stock_ok or state.margin_rate < 0 else "WAIT" if state.margin_rate < 0.1 else "PAY"
        sev = Severity.S3 if verdict=="REFUSE" else Severity.S2 if verdict=="WAIT" else Severity.S1
        return AgentVote(self.agent_id, Domain.ECOM, Layer.OBSERVATION, f"stock_ok={state.stock_ok}, margin={state.margin_rate:.2f}", 0.8, sev, proposed_verdict=verdict)


class CustomerTrustAgent(BaseAgent):
    agent_id = "CustomerTrustAgent"
    def evaluate(self, state: EcomState) -> AgentVote:
        verdict = "PAY" if state.customer_trust > 0.7 else "WAIT" if state.customer_trust > 0.4 else "REFUSE"
        return AgentVote(self.agent_id, Domain.ECOM, Layer.OBSERVATION, f"customer_trust={state.customer_trust:.2f}", state.customer_trust, Severity.S1, proposed_verdict=verdict)


class ConversionReadinessAgent(BaseAgent):
    agent_id = "ConversionReadinessAgent"
    def evaluate(self, state: EcomState) -> AgentVote:
        verdict = "PAY" if state.conversion_readiness > 0.75 else "WAIT" if state.conversion_readiness > 0.45 else "REFUSE"
        return AgentVote(self.agent_id, Domain.ECOM, Layer.INTERPRETATION, f"conversion_readiness={state.conversion_readiness:.2f}", state.conversion_readiness, Severity.S1, proposed_verdict=verdict)


class MarginProtectionAgent(BaseAgent):
    agent_id = "MarginProtectionAgent"
    def evaluate(self, state: EcomState) -> AgentVote:
        verdict = "REFUSE" if state.margin_rate < 0.05 else "WAIT" if state.margin_rate < 0.15 else "PAY"
        sev = Severity.S3 if verdict=="REFUSE" else Severity.S2 if verdict=="WAIT" else Severity.S1
        return AgentVote(self.agent_id, Domain.ECOM, Layer.INTERPRETATION, f"margin_rate={state.margin_rate:.2f}", min(1.0, max(0.0, 1-state.margin_rate)), sev, proposed_verdict=verdict, risk_flags=["LOW_MARGIN"] if verdict!="PAY" else [])


class ROASRealityAgent(BaseAgent):
    agent_id = "ROASRealityAgent"
    def evaluate(self, state: EcomState) -> AgentVote:
        verdict = "PAY" if state.roas > 2.0 else "WAIT" if state.roas > 1.0 else "REFUSE"
        sev = Severity.S2 if verdict=="REFUSE" else Severity.S1
        return AgentVote(self.agent_id, Domain.ECOM, Layer.INTERPRETATION, f"roas={state.roas:.2f}", min(1.0, state.roas/4), sev, proposed_verdict=verdict, risk_flags=["LOW_ROAS"] if verdict=="REFUSE" else [])


class FulfillmentRiskAgent(BaseAgent):
    agent_id = "FulfillmentRiskAgent"
    def evaluate(self, state: EcomState) -> AgentVote:
        verdict = "REFUSE" if state.fulfillment_risk > 0.75 else "WAIT" if state.fulfillment_risk > 0.45 else "PAY"
        sev = Severity.S3 if verdict=="REFUSE" else Severity.S2 if verdict=="WAIT" else Severity.S1
        return AgentVote(self.agent_id, Domain.ECOM, Layer.INTERPRETATION, f"fulfillment_risk={state.fulfillment_risk:.2f}", state.fulfillment_risk, sev, proposed_verdict=verdict)


class IntentConflictAgent(BaseAgent):
    agent_id = "IntentConflictAgent"
    def evaluate(self, state: EcomState) -> AgentVote:
        verdict = "WAIT" if state.intent_conflict_score > 0.4 else "PAY"
        sev = Severity.S2 if verdict=="WAIT" else Severity.S1
        return AgentVote(self.agent_id, Domain.ECOM, Layer.CONTRADICTION, f"intent_conflict={state.intent_conflict_score:.2f}", state.intent_conflict_score, sev, proposed_verdict=verdict, contradictions=["INTENT_CONFLICT"] if verdict=="WAIT" else [])


class CheckoutFrictionAgent(BaseAgent):
    agent_id = "CheckoutFrictionAgent"
    def evaluate(self, state: EcomState) -> AgentVote:
        verdict = "WAIT" if state.checkout_friction_score > 0.45 else "PAY"
        sev = Severity.S2 if verdict=="WAIT" else Severity.S1
        return AgentVote(self.agent_id, Domain.ECOM, Layer.CONTRADICTION, f"checkout_friction={state.checkout_friction_score:.2f}", state.checkout_friction_score, sev, proposed_verdict=verdict, contradictions=["CHECKOUT_FRICTION"] if verdict=="WAIT" else [])


class MerchantPolicyAgent(BaseAgent):
    agent_id = "MerchantPolicyAgent"
    def evaluate(self, state: EcomState) -> AgentVote:
        verdict = "REFUSE" if state.merchant_policy_score < 0.2 else "WAIT" if state.merchant_policy_score < 0.5 else "PAY"
        sev = Severity.S3 if verdict=="REFUSE" else Severity.S2 if verdict=="WAIT" else Severity.S1
        return AgentVote(self.agent_id, Domain.ECOM, Layer.CONTRADICTION, f"merchant_policy={state.merchant_policy_score:.2f}", 1-state.merchant_policy_score, sev, proposed_verdict=verdict, risk_flags=["MERCHANT_POLICY_CONSTRAINT"] if verdict!="PAY" else [])


class EcomProofAgent(BaseAgent):
    agent_id = "EcomProofAgent"
    def evaluate(self, state: EcomState) -> AgentVote:
        unknowns = []
        if state.x108_compliance_rate < 0.8:
            unknowns.append("LOW_X108_COMPLIANCE")
        if state.order_value <= 0:
            unknowns.append("NO_ORDER_VALUE")
        verdict = "WAIT" if unknowns else "PAY"
        return AgentVote(self.agent_id, Domain.ECOM, Layer.PROOF, "ecom proof readiness", 0.9 if not unknowns else 0.45, Severity.S2 if unknowns else Severity.S0, proposed_verdict=verdict, unknowns=unknowns)


def build_ecom_agents() -> list[BaseAgent]:
    return [
        TrafficQualityAgent(),
        BasketIntentAgent(),
        OfferHealthAgent(),
        CustomerTrustAgent(),
        ConversionReadinessAgent(),
        MarginProtectionAgent(),
        ROASRealityAgent(),
        FulfillmentRiskAgent(),
        IntentConflictAgent(),
        CheckoutFrictionAgent(),
        MerchantPolicyAgent(),
        EcomProofAgent(),
    ]
