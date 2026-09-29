"""Local capability registry for Jarvis-owned capabilities."""
from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import ActionRequest, Capability


@dataclass
class LocalCapabilityRegistry:
    _capabilities: dict[str, Capability] = field(default_factory=dict)

    def register(self, capability: Capability) -> None:
        if capability.name in self._capabilities:
            raise ValueError(f"capability already registered: {capability.name}")
        self._capabilities[capability.name] = capability

    def resolve(self, request: ActionRequest) -> Capability | None:
        return self._capabilities.get(request.capability)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._capabilities))
