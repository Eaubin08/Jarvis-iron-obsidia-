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

    def run_turn(self) -> tuple[str, str] | None:
        if self.capture_seconds <= 0:
            raise ValueError("capture_seconds must be positive")

        if self.conversation.follow_up_open:
            transcript = self.ingress.capture_follow_up(self.capture_seconds)
        else:
            transcript = self.ingress.capture_and_begin_turn(self.capture_seconds)
            if transcript is None:
                return None

        reply = self.core.handle_text(transcript).strip()
        if not reply:
            raise ValueError("empty cognition response")

        handle = self.conversation.speak(reply, open_follow_up=True)
        wait = getattr(handle, "wait", None)
        if callable(wait):
            wait(60.0)
        self.conversation.speech_finished()
        return transcript, reply

    def speak_text_reply(self, reply: str) -> None:
        reply = reply.strip()
        if not reply:
            return
        handle = self.conversation.speak(reply, open_follow_up=True)
        wait = getattr(handle, "wait", None)
        if callable(wait):
            wait(60.0)
        self.conversation.speech_finished()
