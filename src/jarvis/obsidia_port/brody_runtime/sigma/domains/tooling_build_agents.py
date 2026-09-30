from __future__ import annotations

from ..base import BaseAgent
from ..contracts import AgentVote, Domain, Layer, Severity, ToolingBuildState


class ScopeIntegrityAgent(BaseAgent):
    """Vérifie que le scope est exact et qu'aucun fichier protégé n'a été touché."""
    agent_id = "ScopeIntegrityAgent"

    def evaluate(self, state: ToolingBuildState) -> AgentVote:
        if state.protected_scope_status == "VIOLATED":
            return AgentVote(
                agent_id=self.agent_id,
                domain=Domain.TOOLING_BUILD,
                layer=Layer.OBSERVATION,
                claim="scope integrity",
                confidence=0.05,
                severity_hint=Severity.S4,
                contradictions=["PROTECTED_PATH_VIOLATION"],
                proposed_verdict="BUILD_BLOCK",
            )

        # Drift = fichiers réellement touchés hors du scope approuvé
        drift = []
        if state.approved_scope:
            approved = set(state.approved_scope)
            drift = [f for f in state.actual_touched_files if f not in approved]

        if drift:
            return AgentVote(
                agent_id=self.agent_id,
                domain=Domain.TOOLING_BUILD,
                layer=Layer.OBSERVATION,
                claim="scope integrity",
                confidence=0.45,
                severity_hint=Severity.S2,
                unknowns=["SCOPE_DRIFT"],
                risk_flags=["SCOPE_DRIFT_DETECTED"],
                proposed_verdict="BUILD_HOLD",
            )

        return AgentVote(
            agent_id=self.agent_id,
            domain=Domain.TOOLING_BUILD,
            layer=Layer.OBSERVATION,
            claim="scope integrity",
            confidence=0.95,
            severity_hint=Severity.S0,
            proposed_verdict="READY_FOR_COMMIT_REVIEW",
        )


class TestGateAgent(BaseAgent):
    """Vérifie que tous les tests et gates ont passé avant d'autoriser la session."""
    agent_id = "TestGateAgent"

    def evaluate(self, state: ToolingBuildState) -> AgentVote:
        tests_fail = state.tests_results == "FAIL"
        gates_fail = state.gates_results == "FAIL"
        tests_partial = state.tests_results == "PARTIAL"
        gates_partial = state.gates_results == "PARTIAL"

        if tests_fail and gates_fail:
            return AgentVote(
                agent_id=self.agent_id,
                domain=Domain.TOOLING_BUILD,
                layer=Layer.INTERPRETATION,
                claim="test gate",
                confidence=0.05,
                severity_hint=Severity.S4,
                contradictions=["GATE_FAILURE"],
                risk_flags=["TESTS_AND_GATES_FAILED"],
                proposed_verdict="BUILD_BLOCK",
            )

        if tests_fail or gates_fail or tests_partial or gates_partial:
            failure_hint = state.first_failure or "UNKNOWN_FAILURE"
            return AgentVote(
                agent_id=self.agent_id,
                domain=Domain.TOOLING_BUILD,
                layer=Layer.INTERPRETATION,
                claim="test gate",
                confidence=0.35,
                severity_hint=Severity.S3,
                unknowns=["TEST_GATE_INCOMPLETE"],
                risk_flags=[f"PARTIAL_FAILURE:{failure_hint}"],
                proposed_verdict="BUILD_HOLD",
            )

        return AgentVote(
            agent_id=self.agent_id,
            domain=Domain.TOOLING_BUILD,
            layer=Layer.INTERPRETATION,
            claim="test gate",
            confidence=0.95,
            severity_hint=Severity.S0,
            proposed_verdict="READY_FOR_COMMIT_REVIEW",
        )


