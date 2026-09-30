"""
X-108 Context Boundary — final sovereignty gate before any context packet
is presented to the kernel. Enforces read-only, no-act, no-write invariants.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_BOUNDARY_INVARIANTS = {
    "readonly": True,
    "context_signal_only": True,
    "decision_authority": "KX108_ONLY",
    "allowed_to_decide": False,
    "allowed_to_act": False,
    "memory_write": False,
    "kernel_mutation": False,
}


@dataclass
class BoundaryCheckResult:
    packet_id: str
    passed: bool
    violations: list[str] = field(default_factory=list)
    readonly: bool = True
    decision_authority: str = "KX108_ONLY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "passed": self.passed,
            "violations": self.violations,
            "readonly": self.readonly,
            "decision_authority": self.decision_authority,
        }


def check_x108_context_boundary(packet: dict[str, Any]) -> BoundaryCheckResult:
    packet_id = packet.get("packet_id", "unknown")
    violations: list[str] = []

    for key, expected in _BOUNDARY_INVARIANTS.items():
        actual = packet.get(key)
        if actual != expected:
            violations.append(f"BOUNDARY_VIOLATION:{key}=={actual!r} required {expected!r}")

    return BoundaryCheckResult(
        packet_id=packet_id,
        passed=len(violations) == 0,
        violations=violations,
        readonly=True,
        decision_authority="KX108_ONLY",
    )
