"""Streaming voice ingress for the Jarjar desktop runtime.

Wake detection is cheap and continuous. Whisper is invoked only after the
wake detector fires and the utterance recorder reaches end-of-speech.
"""
from __future__ import annotations

from dataclasses import dataclass

from .voice_runtime import ConversationVoiceRuntime


@dataclass
class StreamingVoiceIngress:
    microphone: object
    wake_word: object
    stt: object
    conversation: ConversationVoiceRuntime
    chunk_samples: int = 1280
    max_utterance_seconds: float = 8.0
    silence_seconds: float = 0.65
    rms_threshold: int = 300

    def capture_and_begin_turn(self, _duration_seconds: float = 0.0) -> str | None:
        reset = getattr(self.wake_word, "reset", None)
        if callable(reset):
            reset()

        for chunk in self.microphone.iter_chunks(chunk_samples=self.chunk_samples):
            if self.wake_word.detect(chunk):
                break

        audio = self.microphone.capture_until_silence(
            max_seconds=self.max_utterance_seconds,
            silence_seconds=self.silence_seconds,
            rms_threshold=self.rms_threshold,
        )
        if not audio:
            return None
        transcript = self.stt.transcribe(audio).strip()
        if not transcript:
            return None
        return self.conversation.accept_transcript(transcript)

    def capture_follow_up(self, _duration_seconds: float = 0.0) -> str:
        if not self.conversation.follow_up_open:
            raise RuntimeError("follow-up window is not open")
        audio = self.microphone.capture_until_silence(
            max_seconds=self.max_utterance_seconds,
            silence_seconds=self.silence_seconds,
            rms_threshold=self.rms_threshold,
        )
        if not audio:
            raise ValueError("empty follow-up transcript")
        transcript = self.stt.transcribe(audio).strip()
        if not transcript:
            raise ValueError("empty follow-up transcript")
        return self.conversation.accept_transcript(transcript)
