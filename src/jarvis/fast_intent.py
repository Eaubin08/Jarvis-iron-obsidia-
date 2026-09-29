"""Deterministic fast-intent routing for commands that need no cognition."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .contracts import ActionRequest


@dataclass(frozen=True)
class FastIntentMatch:
    request: ActionRequest
    rule: str


class FastIntentRouter:
    """Exact/bounded rules only. Ambiguity returns None and escalates."""

    def __init__(self) -> None:
        self._rules: list[tuple[str, Callable[[str], ActionRequest | None]]] = [
            ("status", self._status),
        ]

    def route(self, text: str, *, session_id: str = "default") -> FastIntentMatch | None:
        normalized = " ".join(text.strip().lower().split())
        if not normalized:
            return None
        for name, rule in self._rules:
            request = rule(normalized)
            if request is not None:
                return FastIntentMatch(
                    ActionRequest(
                        capability=request.capability,
                        arguments=request.arguments,
                        target=request.target,
                        source="fast_intent",
                        session_id=session_id,
                        risk=request.risk,
                        idempotency_key=request.idempotency_key,
                    ),
                    name,
                )
        return None

    @staticmethod
    def _status(text: str) -> ActionRequest | None:
        if text in {"status", "jarvis status", "statut", "statut jarvis"}:
            return ActionRequest("system.status")
        return None
