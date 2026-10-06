"""Standalone text-only runtime.\n\nThis module is intentionally non-canonical for Jarjar live HUD/voice execution.\nThe canonical live composition root is :mod:`jarvis.live_runtime`.\n"""
from __future__ import annotations

from dataclasses import dataclass, field

from .actions import ActionRouter
from .contracts import CognitionProvider, JarvisEvent, MemoryProvider
from .context import ContextAssembler
from .events import EventBus
from .fast_intent import FastIntentRouter


@dataclass
class TextRuntime:
    cognition: CognitionProvider
    memory: MemoryProvider
    events: EventBus = field(default_factory=EventBus)
    session_id: str = "local-text"
    fast_intent: FastIntentRouter | None = None
    actions: ActionRouter | None = None
    context_assembler: ContextAssembler | None = None

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

        if self.context_assembler is None:
            context = self.memory.context()
        else:
            context = self.context_assembler.build(
                session_id=self.session_id,
                request=text,
            )
        self.events.publish(
            JarvisEvent(
                kind="context.built",
                source="text_runtime",
                payload={"summary": context.summary, "provenance": list(context.provenance)},
                session_id=self.session_id,
                causation_id=heard.event_id,
            )
        )

        if self.fast_intent is not None and self.actions is not None:
            match = self.fast_intent.route(text, session_id=self.session_id)
            if match is not None:
                self.events.publish(
                    JarvisEvent(
                        kind="action.requested",
                        source="fast_intent",
                        payload={"capability": match.request.capability, "rule": match.rule},
                        session_id=self.session_id,
                        causation_id=heard.event_id,
                    )
                )
                result = self.actions.execute(match.request, context)
                self.events.publish(
                    JarvisEvent(
                        kind="action.completed" if result.ok else "action.failed",
                        source="action_router",
                        payload={
                            "capability": match.request.capability,
                            "backend": result.backend,
                            "message": result.message,
                        },
                        session_id=self.session_id,
                        causation_id=heard.event_id,
                    )
                )
                return result.message

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
