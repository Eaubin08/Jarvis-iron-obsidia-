"""Kokoro synthesis engine behind Jarvis SpeechEngine."""
from __future__ import annotations

import io
import wave
from threading import Event


class KokoroEngine:
    def __init__(
        self,
        *,
        lang_code: str = "f",
        voice: str = "ff_siwis",
        sample_rate: int = 24000,
        speed: float = 1.18,
    ):
        if speed <= 0:
            raise ValueError("speed must be positive")
        self.lang_code = lang_code
        self.voice = voice
        self.sample_rate = sample_rate
        self.speed = speed
        self._pipeline = None

    def _load(self):
        if self._pipeline is None:
            try:
                from kokoro import KPipeline
            except ImportError as exc:
                raise RuntimeError("kokoro is not installed; install the tts optional dependency") from exc
            self._pipeline = KPipeline(lang_code=self.lang_code)
        return self._pipeline

    def warmup(self) -> None:
        """Load the Kokoro pipeline before the first spoken reply."""
        self._load()

    def stream_speak(self, text: str, stop: Event) -> None:
        """Generate and play Kokoro chunks incrementally.

        This avoids waiting for the complete response waveform before playback
        starts, materially reducing perceived response latency on CPU.
        """
        if not text.strip():
            raise ValueError("text must not be empty")
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("numpy and sounddevice are required for streaming Kokoro playback") from exc

        with sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
        ) as stream:
            produced = False
            for _, _, audio in self._load()(text, voice=self.voice, speed=self.speed):
                if stop.is_set():
                    break
                if audio is None:
                    continue
                chunk = np.asarray(audio, dtype=np.float32).reshape(-1, 1)
                if chunk.size == 0:
                    continue
                produced = True
                stream.write(chunk)
            if not produced and not stop.is_set():
                raise RuntimeError("Kokoro produced no audio")

    def synthesize(self, text: str) -> bytes:
        if not text.strip():
            raise ValueError("text must not be empty")
        import numpy as np

        chunks = []
        for _, _, audio in self._load()(text, voice=self.voice, speed=self.speed):
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
