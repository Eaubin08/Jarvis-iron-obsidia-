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
            ("volume_status", self._volume_status),
            ("volume_up", self._volume_up),
            ("volume_down", self._volume_down),
            ("volume_set", self._volume_set),
            ("mute", self._mute),
            ("media_next", self._media_next),
            ("media_previous", self._media_previous),
            ("media_play_pause", self._media_play_pause),
            ("battery", self._battery),
            ("wifi", self._wifi),
            ("bluetooth", self._bluetooth),
            ("window_focus", self._window_focus),
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
        text = re.sub(r"^(?:et )?(?:hey )?jarvis(?: jarvis)?[ ,]*", "", text).strip()
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

    @staticmethod
    def _volume_status(text: str) -> ActionRequest | None:
        value = " ".join(text.split())

        # Readonly volume-status intent. Accept natural conversational wrappers
        # while staying bounded to explicit volume-status wording.
        if "volume" not in value:
            return None

        status_markers = (
            "niveau",
            "etat",
            "statut",
            "combien",
            "a combien",
            "quel est",
            "quelle est",
            "c est quoi",
            "c'est quoi",
        )
        if not any(marker in value for marker in status_markers) and "actuel" not in value:
            return None

        # Explicit mutation verbs always belong to control routing, never status.
        mutation_markers = (
            "monte",
            "augmente",
            "remonte",
            "baisse",
            "diminue",
            "descend",
            "mets",
            "met",
            "regle",
            "fixe",
            "coupe",
            "mute",
            "sourdine",
        )
        if any(re.search(rf"\b{re.escape(marker)}\b", value) for marker in mutation_markers):
            return None

        # Once a phrase clearly contains "volume" plus a status marker
        # (including "actuel"), treat the surrounding STT wrapper as noise.
        # Examples: "quel est le volume actuel", "elle est le volume actuel",
        # "tele le volume actuel", "niveau du volume".
        return ActionRequest("audio.status", risk=RiskClass.READ_ONLY)

    @staticmethod
    def _volume_amount(text: str) -> int | None:
        match = re.search(r"\b(?:de|a)\s+(\d{1,3})\b", text)
        if match:
            value = int(match.group(1))
            return value if 0 <= value <= 100 else None

        words = {
            "zero": 0, "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4,
            "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
            "onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15,
            "seize": 16, "vingt": 20, "trente": 30, "quarante": 40,
            "cinquante": 50, "soixante": 60, "cent": 100,
        }
        match = re.search(r"\b(?:de|a)\s+([a-z]+)\b", text)
        if not match:
            return None
        return words.get(match.group(1))

    @staticmethod
    def _volume_direction(text: str) -> str | None:
        if "volume" not in text:
            if text in {"monte", "plus fort"} or re.fullmatch(r"(?:monte|augmente|remonte) de (?:\d{1,3}|[a-z]+)", text):
                return "up"
            if text in {"baisse", "moins fort"} or re.fullmatch(r"(?:baisse|diminue|descend) de (?:\d{1,3}|[a-z]+)", text):
                return "down"
            return None

        prefix = text.split("volume", 1)[0].strip()
        tokens = prefix.split()
        if not tokens:
            return None

        # Multiple explicit opposite instructions in one utterance are ambiguous.
        full = set(text.split())
        if ({"monte", "augmente", "remonte"} & full) and ({"baisse", "diminue", "descend"} & full):
            return None

        up_aliases = ("monte", "augmente", "remonte", "mente", "monde", "manque")
        down_aliases = ("baisse", "diminue", "descend")

        # French commands normally contain an article before "volume":
        # "monte le volume", "baisse le volume". Use the first meaningful token,
        # not the last token ("le").
        meaningful = [token for token in tokens if token not in {"le", "la", "les", "du", "de", "des", "un", "une"}]
        if not meaningful:
            return None
        verb = meaningful[-1]

        if verb in up_aliases:
            return "up"
        if verb in down_aliases:
            return "down"

        up_score = max(SequenceMatcher(None, verb, candidate).ratio() for candidate in up_aliases[:3])
        down_score = max(SequenceMatcher(None, verb, candidate).ratio() for candidate in down_aliases)
        best = max(up_score, down_score)
        if best < 0.68 or abs(up_score - down_score) < 0.12:
            return None
        return "up" if up_score > down_score else "down"

    @classmethod
    def _volume_up(cls, text: str) -> ActionRequest | None:
        if cls._volume_direction(text) != "up":
            return None
        amount = cls._volume_amount(text)
        if amount is not None and re.search(r"\bde\s+(?:\d{1,3}|[a-z]+)\b", text):
            return ActionRequest("audio.adjust_volume", {"delta": amount})
        return ActionRequest("audio.volume_up")

    @classmethod
    def _volume_down(cls, text: str) -> ActionRequest | None:
        if cls._volume_direction(text) != "down":
            return None
        amount = cls._volume_amount(text)
        if amount is not None and re.search(r"\bde\s+(?:\d{1,3}|[a-z]+)\b", text):
            return ActionRequest("audio.adjust_volume", {"delta": -amount})
        return ActionRequest("audio.volume_down")

    @classmethod
    def _volume_set(cls, text: str) -> ActionRequest | None:
        if "volume" not in text:
            return None
        if not re.search(r"\b(?:mets|met|regle|fixe)\b.*\bvolume\b.*\ba\b", text):
            return None
        percent = cls._volume_amount(text)
        if percent is not None and 0 <= percent <= 100:
            return ActionRequest("audio.set_volume", {"percent": percent})
        return None

    @classmethod
    def local_guard_response(cls, text: str) -> str | None:
        normalized = cls._normalize_voice_text(text)

        # Guard only clear audio-control intent. The French word "son" is also
        # a possessive determiner ("son contexte", "son fonctionnement") and
        # must never hijack ordinary cognition/project questions.
        audio_control = (
            "volume" in normalized
            or re.search(r"\b(?:sourdine|mute)\b", normalized)
            or normalized in {
                "coupe le son",
                "coupe son",
                "remets le son",
                "remet le son",
                "active le son",
                "desactive le son",
                "monte le son",
                "baisse le son",
            }
        )
        if cls._volume_status(normalized) is not None:
            return None

        if audio_control:
            return "Je n'ai pas compris la commande audio. Dis par exemple : monte le volume de dix, baisse le volume de quinze, ou mets le volume à trente."
        return None

    @classmethod
    def _mute(cls, text: str) -> ActionRequest | None:
        candidates = ("coupe le son", "mets en sourdine", "mute", "son muet")
        if text in candidates or cls._close_command(text, candidates):
            return ActionRequest("audio.mute_toggle")
        return None

    @staticmethod
    def _media_play_pause(text: str) -> ActionRequest | None:
        exact = {
            "pause",
            "lecture pause",
            "play pause",
            "reprends la musique",
            "reprend la musique",
            "active la musique",
            "lance la musique",
            "mets la musique",
            "met la musique",
            "mets pause sur la musique",
            "met pause sur la musique",
            "mets la musique en pause",
            "met la musique en pause",
        }
        if text in exact:
            return ActionRequest("media.play_pause")

        # Directional media commands belong to next/previous, never play/pause.
        if re.search(r"\b(?:suivante?|precedente?|precedent)\b", text):
            return None

        # Natural voice variants that clearly ask to resume/start the media
        # already loaded on the PC. Keep this bounded to explicit music/media
        # verbs so ordinary cognition mentioning music is not hijacked.
        if re.search(
            r"\b(?:active|lance|reprends|reprend|mets|met)\b.*"
            r"\b(?:musique|lecture|media|multimedia)\b",
            text,
        ):
            return ActionRequest("media.play_pause")
        if (
            ("lecteur de musique" in text or "lecteur multimedia" in text)
            and re.search(r"\b(?:lance|reprends|reprend|active)\b", text)
            and re.search(r"\b(?:musique|lecture|en cours)\b", text)
        ):
            return ActionRequest("media.play_pause")
        return None

    @staticmethod
    def _media_next(text: str) -> ActionRequest | None:
        if text in {"musique suivante", "piste suivante", "suivant", "suivante"}:
            return ActionRequest("media.next")
        if re.fullmatch(
            r"(?:mets|met|passe|va a|lance) (?:la )?(?:musique|piste) suivante",
            text,
        ):
            return ActionRequest("media.next")
        return None

    @staticmethod
    def _media_previous(text: str) -> ActionRequest | None:
        if text in {"musique precedente", "piste precedente", "precedent", "precedente"}:
            return ActionRequest("media.previous")
        if re.fullmatch(
            r"(?:mets|met|passe|reviens a|lance) (?:la )?(?:musique|piste) precedente",
            text,
        ):
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
    def _window_focus(text: str) -> ActionRequest | None:
        patterns = (
            r"^(?:focus|pocus|focalise|bascule sur) (.+)$",
            r"^(?:mets|met) (.+?) (?:au premier plan|devant)$",
        )
        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                title = match.group(1).strip()
                for article in ("l'", "le ", "la ", "les "):
                    if title.startswith(article):
                        title = title[len(article):].strip()
                        break
                if title:
                    compact = title.replace(" ", "").replace("-", "")
                    if compact in {"blocnote", "bloquenote", "blocnotes"}:
                        title = "bloc note"
                    return ActionRequest("window.focus", {"title": title})
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
