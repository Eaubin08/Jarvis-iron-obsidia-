"""Cognition composition for Jarjar.

Presence reactions stay local/instant. Unknown conversational requests are
delegated to the governed Obsidia stack boundary. Failure degrades to the
standalone V0 presence layer instead of crashing the HUD.
"""
from __future__ import annotations

from dataclasses import dataclass

from jarvis.contracts import CognitionProvider, ContextSnapshot


@dataclass
class GovernedCognitionBridge:
    local_presence: object
    governed_stack: CognitionProvider

    def respond(self, user_input: str, context: ContextSnapshot) -> str:
        try_local = getattr(self.local_presence, "try_respond", None)
        if callable(try_local):
            local = try_local(user_input, context)
            if isinstance(local, str) and local.strip():
                return local.strip()

        try:
            answer = self.governed_stack.respond(user_input, context).strip()
            if answer:
                return answer
        except Exception:
            # Standalone Jarjar must remain usable while the external stack is
            # stopped. The local provider owns the degraded-mode wording.
            pass

        return self.local_presence.respond(user_input, context).strip()
