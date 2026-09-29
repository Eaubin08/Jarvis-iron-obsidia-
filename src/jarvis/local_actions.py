"""Jarvis-owned local capabilities used before OS integrations exist."""
from __future__ import annotations

from dataclasses import dataclass

from .contracts import (
    ActionRequest,
    ActionResult,
    Capability,
    ContextSnapshot,
    PermissionDecision,
    RiskClass,
)


class LocalPermissionPolicy:
    def evaluate(self, request: ActionRequest, context: ContextSnapshot) -> PermissionDecision:
        if request.risk in {RiskClass.SENSITIVE, RiskClass.DESTRUCTIVE, RiskClass.EXTERNAL_IMPACT}:
            return PermissionDecision.ASK
        return PermissionDecision.ALLOW


@dataclass
class SystemBackend:
    name: str = "jarvis.system"
    priority: int = 0

    def can_execute(self, request: ActionRequest, capability: Capability) -> bool:
        return capability.backend_family == "system" and request.capability == "system.status"

    def execute(self, request: ActionRequest) -> ActionResult:
        return ActionResult(True, "JARVIS_IRON_STATUS: READY", backend=self.name)
