"""Temporary cost/capability cognition router for Jarjar.

This is a replaceable V0 policy while the canonical OpenJarvis/Obsidia router
is not yet ready for Jarjar's full live context.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from jarvis.contracts import CognitionProvider, ContextSnapshot


_PROJECT_PATTERNS = (
    r"\b(obsidia|obsidian|obsidio)\b", r"\bx[- ]?108\b", r"\bbrody\b", r"\bkx108\b",
    r"\bjarvis[- ]iron\b", r"\bsource[- ]?pack\b", r"\bnative memory\b",
)
_ENV_PATTERNS = (
    r"\b(écrans?|ecrans?|moniteurs?|fenêtres?|fenetres?|caméras?|cameras?|webcams?)\b",
    r"\b(autour de moi|environnement|ce que tu vois|qu est ce que tu vois|que vois tu)\b",
    r"\b(application active|app active|fenêtre active|fenetre active)\b",
)

_VISUAL_PATTERNS = (
    r"\b(que vois tu|qu est ce que tu vois|ce que tu vois)\b",
    r"\b(lis|lire|décris|decris|analyse|regarde)\b.*\b(écran|ecran|caméra|camera|webcam|image|photo)\b",
    r"\b(à l écran|a l ecran|sur l écran|sur l ecran|sur la caméra|sur la camera|devant la caméra|devant la camera)\b",
)


def _matches(text: str, patterns: tuple[str, ...]) -> bool:
    value = " ".join(text.casefold().split())
    return any(re.search(pattern, value) for pattern in patterns)


def is_project_query(text: str) -> bool:
    return _matches(text, _PROJECT_PATTERNS)


def is_live_environment_query(text: str) -> bool:
    return _matches(text, _ENV_PATTERNS)


def is_visual_query(text: str) -> bool:
    return _matches(text, _VISUAL_PATTERNS)


@dataclass
class CostAwareCognitionRouter:
    local_presence: object
    governed_stack: CognitionProvider
    qwen: object | None = None
    vision: object | None = None
    last_route: str | None = field(default=None, init=False)

    def _qwen(self, user_input: str, context: ContextSnapshot, *, live: bool) -> str | None:
        if self.qwen is None:
            return None
        try:
            method = getattr(self.qwen, "respond_with_options", None)
            if callable(method):
                answer = method(user_input, context, include_live=live)
            else:
                answer = self.qwen.respond(user_input, context)
            answer = answer.strip()
            return answer or None
        except Exception:
            return None

    def _brody(self, user_input: str, context: ContextSnapshot) -> str | None:
        try:
            answer = self.governed_stack.respond(user_input, context).strip()
            return answer or None
        except Exception:
            return None

    def _vision(self, user_input: str, context: ContextSnapshot) -> str | None:
        if self.vision is None:
            return None
        try:
            answer = self.vision.respond(user_input, context).strip()
            return answer or None
        except Exception:
            return None

    def respond(self, user_input: str, context: ContextSnapshot) -> str:
        try_local = getattr(self.local_presence, "try_respond", None)
        if callable(try_local):
            local = try_local(user_input, context)
            if isinstance(local, str) and local.strip():
                self.last_route = "local"
                return local.strip()

        # Visual semantics require an actual vision provider. Fall back to
        # structured live metadata if vision is unavailable.
        if is_visual_query(user_input):
            answer = self._vision(user_input, context)
            if answer:
                self.last_route = "vision"
                return answer
            answer = self._qwen(user_input, context, live=True)
            if answer:
                self.last_route = "qwen_live"
                return answer
            answer = self._brody(user_input, context)
            if answer:
                self.last_route = "brody_fallback"
                return answer

        # Environment topology/status: cheap local Qwen + live metadata first.
        elif is_live_environment_query(user_input):
            answer = self._qwen(user_input, context, live=True)
            if answer:
                self.last_route = "qwen_live"
                return answer
            answer = self._brody(user_input, context)
            if answer:
                self.last_route = "brody_fallback"
                return answer

        # Project/corpus: Brody has the better retrieval context.
        elif is_project_query(user_input):
            answer = self._brody(user_input, context)
            if answer:
                self.last_route = "brody"
                return answer
            answer = self._qwen(user_input, context, live=False)
            if answer:
                self.last_route = "qwen_fallback"
                return answer

        # General free-form: local Qwen is the cheaper default.
        else:
            answer = self._qwen(user_input, context, live=False)
            if answer:
                self.last_route = "qwen"
                return answer
            answer = self._brody(user_input, context)
            if answer:
                self.last_route = "brody_fallback"
                return answer

        self.last_route = "local_fallback"
        return self.local_presence.respond(user_input, context).strip()


# Backward-compatible name while callers migrate.
GovernedCognitionBridge = CostAwareCognitionRouter
