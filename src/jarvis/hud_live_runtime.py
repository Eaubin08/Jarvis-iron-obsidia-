"""Live voice bridge between the Jarjar HUD and canonical voice providers."""
from __future__ import annotations

from dataclasses import dataclass

from .core import JarvisCore
from .voice_ingress_runtime import VoiceIngressRuntime
from .voice_runtime import ConversationVoiceRuntime


@dataclass
class HUDLiveVoiceBridge:
    ingress: VoiceIngressRuntime
    core: JarvisCore
    conversation: ConversationVoiceRuntime
    capture_seconds: float = 5.0

    def _respond(self, transcript: str) -> tuple[str, str]:
        reply = self.core.handle_text(transcript).strip()
        if not reply:
            raise ValueError("empty cognition response")

        handle = self.conversation.speak(reply, open_follow_up=True)
        wait = getattr(handle, "wait", None)
        if callable(wait):
            wait(60.0)
        self.conversation.speech_finished()
        return transcript, reply

    def run_wake_turn(self) -> tuple[str, str] | None:
        """Capture one turn that must contain the configured wake phrase."""
        if self.capture_seconds <= 0:
            raise ValueError("capture_seconds must be positive")

        # A fresh always-listening cycle must never inherit an old follow-up.
        self.conversation.follow_up_open = False
        transcript = self.ingress.capture_and_begin_turn(self.capture_seconds)
        if transcript is None:
            return None
        return self._respond(transcript)

    def run_follow_up_turn(self) -> tuple[str, str] | None:
        """Capture one wake-free follow-up after a successful spoken reply.

        Silence/empty transcription closes the follow-up window and is treated
        as a normal return to wake-word monitoring, not as a HUD failure.
        """
        if not self.conversation.follow_up_open:
            return None
        try:
            transcript = self.ingress.capture_follow_up(self.capture_seconds)
        except ValueError as exc:
            if "empty" not in str(exc).casefold():
                raise
            self.conversation.follow_up_open = False
            return None
        return self._respond(transcript)

    def run_turn(self) -> tuple[str, str] | None:
        """Backward-compatible manual turn semantics."""
        if self.conversation.follow_up_open:
            return self.run_follow_up_turn()
        return self.run_wake_turn()

    def speak_text_reply(self, reply: str) -> None:
        reply = reply.strip()
        if not reply:
            return
        handle = self.conversation.speak(reply, open_follow_up=True)
        wait = getattr(handle, "wait", None)
        if callable(wait):
            wait(60.0)
        self.conversation.speech_finished()
