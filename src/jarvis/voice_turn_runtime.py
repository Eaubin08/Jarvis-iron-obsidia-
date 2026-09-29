"""Canonical wake-triggered conversational turn composition."""
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

    def run_once(self, duration_seconds: float):
        transcript = self.ingress.capture_and_begin_turn(duration_seconds)
        if transcript is None:
            return None

        response = self.core.handle_text(transcript).strip()
        if not response:
            raise ValueError("empty cognition response")

        return self.conversation.speak(response, open_follow_up=True)
