"""Temporary local Qwen text cognition for Jarjar.

OpenAI-compatible HTTP only. Text output only; no action authority.
It may receive normalized live-environment metadata, but it never claims to
inspect raw pixels unless a future vision provider supplies an explicit visual
description.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from jarvis.contracts import ContextSnapshot


@dataclass
class LocalQwenCognition:
    endpoint: str = "http://127.0.0.1:8080/v1/chat/completions"
    model: str = "Qwen2.5-3B-Instruct"
    timeout_seconds: float = 20.0
    live_timeline: object | None = None

    def _live_context(self, user_input: str) -> str:
        if self.live_timeline is None:
            return ""
        rows = self.live_timeline.query(user_input, limit=8)
        parts = []
        for row in rows:
            parts.append(
                f"[{row.source}/{row.kind}] {row.text} metadata={row.metadata}"
            )
        return "\n".join(parts)

    def respond(self, user_input: str, context: ContextSnapshot) -> str:
        return self.respond_with_options(user_input, context, include_live=False)

    def respond_with_options(
        self,
        user_input: str,
        context: ContextSnapshot,
        *,
        include_live: bool,
    ) -> str:
        text = user_input.strip()
        if not text:
            raise ValueError("empty cognition input")

        live = self._live_context(text) if include_live else ""
        system = (
            "Tu es le provider local temporaire de Jarjar. Réponds brièvement en français. "
            "Tu n'as aucune autorité d'action. N'invente pas d'observation. "
            "Le contexte caméra fourni ici contient seulement des métadonnées de capture, "
            "pas une compréhension des pixels. Si l'utilisateur demande ce qui est visible "
            "dans l'image et qu'aucune description visuelle/OCR n'est fournie, dis que tu "
            "ne peux pas encore le déterminer."
        )
        user_parts = [f"QUESTION:\n{text}"]
        if context.summary and context.summary != "no context":
            user_parts.append(f"CONTEXTE SESSION:\n{context.summary}")
        if live:
            user_parts.append(f"CONTEXTE LIVE STRUCTURÉ:\n{live}")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": "\n\n".join(user_parts)},
            ],
            "temperature": 0.2,
            "stream": False,
        }
        request = Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError("local Qwen unavailable") from exc

        try:
            packet = json.loads(raw.decode("utf-8"))
            answer = packet["choices"][0]["message"]["content"]
        except Exception as exc:
            raise RuntimeError("invalid local Qwen response") from exc
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("empty local Qwen response")
        return answer.strip()


def from_environment(*, live_timeline=None) -> LocalQwenCognition:
    return LocalQwenCognition(
        endpoint=os.getenv(
            "JARJAR_QWEN_URL",
            "http://127.0.0.1:8080/v1/chat/completions",
        ),
        model=os.getenv("JARJAR_QWEN_MODEL", "Qwen2.5-3B-Instruct"),
        timeout_seconds=float(os.getenv("JARJAR_QWEN_TIMEOUT", "20")),
        live_timeline=live_timeline,
    )
