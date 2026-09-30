"""Local microphone capture adapter.

Supports both bounded capture and streaming PCM16 chunks. Speech-boundary
capture is local and deterministic: it stops after sustained silence instead
of forcing every utterance into a fixed-duration window.
"""
from __future__ import annotations

import audioop
import time


class SoundDeviceMicrophone:
    def __init__(
        self,
        *,
        sample_rate: int = 16000,
        channels: int = 1,
        device: int | str | None = None,
    ):
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if channels != 1:
            raise ValueError("canonical microphone capture must be mono")
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device

    @staticmethod
    def _sounddevice():
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError(
                "sounddevice is not installed; install the microphone optional dependency"
            ) from exc
        return sd

    def capture(self, duration_seconds: float) -> bytes:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        sd = self._sounddevice()
        frames = max(1, round(self.sample_rate * duration_seconds))
        recording = sd.rec(
            frames,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            device=self.device,
        )
        sd.wait()
        return recording.astype("<i2", copy=False).tobytes()

    def iter_chunks(self, *, chunk_samples: int = 1280):
        """Yield continuous PCM16 microphone frames.

        1280 samples at 16 kHz is 80 ms, a suitable cadence for openWakeWord.
        """
        if chunk_samples <= 0:
            raise ValueError("chunk_samples must be positive")
        sd = self._sounddevice()
        with sd.RawInputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=chunk_samples,
            device=self.device,
        ) as stream:
            while True:
                data, _overflowed = stream.read(chunk_samples)
                yield bytes(data)

    def capture_until_silence(
        self,
        *,
        max_seconds: float = 8.0,
        silence_seconds: float = 0.65,
        min_seconds: float = 0.35,
        rms_threshold: int = 300,
        chunk_samples: int = 800,
        speech_start_timeout: float | None = None,
    ) -> bytes:
        """Capture one utterance and stop after sustained post-speech silence.

        When speech_start_timeout is set, return empty if no speech starts in
        that window. This is used for conversational follow-up so ambient audio
        cannot keep Jarjar engaged indefinitely.
        """
        if max_seconds <= 0 or silence_seconds <= 0 or min_seconds < 0:
            raise ValueError("invalid speech-boundary timing")
        if speech_start_timeout is not None and speech_start_timeout <= 0:
            raise ValueError("speech_start_timeout must be positive")
        if rms_threshold < 0 or chunk_samples <= 0:
            raise ValueError("invalid speech-boundary threshold")

        sd = self._sounddevice()
        chunks: list[bytes] = []
        started = False
        silence = 0.0
        elapsed = 0.0
        chunk_seconds = chunk_samples / self.sample_rate

        with sd.RawInputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=chunk_samples,
            device=self.device,
        ) as stream:
            while elapsed < max_seconds:
                data, _overflowed = stream.read(chunk_samples)
                raw = bytes(data)
                chunks.append(raw)
                elapsed += chunk_seconds
                rms = audioop.rms(raw, 2)

                if rms >= rms_threshold:
                    started = True
                    silence = 0.0
                elif started:
                    silence += chunk_seconds

                if (
                    not started
                    and speech_start_timeout is not None
                    and elapsed >= speech_start_timeout
                ):
                    return b""

                if started and elapsed >= min_seconds and silence >= silence_seconds:
                    break

        if not started:
            return b""
        return b"".join(chunks)
