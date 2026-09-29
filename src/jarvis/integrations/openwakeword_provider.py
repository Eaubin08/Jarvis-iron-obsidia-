"""openWakeWord adapter behind the canonical Jarvis WakeWordProvider.

No wake-word model is bundled or downloaded by this adapter. Callers must pass
an explicit local model path whose provenance and deployment rights have been
reviewed separately.
"""
from __future__ import annotations

from pathlib import Path


class OpenWakeWordProvider:
    """Detect a wake word from 16 kHz mono PCM16 audio."""

    def __init__(
        self,
        model_path: str | Path,
        *,
        threshold: float = 0.5,
        inference_framework: str = "onnx",
    ):
        path = Path(model_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"wake-word model does not exist: {path}")
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        if inference_framework not in {"onnx", "tflite"}:
            raise ValueError("inference_framework must be 'onnx' or 'tflite'")

        self.model_path = path.resolve()
        self.threshold = threshold
        self.inference_framework = inference_framework
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from openwakeword.model import Model
            except ImportError as exc:
                raise RuntimeError(
                    "openwakeword is not installed; install the wakeword optional dependency"
                ) from exc

            self._model = Model(
                wakeword_models=[str(self.model_path)],
                inference_framework=self.inference_framework,
            )
        return self._model

    def detect(self, audio: bytes) -> bool:
        if not audio:
            raise ValueError("audio must not be empty")
        if len(audio) % 2:
            raise ValueError("PCM16 audio byte length must be even")

        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "numpy is not installed; install the wakeword optional dependency"
            ) from exc

        pcm = np.frombuffer(audio, dtype="<i2")
        scores = self._load().predict(pcm)
        if not scores:
            return False
        return max(float(score) for score in scores.values()) >= self.threshold
