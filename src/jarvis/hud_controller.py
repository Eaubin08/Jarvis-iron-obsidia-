"""Thread-safe Jarjar HUD controller.

The controller owns no cognition. Callbacks are injected so the future Brody /
Obsidia cognition stack can replace the current provider without changing HUD.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .hud_state import HUDModel, HUDState


@dataclass
class HUDController:
    model: HUDModel
    text_handler: Callable[[str], str]
    voice_turn_handler: Callable[[], tuple[str, str] | None] | None = None
    follow_up_turn_handler: Callable[[], tuple[str, str] | None] | None = None
    response_source: Callable[[], str] | None = None
    conversation_idle_seconds: float = 20.0

    def _current_source(self) -> str:
        if self.response_source is None:
            return ""
        return self.response_source().strip()

    def _jarjar_label(self) -> str:
        source = self._current_source()
        return f"JARJAR · {source}" if source else "JARJAR"

    @staticmethod
    def _governance_phase(reply: str, source: str) -> str:
        if not source.startswith("OBSIDIA/GOVERNED_"):
            return ""
        value = " ".join(reply.casefold().split())
        if "rollback" in value:
            if "prépar" in value or "prepar" in value:
                return "ROLLBACK_PREPARE"
            if "exécuté" in value or "execute" in value:
                return "ROLLBACK_EXECUTE"
            if "refus" in value or "non exécut" in value or "indisponible" in value:
                return "BLOCKED"
        if "prépar" in value or "prepare" in value:
            return "PREPARE"
        if "confirme" in value and ("attente" in value or "autoriser" in value):
            return "HUMAN_CONFIRM"
        if "exécuté et prouvé" in value or "créé et prouvé" in value or "appliqué et prouvé" in value:
            return "EXECUTE"
        if "refus" in value or "non exécut" in value or "non créé" in value or "non appliqué" in value:
            return "BLOCKED"
        if "annul" in value:
            return "CANCELLED"
        return "GOVERNED"

    def _sync_governance_surface(self, reply: str) -> None:
        source = self._current_source()
        governed = source.startswith("OBSIDIA/GOVERNED_")
        self.model.set_governance(
            active=governed,
            decision_authority="KX108_ONLY" if governed else "",
            source=source if governed else "",
            phase=self._governance_phase(reply, source) if governed else "",
        )

    def submit_text(self, text: str) -> str:
        clean = text.strip()
        if not clean:
            raise ValueError("empty HUD text input")

        self.model.append("YOU", clean)
        self.model.set_state(HUDState.THINKING)
        try:
            reply = self.text_handler(clean).strip()
            if not reply:
                raise ValueError("empty Jarjar response")
            self.model.append(self._jarjar_label(), reply)
            self._sync_governance_surface(reply)
            return reply
        except Exception:
            self.model.set_state(HUDState.ERROR)
            raise
        finally:
            if self.model.state is not HUDState.ERROR:
                self.model.set_state(HUDState.IDLE)

    def _run_voice_handler(
        self,
        handler: Callable[[], tuple[str, str] | None] | None,
        *,
        missing_message: str,
    ) -> tuple[str, str] | None:
        if not self.model.voice_enabled:
            raise RuntimeError("voice mode is disabled")
        if handler is None:
            raise RuntimeError(missing_message)

        self.model.set_state(HUDState.LISTENING)
        try:
            result = handler()
            if result is None:
                if self.model.session_open:
                    self.model.set_state(HUDState.LISTENING)
                else:
                    self.model.set_state(HUDState.IDLE)
                return None
            transcript, reply = result
            transcript = transcript.strip()
            reply = reply.strip()
            if not transcript or not reply:
                raise ValueError("voice turn returned empty transcript or reply")
            self.model.append("YOU", transcript)
            self.model.append(self._jarjar_label(), reply)
            self._sync_governance_surface(reply)
            if self.model.session_open:
                self.model.set_state(HUDState.LISTENING)
            else:
                self.model.set_state(HUDState.IDLE)
            return transcript, reply
        except Exception:
            self.model.set_state(HUDState.ERROR)
            raise

    def run_voice_turn(self) -> tuple[str, str] | None:
        return self._run_voice_handler(
            self.voice_turn_handler,
            missing_message="voice turn handler is not configured",
        )

    def run_follow_up_turn(self) -> tuple[str, str] | None:
        return self._run_voice_handler(
            self.follow_up_turn_handler,
            missing_message="follow-up voice handler is not configured",
        )

    def voice_finished(self) -> None:
        if self.model.session_open:
            self.model.set_state(HUDState.LISTENING)
        else:
            self.model.set_state(HUDState.IDLE)

    def toggle_voice(self) -> bool:
        new_value = not self.model.voice_enabled
        self.model.set_voice_enabled(new_value)
        if not new_value:
            self.model.set_state(HUDState.IDLE)
        return new_value
