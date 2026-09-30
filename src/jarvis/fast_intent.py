"""Deterministic fast-intent routing for commands that need no cognition."""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Callable
import re
import unicodedata

from .contracts import ActionRequest, RiskClass


@dataclass(frozen=True)
class FastIntentMatch:
    request: ActionRequest
    rule: str


class FastIntentRouter:
    """Bounded deterministic rules. Ambiguity returns None and escalates."""

    def __init__(self) -> None:
        self._rules: list[tuple[str, Callable[[str], ActionRequest | None]]] = [
            ("status", self._status),
            ("volume_up", self._volume_up),
            ("volume_down", self._volume_down),
            ("mute", self._mute),
            ("media_play_pause", self._media_play_pause),
            ("media_next", self._media_next),
            ("media_previous", self._media_previous),
            ("battery", self._battery),
            ("wifi", self._wifi),
            ("bluetooth", self._bluetooth),
            ("window_state", self._window_state),
            ("window_monitor", self._window_monitor),
            ("open_app", self._open_app),
        ]

    def route(self, text: str, *, session_id: str = "default") -> FastIntentMatch | None:
        normalized = self._normalize_voice_text(text)
        if not normalized:
            return None
        for name, rule in self._rules:
            request = rule(normalized)
            if request is not None:
                return FastIntentMatch(
                    ActionRequest(
                        capability=request.capability,
                        arguments=request.arguments,
                        target=request.target,
                        source="fast_intent",
                        session_id=session_id,
                        risk=request.risk,
                        idempotency_key=request.idempotency_key,
                    ),
                    name,
                )
        return None

    @staticmethod
    def _normalize_voice_text(text: str) -> str:
        text = unicodedata.normalize("NFKD", text.lower())
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r"[^a-z0-9' ]+", " ", text)
        text = " ".join(text.split())
        polite_suffixes = (
            " s il te plait",
            " s'il te plait",
            " s il vous plait",
            " s'il vous plait",
        )
        for suffix in polite_suffixes:
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                break
        return text

    @staticmethod
    def _close_command(text: str, candidates: tuple[str, ...], *, threshold: float = 0.80) -> bool:
        if len(text.split()) > 6:
            return False
        return max(SequenceMatcher(None, text, candidate).ratio() for candidate in candidates) >= threshold

    @staticmethod
    def _status(text: str) -> ActionRequest | None:
        if text in {"status", "jarvis status", "statut", "statut jarvis"}:
            return ActionRequest("system.status")
        return None

    @classmethod
    def _volume_up(cls, text: str) -> ActionRequest | None:
        candidates = ("monte le volume", "augmente le volume", "volume plus")
        if text in candidates or cls._close_command(text, candidates):
            return ActionRequest("audio.volume_up")
        if text in {"monte", "plus fort"}:
            return ActionRequest("audio.volume_up")
        return None

    @classmethod
    def _volume_down(cls, text: str) -> ActionRequest | None:
        candidates = ("baisse le volume", "diminue le volume", "volume moins")
        if text in candidates or cls._close_command(text, candidates):
            return ActionRequest("audio.volume_down")
        if text in {"baisse", "moins fort"}:
            return ActionRequest("audio.volume_down")
        return None

    @classmethod
    def _mute(cls, text: str) -> ActionRequest | None:
        candidates = ("coupe le son", "mets en sourdine", "mute", "son muet")
        if text in candidates or cls._close_command(text, candidates):
            return ActionRequest("audio.mute_toggle")
        return None

    @staticmethod
    def _media_play_pause(text: str) -> ActionRequest | None:
        if text in {"pause", "lecture pause", "play pause", "reprends la musique"}:
            return ActionRequest("media.play_pause")
        return None

    @staticmethod
    def _media_next(text: str) -> ActionRequest | None:
        if text in {"musique suivante", "piste suivante", "suivant"}:
            return ActionRequest("media.next")
        return None

    @staticmethod
    def _media_previous(text: str) -> ActionRequest | None:
        if text in {"musique precedente", "piste precedente", "precedent"}:
            return ActionRequest("media.previous")
        return None

    @staticmethod
    def _battery(text: str) -> ActionRequest | None:
        if text in {"batterie", "niveau batterie", "etat batterie"}:
            return ActionRequest("system.battery", risk=RiskClass.READ_ONLY)
        return None

    @staticmethod
    def _open_app(text: str) -> ActionRequest | None:
        prefixes = ("ouvre ", "lance ", "demarre ")
        for prefix in prefixes:
            if text.startswith(prefix):
                app = text[len(prefix):].strip()
                for article in ("l'", "le ", "la ", "les "):
                    if app.startswith(article):
                        app = app[len(article):].strip()
                        break
                if app:
                    return ActionRequest("app.open", {"app": app})
        return None

    @staticmethod
    def _wifi(text: str) -> ActionRequest | None:
        if text in {"wifi", "wi fi", "etat wifi", "statut wifi"}:
            return ActionRequest("wifi.status", risk=RiskClass.READ_ONLY)
        if text in {"active le wifi", "active wifi", "allume le wifi", "allume wifi"}:
            return ActionRequest("wifi.enable", risk=RiskClass.SENSITIVE)
        if text in {"desactive le wifi", "coupe le wifi", "coupe wifi"}:
            return ActionRequest("wifi.disable", risk=RiskClass.SENSITIVE)
        return None

    @staticmethod
    def _bluetooth(text: str) -> ActionRequest | None:
        if text in {"bluetooth", "etat bluetooth", "statut bluetooth"}:
            return ActionRequest("bluetooth.status", risk=RiskClass.READ_ONLY)
        if text in {"active le bluetooth", "active bluetooth", "allume le bluetooth"}:
            return ActionRequest("bluetooth.enable", risk=RiskClass.SENSITIVE)
        if text in {"desactive le bluetooth", "coupe le bluetooth"}:
            return ActionRequest("bluetooth.disable", risk=RiskClass.SENSITIVE)
        return None

    @staticmethod
    def _window_state(text: str) -> ActionRequest | None:
        patterns = (
            (r"^(?:minimise|minimize) (.+)$", "window.minimize"),
            (r"^(?:maximise|maximize) (.+)$", "window.maximize"),
            (r"^(?:restaure|restore) (.+)$", "window.restore"),
        )
        for pattern, capability in patterns:
            match = re.match(pattern, text)
            if match:
                title = match.group(1).strip()
                if title:
                    return ActionRequest(capability, {"title": title})
        return None

    @staticmethod
    def _window_monitor(text: str) -> ActionRequest | None:
        match = re.match(
            r"^(?:mets|deplace) (.+?) (?:sur |vers )?(?:l )?ecran (\d+)$",
            text,
        )
        if not match:
            return None
        title = match.group(1).strip()
        monitor_index = int(match.group(2))
        if not title or monitor_index < 1:
            return None
        return ActionRequest(
            "window.move_monitor",
            {"title": title, "monitor_index": monitor_index},
        )
