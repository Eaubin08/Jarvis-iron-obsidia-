"""Minimal provider-driven Jarvis core."""

from __future__ import annotations

from dataclasses import dataclass, field

from .actions import ActionRouter
from .fast_intent import FastIntentRouter

from .contracts import CognitionProvider, MemoryProvider


@dataclass
class JarvisCore:
    cognition: CognitionProvider
    memory: MemoryProvider
    fast_intent: FastIntentRouter | None = None
    actions: ActionRouter | None = None
    last_source: str = field(default="LOCAL", init=False)

    def handle_text(self, text: str) -> str:
        context = self.memory.context()
        if self.fast_intent is not None and self.actions is not None:
            match = self.fast_intent.route(text, session_id="jarvis-core")
            if match is not None:
                result = self.actions.execute(match.request, context)
                backend = (result.backend or "ACTION").upper()
                self.last_source = f"ACTION/{backend}"
                return result.message
            guarded = self.fast_intent.local_guard_response(text)
            if guarded is not None:
                self.last_source = "LOCAL/GUARD"
                return guarded
        reply = self.cognition.respond(text, context)
        route = getattr(self.cognition, "last_route", None)
        labels = {
            "local": "LOCAL",
            "obsidia_local": "OBSIDIA/LOCAL",
            "vision": "QWEN-VL",
            "qwen_live": "QWEN/LIVE",
            "qwen": "QWEN",
            "qwen_fallback": "QWEN/FALLBACK",
            "brody": "BRODY/OBSIDIA",
            "brody_fallback": "BRODY/OBSIDIA/FALLBACK",
            "local_fallback": "LOCAL/FALLBACK",
        }
        self.last_source = labels.get(route, "COGNITION")
        return reply
