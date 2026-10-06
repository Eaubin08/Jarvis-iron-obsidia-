"""Jarvis-owned action routing.

Backends are ordered by structure/precision, never by donor identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import (
    ActionBackend,
    ActionRequest,
    ActionResult,
    CapabilityRegistry,
    ContextSnapshot,
    PermissionDecision,
    PermissionPolicy,
)


@dataclass
class ActionRouter:
    registry: CapabilityRegistry
    permission_policy: PermissionPolicy
    backends: list[ActionBackend] = field(default_factory=list)

    def execute(self, request: ActionRequest, context: ContextSnapshot) -> ActionResult:
        capability = self.registry.resolve(request)
        if capability is None:
            return ActionResult(False, f"unknown capability: {request.capability}")

        decision = self.permission_policy.evaluate(request, context)
        if decision is PermissionDecision.DENY:
            reason = getattr(self.permission_policy, "deny_reason", "permission denied")
            return ActionResult(False, str(reason))
        if decision is PermissionDecision.ASK:
            return ActionResult(False, "explicit approval required")

        for backend in sorted(self.backends, key=lambda item: item.priority):
            if backend.can_execute(request, capability):
                result = backend.execute(request)
                if result.backend is None:
                    return ActionResult(
                        ok=result.ok,
                        message=result.message,
                        data=result.data,
                        backend=backend.name,
                        started_at=result.started_at,
                        finished_at=result.finished_at,
                        evidence_refs=result.evidence_refs,
                    )
                return result

        return ActionResult(False, "no compatible action backend")
