"""
Context Packet Validator — enforces sovereignty invariants on a context packet dict.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_REQUIRED_READONLY_FIELDS = {
    "readonly": True,
    "context_signal_only": True,
    "decision_authority": "KX108_ONLY",
    "allowed_to_decide": False,
    "allowed_to_act": False,
    "kernel_mutation": False,
    "memory_write": False,
}


@dataclass
class ContextPacketValidationResult:
    packet_id: str
    valid: bool
    violations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "valid": self.valid,
            "violations": self.violations,
        }


def validate_context_packet(packet: dict[str, Any]) -> ContextPacketValidationResult:
    packet_id = packet.get("packet_id", "unknown")
    violations: list[str] = []

    for field_name, expected in _REQUIRED_READONLY_FIELDS.items():
        actual = packet.get(field_name)
        if actual != expected:
            violations.append(
                f"INVARIANT_VIOLATED:{field_name}=={actual!r} expected {expected!r}"
            )

    return ContextPacketValidationResult(
        packet_id=packet_id,
        valid=len(violations) == 0,
        violations=violations,
    )
