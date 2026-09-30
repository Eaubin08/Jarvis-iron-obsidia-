"""Local faster-whisper adapter for Jarvis SpeechToTextProvider."""
from __future__ import annotations

import re
import tempfile
import unicodedata
import wave
from pathlib import Path


_KNOWN_HALLUCINATIONS = (
    "sous titres realises par la communaute d amara org",
    "les sous titres de cette session ont ete realises par la communaute d amara org",
    "merci d avoir regarde cette video",
    "merci d avoir visionne cette video",
    "n oubliez pas de vous abonner",
)

def _normalize_gate_text(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())

def _known_hallucination(text: str) -> bool:
    value = _normalize_gate_text(text)
    return any(phrase in value for phrase in _KNOWN_HALLUCINATIONS)

class FasterWhisperSTT:
    def __init__(
        self,
        model_size: str = "small",
        *,
        device: str = "cpu",
        compute_type: str = "int8",
        language: str | None = None,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
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

    def warmup(self) -> None:
        """Load model weights without requiring a microphone turn."""
        self._load()

    def transcribe(self, audio: bytes) -> str:
        if not audio:
            raise ValueError("audio must not be empty")
        path = self._write_pcm16_wav(audio)
        try:
            kwargs = {
                "vad_filter": True,
                "initial_prompt": (
                    "Assistant Jarvis en français. "
                    "Commandes possibles : monte le volume, baisse le volume, coupe le son, "
                    "mets en sourdine, play, pause, piste suivante, piste précédente, "
                    "ouvre une application, ferme une application. "
                    "Noms importants : Jarjar, Jarvis, Obsidia, Brody, X-108, Qwen."
                ),
                "beam_size": 5,
                "best_of": 5,
                "temperature": 0.0,
                "condition_on_previous_text": False,
            }
            if self.language:
                kwargs["language"] = self.language
            segments, _ = self._load().transcribe(str(path), **kwargs)
            accepted: list[str] = []
            for segment in segments:
                text = segment.text.strip()
                if not text:
                    continue

                no_speech_prob = float(getattr(segment, "no_speech_prob", 0.0) or 0.0)
                avg_logprob = float(getattr(segment, "avg_logprob", 0.0) or 0.0)

                # Reject only extreme no-speech hypotheses. Normal speech can
                # legitimately have weak confidence on a noisy desktop mic.
                if no_speech_prob >= 0.92 and avg_logprob <= -1.20:
                    print(
                        "JARJAR_STT: REJECTED low-confidence "
                        f"no_speech={no_speech_prob:.2f} avg_logprob={avg_logprob:.2f} "
                        f"text={text!r}"
                    )
                    continue

                if _known_hallucination(text):
                    print(f"JARJAR_STT: REJECTED known-hallucination text={text!r}")
                    continue

                accepted.append(text)

            transcript = " ".join(accepted).strip()
            print(f"JARJAR_STT: transcript={transcript!r}")
            if transcript and _known_hallucination(transcript):
                print(f"JARJAR_STT: REJECTED known-hallucination transcript={transcript!r}")
                return ""
            return transcript
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
