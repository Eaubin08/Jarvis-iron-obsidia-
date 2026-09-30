"""Streaming voice ingress for the Jarjar desktop runtime.

Wake detection is cheap and continuous. Whisper is invoked only after the
wake detector fires and the utterance recorder reaches end-of-speech.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
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
    on_wake: Callable[[], None] | None = None
    _pending_fragment: str = field(default="", init=False, repr=False)

    def capture_and_begin_turn(self, _duration_seconds: float = 0.0) -> str | None:
        reset = getattr(self.wake_word, "reset", None)
        if callable(reset):
            reset()

        peak = 0.0
        last_report = time.monotonic()
        chunks = self.microphone.iter_chunks(chunk_samples=self.chunk_samples)
        try:
            for chunk in chunks:
                detected = self.wake_word.detect(chunk)
                score = float(getattr(self.wake_word, "last_score", 0.0))
                peak = max(peak, score)
                now = time.monotonic()
                if detected:
                    print(
                        f"JARJAR_WAKE: DETECTED model={getattr(self.wake_word, 'last_model', '')} "
                        f"score={score:.3f} threshold={getattr(self.wake_word, 'threshold', 0.0):.3f}"
                    )
                    print("JARJAR_SESSION: OPEN")
                    if self.on_wake is not None:
                        self.on_wake()

                    # Release the continuous wake stream before opening the
                    # utterance recorder. Two simultaneous input streams can
                    # steal/drop the first words after the wake phrase.
                    close = getattr(chunks, "close", None)
                    if callable(close):
                        close()

                    audio = self.microphone.capture_until_silence(
                        max_seconds=self.max_utterance_seconds,
                        silence_seconds=self.silence_seconds,
                        rms_threshold=self.rms_threshold,
                        speech_start_timeout=self.wake_speech_start_timeout,
                    )
                    if not audio:
                        self.conversation.follow_up_open = False
                        print("JARJAR_SESSION: CLOSED (no speech after wake)")
                        return None
                    transcript = self.stt.transcribe(audio).strip()
                    if not transcript:
                        self.conversation.follow_up_open = False
                        print("JARJAR_SESSION: CLOSED (empty wake transcript)")
                        return None
                    return self.conversation.accept_transcript(transcript)

                if now - last_report >= 4.0:
                    if peak >= 0.10:
                        print(
                            f"JARJAR_WAKE: peak={peak:.3f} "
                            f"threshold={getattr(self.wake_word, 'threshold', 0.0):.3f}"
                        )
                    peak = 0.0
                    last_report = now
        finally:
            close = getattr(chunks, "close", None)
            if callable(close):
                close()


    @staticmethod
    def _looks_incomplete_fragment(text: str) -> bool:
        value = text.strip()
        if not value:
            return False
        tokens = value.split()
        # Conservative gate: only hold short transcripts that Whisper itself
        # marks as trailing/incomplete. Normal short commands still pass.
        return len(tokens) <= 8 and (
            value.endswith("...")
            or value.endswith("…")
        )

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
            print("JARJAR_SESSION: IDLE_WINDOW (no speech yet)")
            raise ValueError("empty follow-up transcript")
        transcript = self.stt.transcribe(audio).strip()
        if not transcript:
            raise ValueError("empty follow-up transcript")

        if self._pending_fragment:
            transcript = f"{self._pending_fragment} {transcript}".strip()
            print(f"JARJAR_STT: MERGED_PENDING transcript={transcript!r}")
            self._pending_fragment = ""

        if self._looks_incomplete_fragment(transcript):
            self._pending_fragment = transcript
            print(f"JARJAR_STT: HOLD_FRAGMENT transcript={transcript!r}")
            raise ValueError("empty follow-up transcript")

        return self.conversation.accept_transcript(transcript)
