"""Local faster-whisper adapter for Jarvis SpeechToTextProvider."""
from __future__ import annotations

import tempfile
import wave
from pathlib import Path


class FasterWhisperSTT:
    def __init__(self, model_size: str = "small", *, device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError("faster-whisper is not installed; install the voice optional dependency") from exc
            self._patch_pyav_metadata_errors()
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe(self, audio: bytes) -> str:
        if not audio:
            raise ValueError("audio must not be empty")
        path = self._write_pcm16_wav(audio)
        try:
            segments, _ = self._load().transcribe(str(path), vad_filter=True)
            return " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
        finally:
            path.unlink(missing_ok=True)

    @staticmethod
    def _write_pcm16_wav(audio: bytes) -> Path:
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        handle.close()
        path = Path(handle.name)
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(audio)
        return path

    @staticmethod
    def _patch_pyav_metadata_errors() -> None:
        try:
            import av
        except ImportError:
            return
        if getattr(av.open, "_jarvis_metadata_errors_compat", False):
            return
        original_open = av.open

        def open_compat(*args, **kwargs):
            kwargs.pop("metadata_errors", None)
            return original_open(*args, **kwargs)

        open_compat._jarvis_metadata_errors_compat = True
        av.open = open_compat
