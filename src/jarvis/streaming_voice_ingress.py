"""Streaming voice ingress for the Jarjar desktop runtime.

Wake detection is cheap and continuous. Whisper is invoked only after the
wake detector fires and the utterance recorder reaches end-of-speech.
"""
from __future__ import annotations

from dataclasses import dataclass
import time

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
    wake_speech_start_timeout: float = 3.0
    follow_up_start_timeout: float = 2.0

    def capture_and_begin_turn(self, _duration_seconds: float = 0.0) -> str | None:
        reset = getattr(self.wake_word, "reset", None)
        if callable(reset):
            reset()

        peak = 0.0
        last_report = time.monotonic()
        for chunk in self.microphone.iter_chunks(chunk_samples=self.chunk_samples):
            detected = self.wake_word.detect(chunk)
            score = float(getattr(self.wake_word, "last_score", 0.0))
            peak = max(peak, score)
            now = time.monotonic()
            if detected:
                print(
                    f"JARJAR_WAKE: DETECTED model={getattr(self.wake_word, 'last_model', '')} "
                    f"score={score:.3f} threshold={getattr(self.wake_word, 'threshold', 0.0):.3f}"
                )
                break
            if now - last_report >= 2.0:
                print(
                    f"JARJAR_WAKE: listening peak={peak:.3f} "
                    f"threshold={getattr(self.wake_word, 'threshold', 0.0):.3f}"
                )
                peak = 0.0
                last_report = now

        audio = self.microphone.capture_until_silence(
            max_seconds=self.max_utterance_seconds,
            silence_seconds=self.silence_seconds,
            rms_threshold=self.rms_threshold,
            speech_start_timeout=self.wake_speech_start_timeout,
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
            speech_start_timeout=self.follow_up_start_timeout,
        )
        if not audio:
            self.conversation.follow_up_open = False
            raise ValueError("empty follow-up transcript")
        transcript = self.stt.transcribe(audio).strip()
        if not transcript:
            raise ValueError("empty follow-up transcript")
        return self.conversation.accept_transcript(transcript)
