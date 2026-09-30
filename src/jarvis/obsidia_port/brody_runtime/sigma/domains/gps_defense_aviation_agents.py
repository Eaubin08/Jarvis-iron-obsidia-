from __future__ import annotations

from ..base import BaseAgent
from ..contracts import AgentVote, Domain, Layer, Severity, GpsDefenseAviationState

class SourceAvailabilityAgent(BaseAgent):
    agent_id = "SourceAvailabilityAgent"
    def evaluate(self, state: GpsDefenseAviationState) -> AgentVote:
        missing = []
        if not state.gps_available:
            missing.append("GPS_MISSING")
        if not state.inertial_available:
            missing.append("INERTIAL_MISSING")
        if not state.radio_available:
            missing.append("RADIO_MISSING")
        return AgentVote(
            agent_id=self.agent_id,
            domain=Domain.GPS_DEFENSE_AVIATION,
            layer=Layer.OBSERVATION,
            claim="source availability",
            confidence=0.95 if not missing else 0.35,
            severity_hint=Severity.S0 if not missing else Severity.S3,
            unknowns=missing,
            proposed_verdict="RECALC_TRAJECTORY" if missing else "TRAJECTORY_VALID",
        )

class TrajectoryIntegrityAgent(BaseAgent):
    agent_id = "TrajectoryIntegrityAgent"
    def evaluate(self, state: GpsDefenseAviationState) -> AgentVote:
        drift = state.trajectory_drift_score
        risk = ["TRAJECTORY_DRIFT"] if drift >= 0.6 else []
        verdict = "ABORT_TRAJECTORY" if drift >= 0.85 else "DEGRADED_NAVIGATION" if drift >= 0.6 else "TRAJECTORY_VALID"
        return AgentVote(
            self.agent_id,
            Domain.GPS_DEFENSE_AVIATION,
            Layer.INTERPRETATION,
            "trajectory integrity",
            max(0.0, 1.0 - drift),
            Severity.S4 if drift >= 0.85 else Severity.S2 if drift >= 0.6 else Severity.S0,
            risk_flags=risk,
            proposed_verdict=verdict,
        )

class SourceConflictAgent(BaseAgent):
    agent_id = "SourceConflictAgent"
    def evaluate(self, state: GpsDefenseAviationState) -> AgentVote:
        conflict = state.source_conflict_score
        contradictions = ["SOURCE_CONFLICT"] if conflict >= 0.5 else []
        verdict = "ABORT_TRAJECTORY" if conflict >= 0.8 else "RECALC_TRAJECTORY" if conflict >= 0.5 else "TRAJECTORY_VALID"
        return AgentVote(
            self.agent_id,
            Domain.GPS_DEFENSE_AVIATION,
            Layer.CONTRADICTION,
            "source conflict",
            max(0.0, 1.0 - conflict),
            Severity.S4 if conflict >= 0.8 else Severity.S2 if conflict >= 0.5 else Severity.S0,
            contradictions=contradictions,
            proposed_verdict=verdict,
        )

class TimeSkewAgent(BaseAgent):
    agent_id = "TimeSkewAgent"
    def evaluate(self, state: GpsDefenseAviationState) -> AgentVote:
        skew = state.time_skew_score
        risk = ["TIME_SKEW"] if skew >= 0.5 else []
        severe_unknowns = ["TIME_SKEW_ACTIVE", "TEMPORAL_ALIGNMENT_UNCERTAIN"] if skew >= 0.8 else []
        verdict = "ABORT_TRAJECTORY" if skew >= 0.9 else "RECALC_TRAJECTORY" if skew >= 0.5 else "TRAJECTORY_VALID"
        return AgentVote(
            self.agent_id,
            Domain.GPS_DEFENSE_AVIATION,
            Layer.PROOF,
            "time skew",
            max(0.0, 1.0 - skew),
            Severity.S4 if skew >= 0.9 else Severity.S3 if skew >= 0.8 else Severity.S2 if skew >= 0.5 else Severity.S0,
            risk_flags=risk,
            unknowns=severe_unknowns,
            proposed_verdict=verdict,
        )

class BrownoutAgent(BaseAgent):
    agent_id = "BrownoutAgent"
    def evaluate(self, state: GpsDefenseAviationState) -> AgentVote:
        b = state.brownout_score
        risk = ["BROWNOUT"] if b >= 0.5 else []
        severe_unknowns = ["BROWNOUT_ACTIVE", "POWER_STATE_UNCERTAIN"] if b >= 0.8 else []
        verdict = "ABORT_TRAJECTORY" if b >= 0.9 else "DEGRADED_NAVIGATION" if b >= 0.5 else "TRAJECTORY_VALID"
        return AgentVote(
            self.agent_id,
            Domain.GPS_DEFENSE_AVIATION,
            Layer.OBSERVATION,
            "brownout",
            max(0.0, 1.0 - b),
            Severity.S4 if b >= 0.9 else Severity.S3 if b >= 0.8 else Severity.S2 if b >= 0.5 else Severity.S0,
            risk_flags=risk,
            unknowns=severe_unknowns,
            proposed_verdict=verdict,
        )

class AttestationReadinessAgent(BaseAgent):
    agent_id = "GpsAttestationReadinessAgent"
    def evaluate(self, state: GpsDefenseAviationState) -> AgentVote:
        ready = state.attestation_ready and state.rollback_possible
        return AgentVote(
            self.agent_id,
            Domain.GPS_DEFENSE_AVIATION,
            Layer.PROOF,
            "attestation readiness",
            0.9 if ready else 0.4,
            Severity.S0 if ready else Severity.S2,
            unknowns=[] if ready else ["ATTESTATION_NOT_READY"],
            proposed_verdict="TRAJECTORY_VALID" if ready else "RECALC_TRAJECTORY",
        )

def build_gps_defense_aviation_agents():
    return [
        SourceAvailabilityAgent(),
        TrajectoryIntegrityAgent(),
        SourceConflictAgent(),
        TimeSkewAgent(),
        BrownoutAgent(),
        AttestationReadinessAgent(),
    ]