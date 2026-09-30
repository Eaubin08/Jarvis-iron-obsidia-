from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal
GateHint = Literal['NONE','HOLD','BLOCK_CANDIDATE']
@dataclass
class ActionCandidate:
    action_id:str; domain:str; actor_id:str; intent:str; action_type:str; irreversible:bool; timestamp_plan:str
    timestamp_exec:str|None=None
    payload:dict[str,Any]=field(default_factory=dict)
@dataclass
class PeripheralSignalPacket:
    action_id:str; domain:str
    extra_metrics:dict[str,Any]=field(default_factory=dict)
    unknowns:list[str]=field(default_factory=list)
    risk_flags:list[str]=field(default_factory=list)
    contradictions:list[str]=field(default_factory=list)
    evidence_refs:list[str]=field(default_factory=list)
    recommended_gate:GateHint='NONE'
    can_emit_act:bool=False
    def assert_non_sovereign(self)->None:
        if self.can_emit_act: raise AssertionError('PERIPHERY_CANNOT_EMIT_ACT')
    def add_unknown(self, code:str)->None:
        if code not in self.unknowns: self.unknowns.append(code)
    def add_risk(self, code:str)->None:
        if code not in self.risk_flags: self.risk_flags.append(code)
    def add_contradiction(self, code:str)->None:
        if code not in self.contradictions: self.contradictions.append(code)
