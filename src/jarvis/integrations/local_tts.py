"""Jarvis-owned cancellable local speech adapter.

The engine is injected. Model/voice acquisition remains outside this adapter,
so source code, engine package and voice assets can be licensed independently.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import Event, Thread
from typing import Protocol


class SpeechEngine(Protocol):
    def synthesize(self, text: str) -> bytes: ...
    def play(self, audio: bytes, stop: Event) -> None: ...


@dataclass
class LocalSpeechHandle:
    stop: Event
    thread: Thread

    def cancel(self) -> None:
        self.stop.set()

    def wait(self, timeout: float | None = None) -> None:
        self.thread.join(timeout)


class LocalTTS:
    def __init__(self, engine: SpeechEngine):
        self.engine = engine

    def speak(self, text: str) -> LocalSpeechHandle:
        if not text.strip():
            raise ValueError("speech text must not be empty")
        stop = Event()

        def run() -> None:
            audio = self.engine.synthesize(text)
            if not stop.is_set():
                self.engine.play(audio, stop)

        thread = Thread(target=run, name="jarvis-tts", daemon=True)
        thread.start()
        return LocalSpeechHandle(stop, thread)
