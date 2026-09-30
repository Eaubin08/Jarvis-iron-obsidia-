from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable

from .common import ActionCandidate, PeripheralSignalPacket

class AgentLayer(StrEnum):
    CONTROL = "CONTROL"
    DATA = "DATA"
    PROVENANCE = "PROVENANCE"
    MEMORY = "MEMORY"
    SIGMA = "SIGMA"
    EML = "EML"
    ENERGY = "ENERGY"
    TIMEVERSE = "TIMEVERSE"
    OCS = "OCS"
    OPERATIONAL_CONSTANCE = "OPERATIONAL_CONSTANCE"
    PERMISSION_ECONOMIC = "PERMISSION_ECONOMIC"
    OS3 = "OS3"
    GENCOIN = "GENCOIN"
    WORLD_ACTION = "WORLD_ACTION"
    FEEDBACK_MEMORY = "FEEDBACK_MEMORY"

@dataclass(frozen=True)
class NonSovereignAgentSpec:
    agent_id: str
    layer: AgentLayer
    description: str
    can_score: bool = True
    can_emit_act: bool = False
    can_authorize: bool = False
    can_mutate_kernel: bool = False
    can_write_memory: bool = False

    def assert_safe(self) -> None:
        if self.can_emit_act or self.can_authorize or self.can_mutate_kernel:
            raise AssertionError(f"AGENT_NOT_NON_SOVEREIGN:{self.agent_id}")

@dataclass
class AgentResult:
    agent_id: str
    layer: AgentLayer
    packet: PeripheralSignalPacket
    notes: list[str] = field(default_factory=list)

    def assert_non_sovereign(self) -> None:
        self.packet.assert_non_sovereign()

AgentCallable = Callable[[ActionCandidate], AgentResult]

def run_agent_safely(spec: NonSovereignAgentSpec, fn: Callable[[ActionCandidate], PeripheralSignalPacket], action: ActionCandidate) -> AgentResult:
    spec.assert_safe()
    packet = fn(action)
    packet.assert_non_sovereign()
    packet.evidence_refs.append(f"agent:{spec.agent_id}")
    return AgentResult(agent_id=spec.agent_id, layer=spec.layer, packet=packet)
