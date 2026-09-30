"""Minimal provider-driven Jarvis core."""

from __future__ import annotations

from dataclasses import dataclass

from .actions import ActionRouter
from .fast_intent import FastIntentRouter

from .contracts import CognitionProvider, MemoryProvider


@dataclass
class JarvisCore:
    cognition: CognitionProvider
    memory: MemoryProvider
    fast_intent: FastIntentRouter | None = None
    actions: ActionRouter | None = None

    def handle_text(self, text: str) -> str:
        context = self.memory.context()
        if self.fast_intent is not None and self.actions is not None:
            match = self.fast_intent.route(text, session_id="jarvis-core")
            if match is not None:
                return self.actions.execute(match.request, context).message
            guarded = self.fast_intent.local_guard_response(text)
            if guarded is not None:
                return guarded
        return self.cognition.respond(text, context)
