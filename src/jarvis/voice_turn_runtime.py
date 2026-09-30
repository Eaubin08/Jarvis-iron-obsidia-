"""Canonical conversational voice turn composition."""
from __future__ import annotations

from dataclasses import dataclass

from .core import JarvisCore
from .voice_ingress_runtime import VoiceIngressRuntime
from .voice_runtime import ConversationVoiceRuntime


@dataclass
class VoiceTurnRuntime:
    ingress: VoiceIngressRuntime
    core: JarvisCore
    conversation: ConversationVoiceRuntime

    def _respond(self, transcript: str):
        response = self.core.handle_text(transcript).strip()
        if not response:
            raise ValueError("empty cognition response")
        return self.conversation.speak(response, open_follow_up=True)

    def run_once(self, duration_seconds: float):
        transcript = self.ingress.capture_and_begin_turn(duration_seconds)
        if transcript is None:
            return None
        return self._respond(transcript)

    def run_follow_up_once(self, duration_seconds: float):
        """Run one conversational turn while the follow-up window is open."""
        transcript = self.ingress.capture_follow_up(duration_seconds)
        return self._respond(transcript)
