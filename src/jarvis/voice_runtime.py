"""Jarvis-owned conversational voice runtime.

Audio engines are providers. This module owns turn state, follow-up and
barge-in semantics; it contains no model-specific code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .contracts import SpeechHandle, SpeechToTextProvider, TextToSpeechProvider


class VoiceState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


@dataclass
class ConversationVoiceRuntime:
    stt: SpeechToTextProvider
    tts: TextToSpeechProvider
    state: VoiceState = VoiceState.IDLE
    follow_up_open: bool = False
    _speech: SpeechHandle | None = field(default=None, init=False, repr=False)

    def transcribe_turn(self, audio: bytes) -> str:
        self.state = VoiceState.LISTENING
        try:
            text = self.stt.transcribe(audio).strip()
        finally:
            self.state = VoiceState.IDLE
        if not text:
            raise ValueError("empty transcript")
        return text

    def speak(self, text: str, *, open_follow_up: bool = True) -> SpeechHandle:
        if not text.strip():
            raise ValueError("speech text must not be empty")
        self._speech = self.tts.speak(text)
        self.state = VoiceState.SPEAKING
        self.follow_up_open = open_follow_up
        return self._speech

    def barge_in(self) -> None:
        if self._speech is not None:
            self._speech.cancel()
            self._speech = None
        self.state = VoiceState.LISTENING
        self.follow_up_open = True

    def speech_finished(self) -> None:
        self._speech = None
        self.state = VoiceState.IDLE