class SessionIntegrityAgent(BaseAgent):
    """Vérifie l'intégrité de session : sha, manifest, approbation humaine, isolation."""
    agent_id = "SessionIntegrityAgent"

    def evaluate(self, state: ToolingBuildState) -> AgentVote:
        contradictions = list(state.contradictions)
        unknowns = list(state.unknowns)
        risk_flags = list(state.risk_flags)

        if state.human_approval_status == "MISSING":
            contradictions.append("HUMAN_APPROVAL_MISSING")
        elif state.human_approval_status in ("PENDING", "UNKNOWN"):
            unknowns.append("HUMAN_APPROVAL_PENDING")

        if not state.base_sha:
            unknowns.append("BASE_SHA_MISSING")
        if not state.manifest_hash:
            unknowns.append("MANIFEST_HASH_MISSING")
        if not state.worktree_isolated:
            contradictions.append("WORKTREE_NOT_ISOLATED")
        if not state.branch_isolated:
            contradictions.append("BRANCH_NOT_ISOLATED")

        if state.decision_authority != "KX108_ONLY":
            contradictions.append("DECISION_AUTHORITY_VIOLATION")

        if contradictions:
            return AgentVote(
                agent_id=self.agent_id,
                domain=Domain.TOOLING_BUILD,
                layer=Layer.CONTRADICTION,
                claim="session integrity",
                confidence=0.10,
                severity_hint=Severity.S4,
                contradictions=contradictions,
                unknowns=unknowns,
                risk_flags=risk_flags,
                proposed_verdict="BUILD_BLOCK",
            )
        if unknowns:
            return AgentVote(
                agent_id=self.agent_id,
                domain=Domain.TOOLING_BUILD,
                layer=Layer.CONTRADICTION,
                claim="session integrity",
                confidence=0.40,
                severity_hint=Severity.S2,
                unknowns=unknowns,
                risk_flags=risk_flags,
                proposed_verdict="BUILD_HOLD",
            )
        return AgentVote(
            agent_id=self.agent_id,
            domain=Domain.TOOLING_BUILD,
            layer=Layer.CONTRADICTION,
            claim="session integrity",
            confidence=0.92,
            severity_hint=Severity.S0,
            proposed_verdict="READY_FOR_COMMIT_REVIEW",
        )


class CommitGuardAgent(BaseAgent):
    """Couche KERNEL : vérifie qu'aucun commit/push/merge non autorisé n'a eu lieu.
    Vérifie aussi que les garde-fous d'irréversibilité sont actifs.
    ACT=false — ce vote autorise uniquement la revue, jamais l'exécution."""
    agent_id = "CommitGuardAgent"

    def evaluate(self, state: ToolingBuildState) -> AgentVote:
        contradictions = []

        if not state.auto_commit_disabled:
            contradictions.append("AUTO_COMMIT_NOT_DISABLED")
        if not state.auto_push_disabled:
            contradictions.append("AUTO_PUSH_NOT_DISABLED")
        if not state.auto_merge_disabled:
            contradictions.append("AUTO_MERGE_NOT_DISABLED")

        if state.commit_status not in ("NOT_COMMITTED", "UNKNOWN"):
            contradictions.append("UNAUTHORIZED_COMMIT")
        if state.push_status not in ("NOT_PUSHED", "UNKNOWN"):
            contradictions.append("UNAUTHORIZED_PUSH")
        if state.merge_status not in ("NOT_MERGED", "UNKNOWN"):
            contradictions.append("UNAUTHORIZED_MERGE")

        if contradictions:
            return AgentVote(
                agent_id=self.agent_id,
                domain=Domain.TOOLING_BUILD,
                layer=Layer.KERNEL,
                claim="commit guard",
                confidence=0.05,
                severity_hint=Severity.S4,
                contradictions=contradictions,
                risk_flags=["IRREVERSIBLE_ACTION_DETECTED"],
                proposed_verdict="BUILD_BLOCK",
            )
        return AgentVote(
            agent_id=self.agent_id,
            domain=Domain.TOOLING_BUILD,
            layer=Layer.KERNEL,
            claim="commit guard",
            confidence=0.97,
            severity_hint=Severity.S0,
            proposed_verdict="READY_FOR_COMMIT_REVIEW",
        )


def build_tooling_build_agents() -> list:
    return [
        ScopeIntegrityAgent(),
        TestGateAgent(),
        SessionIntegrityAgent(),
        CommitGuardAgent(),
    ]
