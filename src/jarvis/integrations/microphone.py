"""Local microphone capture adapter.

Capture is explicit and bounded. The adapter returns mono 16 kHz PCM16 bytes
and performs no wake-word, STT or conversation logic.
"""
from __future__ import annotations


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

    def capture(self, duration_seconds: float) -> bytes:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")

        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError(
                "sounddevice is not installed; install the microphone optional dependency"
            ) from exc

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
