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


class KX108OnlyLivePermissionPolicy:
    """Fail-closed permission policy for the canonical live runtime.

    Readonly device inspection may execute locally. Any mutation must be
    represented by an explicit governed capability path before it can act.
    """

    deny_reason = "WORLD_ACTION_DRY_RUN_ONLY"

    def evaluate(self, request: ActionRequest, context: ContextSnapshot) -> PermissionDecision:
        if request.risk is RiskClass.READ_ONLY:
            return PermissionDecision.ALLOW
        return PermissionDecision.DENY


@dataclass
class SystemBackend:
    name: str = "jarvis.system"
    priority: int = 0

    def can_execute(self, request: ActionRequest, capability: Capability) -> bool:
        return capability.backend_family == "system" and request.capability == "system.status"

    def execute(self, request: ActionRequest) -> ActionResult:
        return ActionResult(True, "JARVIS_IRON_STATUS: READY", backend=self.name)
