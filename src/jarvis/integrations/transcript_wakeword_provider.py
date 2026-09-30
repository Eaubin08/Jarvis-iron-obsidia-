"""Local transcript-match wake provider behind Jarvis WakeWordProvider."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from jarvis.contracts import SpeechToTextProvider


def _normalize_phrase(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold(), flags=re.UNICODE))


def _wake_variants(phrase: str) -> tuple[str, ...]:
    normalized = _normalize_phrase(phrase)
    variants = {normalized}
    if normalized == "hey jarvis":
        variants.update({
            "hey jarvis",
            "hé jarvis",
            "eh jarvis",
            "et jarvis",
            "jarvis",
            "hey j arvisse",
            "j arvisse hey j arvisse",
            "j ai revis",
            "j ai revis statue",
            "j ai revis status",
        })
    return tuple(sorted(variants))


@dataclass
class TranscriptWakeWordProvider:
    """Detect a configurable wake phrase using a local STT provider.

    Matching is exact after normalization, with a narrowly scoped compatibility
    set for the default "hey jarvis" phrase based on observed/local likely
    Whisper transcriptions on the target Windows microphone.
    """

    stt: SpeechToTextProvider
    phrase: str = "hey jarvis"
    last_transcript: str = field(default="", init=False)
    last_normalized_transcript: str = field(default="", init=False)

    def __post_init__(self) -> None:
        normalized = _normalize_phrase(self.phrase)
        if not normalized:
            raise ValueError("wake phrase must not be empty")
        self._normalized_phrase = normalized
        self._accepted_variants = _wake_variants(self.phrase)

    def detect(self, audio: bytes) -> bool:
        if not audio:
            raise ValueError("audio must not be empty")
        transcript = self.stt.transcribe(audio)
        normalized = _normalize_phrase(transcript)
        self.last_transcript = transcript
        self.last_normalized_transcript = normalized
        if not normalized:
            return False

        haystack = f" {normalized} "
        for variant in self._accepted_variants:
            if f" {variant} " in haystack:
                return True
        return False
