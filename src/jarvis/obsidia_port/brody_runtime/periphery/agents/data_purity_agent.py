from __future__ import annotations

from periphery.common import ActionCandidate
from periphery.agent_contracts import AgentLayer, NonSovereignAgentSpec, AgentResult, run_agent_safely
from periphery.data_gate import run_data_gate

SPEC = NonSovereignAgentSpec(
    agent_id="DATA_PURITY_AGENT",
    layer=AgentLayer.DATA,
    description="Wrapper non souverain autour de run_data_gate",
)

def run(action: ActionCandidate) -> AgentResult:
    return run_agent_safely(SPEC, run_data_gate, action)
