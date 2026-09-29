"""Standalone text runtime for F1.

This is Jarvis-owned orchestration. Providers remain replaceable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import CognitionProvider, JarvisEvent, MemoryProvider
from .events import EventBus


@dataclass
class TextRuntime:
    cognition: CognitionProvider
    memory: MemoryProvider
    events: EventBus = field(default_factory=EventBus)
    session_id: str = "local-text"

    def handle(self, text: str) -> str:
        text = text.strip()
        if not text:
            raise ValueError("text must not be empty")

        heard = JarvisEvent(
            kind="voice.heard",
            source="text_runtime",
            payload={"text": text, "modality": "text"},
            session_id=self.session_id,
        )
        self.events.publish(heard)
        self.memory.remember(heard)

        context = self.memory.context()
        self.events.publish(
            JarvisEvent(
                kind="context.built",
                source="text_runtime",
                payload={
                    "summary": context.summary,
                    "provenance": list(context.provenance),
                },
                session_id=self.session_id,
                causation_id=heard.event_id,
            )
        )

        self.events.publish(
            JarvisEvent(
                kind="cognition.started",
                source="text_runtime",
                payload={"provider": type(self.cognition).__name__},
                session_id=self.session_id,
                causation_id=heard.event_id,
            )
        )
        try:
            reply = self.cognition.respond(text, context)
        except Exception as exc:
            self.events.publish(
                JarvisEvent(
                    kind="cognition.failed",
                    source="text_runtime",
                    payload={"error_type": type(exc).__name__, "message": str(exc)},
                    session_id=self.session_id,
                    causation_id=heard.event_id,
                )
            )
            raise

        completed = JarvisEvent(
            kind="cognition.completed",
            source="text_runtime",
            payload={"text": reply},
            session_id=self.session_id,
            causation_id=heard.event_id,
        )
        self.events.publish(completed)
        self.memory.remember(completed)
        return reply
