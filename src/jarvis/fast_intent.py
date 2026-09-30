"""Deterministic fast-intent routing for commands that need no cognition."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .contracts import ActionRequest, RiskClass


@dataclass(frozen=True)
class FastIntentMatch:
    request: ActionRequest
    rule: str


class FastIntentRouter:
    """Exact/bounded rules only. Ambiguity returns None and escalates."""

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
            ("open_app", self._open_app),
        ]

    def route(self, text: str, *, session_id: str = "default") -> FastIntentMatch | None:
        normalized = " ".join(text.strip().lower().split())
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
    def _status(text: str) -> ActionRequest | None:
        if text in {"status", "jarvis status", "statut", "statut jarvis"}:
            return ActionRequest("system.status")
        return None


    @staticmethod
    def _volume_up(text: str) -> ActionRequest | None:
        if text in {"monte le volume", "augmente le volume", "volume plus"}:
            return ActionRequest("audio.volume_up")
        return None

    @staticmethod
    def _volume_down(text: str) -> ActionRequest | None:
        if text in {"baisse le volume", "diminue le volume", "volume moins"}:
            return ActionRequest("audio.volume_down")
        return None

    @staticmethod
    def _mute(text: str) -> ActionRequest | None:
        if text in {"coupe le son", "mute", "son muet"}:
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
        if text in {"musique précédente", "musique precedente", "piste précédente", "piste precedente", "précédent", "precedent"}:
            return ActionRequest("media.previous")
        return None

    @staticmethod
    def _battery(text: str) -> ActionRequest | None:
        if text in {"batterie", "niveau batterie", "état batterie", "etat batterie"}:
            return ActionRequest("system.battery", risk=RiskClass.READ_ONLY)
        return None

    @staticmethod
    def _open_app(text: str) -> ActionRequest | None:
        prefixes = ("ouvre ", "lance ", "démarre ", "demarre ")
        for prefix in prefixes:
            if text.startswith(prefix):
                app = text[len(prefix):].strip()
                if app:
                    return ActionRequest("app.open", {"app": app})
        return None
