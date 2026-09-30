"""Temporary cost/capability cognition router for Jarjar.

This is a replaceable V0 policy while the canonical OpenJarvis/Obsidia router
is not yet ready for Jarjar's full live context.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from jarvis.contracts import CognitionProvider, ContextSnapshot


_PROJECT_PATTERNS = (
    r"\bobsidia\b", r"\bx[- ]?108\b", r"\bbrody\b", r"\bkx108\b",
    r"\bjarvis[- ]iron\b", r"\bsource[- ]?pack\b", r"\bnative memory\b",
)
_ENV_PATTERNS = (
    r"\b(écran|ecran|moniteur|fenêtre|fenetre|caméra|camera|webcam)\b",
    r"\b(autour de moi|environnement|ce que tu vois|qu est ce que tu vois|que vois tu)\b",
    r"\b(application active|app active|fenêtre active|fenetre active)\b",
)


def _matches(text: str, patterns: tuple[str, ...]) -> bool:
    value = " ".join(text.casefold().split())
    return any(re.search(pattern, value) for pattern in patterns)


def is_project_query(text: str) -> bool:
    return _matches(text, _PROJECT_PATTERNS)


def is_live_environment_query(text: str) -> bool:
    return _matches(text, _ENV_PATTERNS)


@dataclass
class CostAwareCognitionRouter:
    local_presence: object
    governed_stack: CognitionProvider
    qwen: object | None = None

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

    def respond(self, user_input: str, context: ContextSnapshot) -> str:
        try_local = getattr(self.local_presence, "try_respond", None)
        if callable(try_local):
            local = try_local(user_input, context)
            if isinstance(local, str) and local.strip():
                return local.strip()

        # Environment: cheap local Qwen + live metadata first.
        if is_live_environment_query(user_input):
            answer = self._qwen(user_input, context, live=True)
            if answer:
                return answer
            answer = self._brody(user_input, context)
            if answer:
                return answer

        # Project/corpus: Brody has the better retrieval context.
        elif is_project_query(user_input):
            answer = self._brody(user_input, context)
            if answer:
                return answer
            answer = self._qwen(user_input, context, live=False)
            if answer:
                return answer

        # General free-form: local Qwen is the cheaper default.
        else:
            answer = self._qwen(user_input, context, live=False)
            if answer:
                return answer
            answer = self._brody(user_input, context)
            if answer:
                return answer

        return self.local_presence.respond(user_input, context).strip()


# Backward-compatible name while callers migrate.
GovernedCognitionBridge = CostAwareCognitionRouter
