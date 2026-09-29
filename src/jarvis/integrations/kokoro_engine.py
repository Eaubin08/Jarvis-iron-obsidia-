"""Kokoro synthesis engine behind Jarvis SpeechEngine."""
from __future__ import annotations

import io
import wave
from threading import Event


class KokoroEngine:
    def __init__(self, *, lang_code: str = "a", voice: str = "af_heart", sample_rate: int = 24000):
        self.lang_code = lang_code
        self.voice = voice
        self.sample_rate = sample_rate
        self._pipeline = None

    def _load(self):
        if self._pipeline is None:
            try:
                from kokoro import KPipeline
            except ImportError as exc:
                raise RuntimeError("kokoro is not installed; install the tts optional dependency") from exc
            self._pipeline = KPipeline(lang_code=self.lang_code)
        return self._pipeline

    def synthesize(self, text: str) -> bytes:
        if not text.strip():
            raise ValueError("text must not be empty")
        import numpy as np

        chunks = []
        for _, _, audio in self._load()(text, voice=self.voice):
            if audio is not None:
                chunks.append(np.asarray(audio, dtype=np.float32))
        if not chunks:
            raise RuntimeError("Kokoro produced no audio")
        audio = np.concatenate(chunks)
        pcm = np.clip(audio, -1.0, 1.0)
        pcm = (pcm * 32767.0).astype("<i2").tobytes()

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(pcm)
        return buffer.getvalue()

    def play(self, audio: bytes, stop: Event) -> None:
        try:
            import sounddevice as sd
            import soundfile as sf
        except ImportError as exc:
            raise RuntimeError("sounddevice and soundfile are required for local playback") from exc
        data, rate = sf.read(io.BytesIO(audio), dtype="float32")
        sd.play(data, rate)
        while sd.get_stream().active and not stop.is_set():
            stop.wait(0.02)
        if stop.is_set():
            sd.stop()
