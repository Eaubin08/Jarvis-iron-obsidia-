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
            ("wifi", self._wifi),
            ("bluetooth", self._bluetooth),
            ("window_state", self._window_state),
            ("window_monitor", self._window_monitor),
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
                for article in ("l'", "l’", "le ", "la ", "les "):
                    if app.startswith(article):
                        app = app[len(article):].strip()
                        break
                if app:
                    return ActionRequest("app.open", {"app": app})
        return None


    @staticmethod
    def _wifi(text: str) -> ActionRequest | None:
        if text in {"wifi", "wi fi", "état wifi", "etat wifi", "statut wifi"}:
            return ActionRequest("wifi.status", risk=RiskClass.READ_ONLY)
        if text in {"active le wifi", "active wifi", "allume le wifi", "allume wifi"}:
            return ActionRequest("wifi.enable", risk=RiskClass.SENSITIVE)
        if text in {"désactive le wifi", "desactive le wifi", "coupe le wifi", "coupe wifi"}:
            return ActionRequest("wifi.disable", risk=RiskClass.SENSITIVE)
        return None

    @staticmethod
    def _bluetooth(text: str) -> ActionRequest | None:
        if text in {"bluetooth", "état bluetooth", "etat bluetooth", "statut bluetooth"}:
            return ActionRequest("bluetooth.status", risk=RiskClass.READ_ONLY)
        if text in {"active le bluetooth", "active bluetooth", "allume le bluetooth"}:
            return ActionRequest("bluetooth.enable", risk=RiskClass.SENSITIVE)
        if text in {"désactive le bluetooth", "desactive le bluetooth", "coupe le bluetooth"}:
            return ActionRequest("bluetooth.disable", risk=RiskClass.SENSITIVE)
        return None

    @staticmethod
    def _window_state(text: str) -> ActionRequest | None:
        import re
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
        import re
        match = re.match(
            r"^(?:mets|déplace|deplace) (.+?) (?:sur |vers )?(?:l )?[ée]cran (\d+)$",
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
