"""Live voice bridge between the Jarjar HUD and canonical voice providers."""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
import re
import time
import unicodedata
from typing import Callable

from .core import JarvisCore
from .voice_ingress_runtime import VoiceIngressRuntime
from .voice_runtime import ConversationVoiceRuntime


@dataclass
class HUDLiveVoiceBridge:
    ingress: VoiceIngressRuntime
    core: JarvisCore
    conversation: ConversationVoiceRuntime
    capture_seconds: float = 5.0
    on_thinking: Callable[[], None] | None = None
    on_speaking: Callable[[], None] | None = None
    post_speech_cooldown_seconds: float = 0.45
    _last_spoken_text: str = field(default="", init=False, repr=False)

    @staticmethod
    def _normalize_echo_text(text: str) -> str:
        value = unicodedata.normalize("NFKD", text.casefold())
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = re.sub(r"[^a-z0-9]+", " ", value)
        return " ".join(value.split())

    @classmethod
    def _looks_like_self_echo(cls, transcript: str, spoken: str) -> bool:
        heard = cls._normalize_echo_text(transcript)
        own = cls._normalize_echo_text(spoken)
        if len(heard) < 5 or len(own) < 5:
            return False
        if len(heard) >= 8 and heard in own:
            return True

        heard_tokens = heard.split()
        own_tokens = set(own.split())
        if heard_tokens:
            overlap = sum(token in own_tokens for token in heard_tokens) / len(heard_tokens)
            if len(heard_tokens) >= 3 and overlap >= 0.80:
                return True

        return SequenceMatcher(None, heard, own).ratio() >= 0.72

    @staticmethod
    def _spoken_reply(reply: str) -> str:
        text = reply.strip()
        if not text:
            return text

        stop_markers = (
            "\nX108 reste seul décideur",
            "\n**Sources de référence",
            "\nSources de référence",
            "\n_Brody",
            "\nBrody — réponse structurée",
        )
        positions = [
            text.find(marker)
            for marker in stop_markers
            if text.find(marker) >= 0
        ]
        if positions:
            text = text[: min(positions)]

        text = re.sub(r"[*_#`]+", "", text)
        text = " ".join(text.split())

        sentences = re.split(r"(?<=[.!?])\s+", text)
        spoken = " ".join(sentences[:3]).strip()
        if len(spoken) > 520:
            cut = spoken.rfind(" ", 0, 520)
            spoken = spoken[: cut if cut > 0 else 520].rstrip(" ,;:") + "."
        return spoken or text[:520]

    def _respond(self, transcript: str) -> tuple[str, str]:
        if self.on_thinking is not None:
            self.on_thinking()
        reply = self.core.handle_text(transcript).strip()
        if not reply:
            raise ValueError("empty cognition response")

        spoken_reply = self._spoken_reply(reply)
        self._last_spoken_text = spoken_reply

        if self.on_speaking is not None:
            self.on_speaking()
        handle = self.conversation.speak(spoken_reply, open_follow_up=True)
        wait = getattr(handle, "wait", None)
        if callable(wait):
            wait(60.0)
        self.conversation.speech_finished()
        if self.post_speech_cooldown_seconds > 0:
            time.sleep(self.post_speech_cooldown_seconds)
        return transcript, reply

    def run_wake_turn(self) -> tuple[str, str] | None:
        """Capture one turn that must contain the configured wake phrase."""
        if self.capture_seconds <= 0:
            raise ValueError("capture_seconds must be positive")

        # A fresh always-listening cycle must never inherit an old follow-up.
        self.conversation.follow_up_open = False
        transcript = self.ingress.capture_and_begin_turn(self.capture_seconds)
        if transcript is None:
            return None
        return self._respond(transcript)

    def is_self_echo(self, transcript: str) -> bool:
        """Return True when a captured utterance matches Jarjar's own TTS."""
        return bool(
            self._last_spoken_text
            and self._looks_like_self_echo(transcript, self._last_spoken_text)
        )

    def run_follow_up_turn(self) -> tuple[str, str] | None:
        """Capture one wake-free follow-up after a successful spoken reply.

        Silence/empty transcription closes the follow-up window and is treated
        as a normal return to wake-word monitoring, not as a HUD failure.
        """
        if not self.conversation.follow_up_open:
            return None
        try:
            transcript = self.ingress.capture_follow_up(self.capture_seconds)
        except ValueError as exc:
            if "empty" not in str(exc).casefold():
                raise
            return None

        if self.is_self_echo(transcript):
            print(f"JARJAR_ECHO: REJECTED transcript={transcript!r}")
            self.conversation.follow_up_open = True
            return None

        return self._respond(transcript)

    def run_turn(self) -> tuple[str, str] | None:
        """Backward-compatible manual turn semantics."""
        if self.conversation.follow_up_open:
            return self.run_follow_up_turn()
        return self.run_wake_turn()

    def speak_text_reply(self, reply: str) -> None:
        reply = reply.strip()
        if not reply:
            return
        spoken_reply = self._spoken_reply(reply)
        self._last_spoken_text = spoken_reply
        handle = self.conversation.speak(spoken_reply, open_follow_up=True)
        wait = getattr(handle, "wait", None)
        if callable(wait):
            wait(60.0)
        self.conversation.speech_finished()
        if self.post_speech_cooldown_seconds > 0:
            time.sleep(self.post_speech_cooldown_seconds)
