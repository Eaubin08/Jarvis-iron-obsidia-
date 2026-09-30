"""Zero-dependency providers used to validate the standalone boundary."""
from __future__ import annotations

import re

from jarvis.contracts import ContextSnapshot, JarvisEvent


class StubMemory:
    def __init__(self) -> None:
        self.events: list[JarvisEvent] = []

    def remember(self, event: JarvisEvent) -> None:
        self.events.append(event)

    def context(self) -> ContextSnapshot:
        return ContextSnapshot(
            summary=f"{len(self.events)} local event(s)",
            metadata={"provider": "stub"},
        )


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold(), flags=re.UNICODE))


class StubCognition:
    """Tiny local presence layer for the standalone V0.

    This is deliberately not a general intelligence provider. It gives short,
    predictable acknowledgements for common conversational phrases so the HUD
    feels responsive while Brody/Obsidia remain replaceable future providers.
    """

    def try_respond(self, user_input: str, context: ContextSnapshot) -> str | None:
        """Return only deterministic local-presence answers.

        Unknown requests return None so a governed cognition provider may
        handle them. This method never performs actions.
        """
        text = _normalize(user_input)

        exact = {
            "bonjour": "Salut.",
            "salut": "Salut.",
            "coucou": "Salut.",
            "ça va": "Oui, je suis là.",
            "ca va": "Oui, je suis là.",
            "tu m entends": "Oui, je t'entends.",
            "tu m entends bien": "Oui, je t'entends.",
            "attends": "D'accord.",
            "attend": "D'accord.",
            "continue": "Je continue.",
            "continuer": "Je continue.",
            "merci": "Avec plaisir.",
            "au revoir": "À plus.",
            "a plus": "À plus.",
            "ok": "D'accord.",
            "d accord": "D'accord.",
            "comment vas tu": "Ça va, je suis opérationnel.",
            "comment va tu": "Ça va, je suis opérationnel.",
            "comment vas tu aujourd hui": "Ça va, je suis opérationnel.",
            "comment va tu aujourd hui": "Ça va, je suis opérationnel.",
            "qui es tu": "Je suis Jarjar, ton assistant local en construction.",
            "qui est tu": "Je suis Jarjar, ton assistant local en construction.",
            "quelles sont tes capacités": "Pour l'instant, je t'écoute, je te réponds et je garde une courte conversation ouverte.",
            "quelle sont tes capacités": "Pour l'instant, je t'écoute, je te réponds et je garde une courte conversation ouverte.",
            "que peux tu faire": "Pour l'instant, je t'écoute, je te réponds et je garde une courte conversation ouverte.",
        }
        if text in exact:
            return exact[text]

        if "tu m entends" in text:
            return "Oui, je t'entends."
        if text.startswith("qu est ce que tu comprends") or text.startswith("que comprends tu"):
            return "Je t'écoute et je comprends ta phrase."
        if "on peut encore continuer" in text or text.startswith("on continue"):
            return "Oui, on continue."
        if "comment vas tu" in text or "comment va tu" in text:
            return "Ça va, je suis opérationnel."
        if "capacités" in text or "capacites" in text or "que peux tu faire" in text:
            return "Pour l'instant, je t'écoute, je te réponds et je garde une courte conversation ouverte."
        if text.startswith("hey jarvis"):
            remainder = text.removeprefix("hey jarvis").strip()
            if not remainder:
                return "Oui ?"
            if remainder in exact:
                return exact[remainder]

        return None

    def respond(self, user_input: str, context: ContextSnapshot) -> str:
        local = self.try_respond(user_input, context)
        if local is not None:
            return local
        # Preserve the original deterministic standalone stub contract.
        # The live router calls try_respond() directly and therefore still
        # escalates unknown language to Qwen/Brody instead of stopping here.
        return f"JARVIS_V0: {user_input.strip()}"
