"""openWakeWord adapter behind the canonical Jarvis WakeWordProvider."""
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
        self.last_score = 0.0
        self.last_model = ""

    @classmethod
    def builtin(
        cls,
        name: str = "hey_jarvis",
        *,
        threshold: float = 0.5,
        inference_framework: str = "onnx",
    ) -> "OpenWakeWordProvider":
        """Resolve/download one official openWakeWord pretrained model."""
        try:
            import openwakeword
            from openwakeword.utils import download_models
        except ImportError as exc:
            raise RuntimeError(
                "openwakeword is not installed; install the wakeword optional dependency"
            ) from exc

        normalized = name.strip().casefold().replace(" ", "_")
        if not normalized:
            raise ValueError("wake-word model name must not be empty")

        download_models([normalized])
        candidates = openwakeword.get_pretrained_model_paths(inference_framework)
        for candidate in candidates:
            path = Path(candidate)
            if normalized in path.stem.casefold():
                return cls(
                    path,
                    threshold=threshold,
                    inference_framework=inference_framework,
                )
        raise RuntimeError(f"openWakeWord pretrained model not found after download: {normalized}")

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

    def warmup(self) -> None:
        self._load()

    def reset(self) -> None:
        model = self._model
        if model is not None:
            reset = getattr(model, "reset", None)
            if callable(reset):
                reset()

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
            self.last_score = 0.0
            self.last_model = ""
            return False
        model_name, score = max(scores.items(), key=lambda item: float(item[1]))
        self.last_model = str(model_name)
        self.last_score = float(score)
        return self.last_score >= self.threshold
