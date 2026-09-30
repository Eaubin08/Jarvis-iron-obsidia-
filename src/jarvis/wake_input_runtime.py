"""Jarvis-owned wake-triggered input pipeline.

This module composes canonical provider seams only. It does not know which
microphone, wake-word engine, model or STT engine is behind those providers.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import MicrophoneProvider, SpeechToTextProvider, WakeWordProvider


@dataclass(frozen=True)
class WakeInputResult:
    woke: bool
    transcript: str | None = None


@dataclass
class WakeInputRuntime:
    microphone: MicrophoneProvider
    wake_word: WakeWordProvider
    stt: SpeechToTextProvider
    _previous_audio: bytes = field(default=b"", init=False, repr=False)

    def capture_once(self, duration_seconds: float) -> WakeInputResult:
        audio = self.microphone.capture(duration_seconds)
        if not audio:
            raise ValueError("microphone returned empty audio")

        # Rolling two-window buffer: a wake phrase split across capture
        # boundaries is still visible to the detector on the next pass.
        detection_audio = self._previous_audio + audio if self._previous_audio else audio
        self._previous_audio = audio

        if not self.wake_word.detect(detection_audio):
            return WakeInputResult(woke=False)

        # Transcript-based wake providers already ran STT during detect().
        # Reuse that transcript instead of paying a second CPU inference.
        cached = getattr(self.wake_word, "last_transcript", None)
        if isinstance(cached, str) and cached.strip():
            transcript = cached.strip()
        else:
            transcript = self.stt.transcribe(detection_audio).strip()

        if not transcript:
            raise ValueError("empty transcript after wake detection")

        # A successful wake consumes the rolling context so old wake words
        # cannot retrigger the next cycle.
        self._previous_audio = b""
        return WakeInputResult(woke=True, transcript=transcript)
