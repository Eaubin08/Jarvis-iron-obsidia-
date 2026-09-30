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
    r"\b(kernel|carnel|karnel)\b",
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


def is_short_followup(text: str) -> bool:
    value = " ".join(text.casefold().split())
    if not value:
        return False
    tokens = value.split()
    if len(tokens) > 14:
        return False
    starters = (
        "oui", "non", "continue", "continues", "pourquoi", "comment",
        "explique", "developpe", "développe", "et ", "donc ", "mais ",
        "du coup", "dans tout ça", "dans tout ca", "et après", "et apres",
    )
    return any(value == item.strip() or value.startswith(item) for item in starters)


@dataclass
class CostAwareCognitionRouter:
    local_presence: object
    governed_stack: CognitionProvider
    qwen: object | None = None
    vision: object | None = None
    pre_inference: object | None = None
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

    def _runtime_state_answer(self) -> str | None:
        trace = getattr(self.governed_stack, "last_trace", None)
        if not isinstance(trace, dict) or not trace:
            return None

        native = trace.get("native_memory_active")
        memory_mode = trace.get("memory_source_mode") or "UNKNOWN"
        memory_status = trace.get("memory_status") or "UNKNOWN"
        authority = trace.get("decision_authority") or "UNKNOWN"
        readonly = trace.get("readonly")
        voice_runtime = trace.get("voice_runtime") or "UNKNOWN"

        if native is True:
            memory_sentence = (
                "Native Memory est bien active sur le runtime connecté."
            )
        elif native is False:
            memory_sentence = (
                "Native Memory n'est pas active sur le runtime actuellement connecté ; "
                f"la source mémoire observée est {memory_mode}."
            )
        else:
            memory_sentence = (
                "L'état Native Memory n'est pas déterminable avec la dernière trace runtime."
            )

        readonly_sentence = (
            "Le runtime est déjà en lecture seule."
            if readonly is True
            else f"État readonly observé : {readonly!r}."
        )

        return (
            f"{memory_sentence} "
            f"{readonly_sentence} "
            f"Runtime Brody : {voice_runtime}. "
            f"Statut mémoire : {memory_status}. "
            f"Autorité : {authority}."
        )

    def respond(self, user_input: str, context: ContextSnapshot) -> str:
        try_local = getattr(self.local_presence, "try_respond", None)
        if callable(try_local):
            local = try_local(user_input, context)
            if isinstance(local, str) and local.strip():
                self.last_route = "local"
                return local.strip()

        # Canonical Obsidia pre-inference routing. Visual/environment
        # requests keep their dedicated Jarjar sensor path for now; the ported
        # router does not yet model those capabilities.
        pre_decision = None
        if (
            self.pre_inference is not None
            and not is_visual_query(user_input)
            and not is_live_environment_query(user_input)
        ):
            try:
                pre_decision = self.pre_inference.route(user_input)
            except Exception as exc:
                print(f"JARJAR_PRE_ROUTE: FALLBACK error={type(exc).__name__}: {exc}")
                pre_decision = None

        if pre_decision is not None and getattr(pre_decision, "is_confident", False):
            route = getattr(pre_decision, "route", "")

            if route == "runtime_state_readonly":
                answer = self._runtime_state_answer()
                if answer is None:
                    # Populate the runtime trace through the canonical Brody
                    # boundary, but never surface that semantic answer here.
                    self._brody(user_input, context)
                    answer = self._runtime_state_answer()
                if answer is not None:
                    self.last_route = "obsidia_local"
                    return answer

            direct = getattr(pre_decision, "direct_answer", None)
            if isinstance(direct, str) and direct.strip():
                self.last_route = "obsidia_local"
                return direct.strip()

            if route in {"brody", "lean_route_only", "domain_bridge", "obsidure_route_only"}:
                brody_input = user_input
                topic = getattr(pre_decision, "topic", {})
                if (
                    isinstance(topic, dict)
                    and topic.get("topic") == "OBSIDIA_BRODY_ROLE"
                    and "jarjar" in user_input.casefold()
                ):
                    # Jarjar is the local surface identity; Brody's canonical
                    # semantic/domain adapters know the underlying role as Brody.
                    # Rewrite only this already-classified identity alias so the
                    # real 8012 Domain Raccord can answer structurally.
                    brody_input = (
                        "Qu'est-ce que tu sais du projet Obsidia et de ton rôle Brody ?"
                    )
                answer = self._brody(brody_input, context)
                if answer:
                    self.last_route = "brody"
                    return answer

            if route == "fireworks":
                # Jarjar keeps inference local: the ported router's escalation
                # class is satisfied by the configured local Qwen provider.
                answer = self._qwen(user_input, context, live=False)
                if answer:
                    self.last_route = "qwen"
                    return answer
                answer = self._brody(user_input, context)
                if answer:
                    self.last_route = "brody_fallback"
                    return answer

        # Preserve conversational continuity: a short follow-up after a
        # successful Brody turn stays on Brody unless the user explicitly asks
        # for visual/environment context. This avoids stateless Qwen detours on
        # "oui", "pourquoi ?", "continue", "et après ?", etc.
        if (
            self.last_route in {"brody", "brody_fallback"}
            and is_short_followup(user_input)
            and not is_visual_query(user_input)
            and not is_live_environment_query(user_input)
        ):
            answer = self._brody(user_input, context)
            if answer:
                self.last_route = "brody"
                return answer

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
