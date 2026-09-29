"""Minimal provider-driven Jarvis core."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import CognitionProvider, MemoryProvider


@dataclass
class JarvisCore:
    cognition: CognitionProvider
    memory: MemoryProvider

    def handle_text(self, text: str) -> str:
        return self.cognition.respond(text, self.memory.context())
