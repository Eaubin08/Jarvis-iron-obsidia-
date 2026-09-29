"""Local transcript-match wake provider behind Jarvis WakeWordProvider."""
from __future__ import annotations

import re
from dataclasses import dataclass

from jarvis.contracts import SpeechToTextProvider


def _normalize_phrase(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold(), flags=re.UNICODE))


@dataclass
class TranscriptWakeWordProvider:
    """Detect a configurable wake phrase using a local STT provider."""

    stt: SpeechToTextProvider
    phrase: str = "hey jarvis"

    def __post_init__(self) -> None:
        normalized = _normalize_phrase(self.phrase)
        if not normalized:
            raise ValueError("wake phrase must not be empty")
        self._normalized_phrase = normalized

    def detect(self, audio: bytes) -> bool:
        if not audio:
            raise ValueError("audio must not be empty")
        transcript = self.stt.transcribe(audio)
        normalized = _normalize_phrase(transcript)
        if not normalized:
            return False
        haystack = f" {normalized} "
        needle = f" {self._normalized_phrase} "
        return needle in haystack
