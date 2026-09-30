"""
Brody Response Contract — defines invariants for all Brody responses.
readonly=True, advisory_only=True, emits_act=False, emits_verdict=False always.
decision_authority=KX108_ONLY.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BrodyResponseContract:
    readonly: bool = True
    advisory_only: bool = True
    context_signal_only: bool = True
    emits_act: bool = False
    emits_verdict: bool = False
    decision_authority: str = "KX108_ONLY"
    memory_write: bool = False
    kernel_mutation: bool = False

    def validate(self) -> None:
        assert self.readonly is True, "BRODY_CONTRACT_VIOLATION:readonly"
        assert self.emits_act is False, "BRODY_CONTRACT_VIOLATION:emits_act"
        assert self.emits_verdict is False, "BRODY_CONTRACT_VIOLATION:emits_verdict"
        assert self.memory_write is False, "BRODY_CONTRACT_VIOLATION:memory_write"
        assert self.kernel_mutation is False, "BRODY_CONTRACT_VIOLATION:kernel_mutation"
        assert self.decision_authority == "KX108_ONLY", "BRODY_CONTRACT_VIOLATION:decision_authority"

    def to_dict(self) -> dict[str, Any]:
        return {
            "readonly": self.readonly,
            "advisory_only": self.advisory_only,
            "context_signal_only": self.context_signal_only,
            "emits_act": self.emits_act,
            "emits_verdict": self.emits_verdict,
            "decision_authority": self.decision_authority,
            "memory_write": self.memory_write,
            "kernel_mutation": self.kernel_mutation,
        }


BRODY_CONTRACT = BrodyResponseContract()
