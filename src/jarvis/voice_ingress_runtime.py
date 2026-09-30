"""Bridge from wake-triggered or follow-up input into conversational voice state."""
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

    def capture_follow_up(self, duration_seconds: float) -> str:
        """Capture a follow-up turn without re-running wake-word detection."""
        if not self.conversation.follow_up_open:
            raise RuntimeError("follow-up window is not open")

        audio = self.wake_input.microphone.capture(duration_seconds)
        if not audio:
            raise ValueError("microphone returned empty audio")

        transcript = self.wake_input.stt.transcribe(audio).strip()
        if not transcript:
            raise ValueError("empty follow-up transcript")

        return self.conversation.accept_transcript(transcript)
