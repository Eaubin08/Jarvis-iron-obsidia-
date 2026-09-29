"""Bridge from wake-triggered input into conversational voice state."""
from __future__ import annotations

from dataclasses import dataclass

from .voice_runtime import ConversationVoiceRuntime
from .wake_input_runtime import WakeInputRuntime


@dataclass
class VoiceIngressRuntime:
    wake_input: WakeInputRuntime
    conversation: ConversationVoiceRuntime

    def capture_and_begin_turn(self, duration_seconds: float) -> str | None:
        result = self.wake_input.capture_once(duration_seconds)
        if not result.woke:
            return None
        if result.transcript is None:
            raise ValueError("wake input returned no transcript")
        return self.conversation.accept_transcript(result.transcript)
