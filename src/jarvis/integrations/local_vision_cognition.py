"""Local OpenAI-compatible vision provider for Jarjar.

Designed for Qwen-VL-like local servers. It receives fresh local image evidence
from Jarjar's live timeline and returns text only. It has no action authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
import json
import mimetypes
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from jarvis.contracts import ContextSnapshot


@dataclass
class LocalVisionCognition:
    endpoint: str = "http://127.0.0.1:8081/v1/chat/completions"
    model: str = "Qwen2.5-VL-3B-Instruct"
    timeout_seconds: float = 180.0
    live_timeline: object | None = None
    max_images: int = 3
    max_tokens: int = 96

    def _collect_images(self, user_input: str) -> tuple[list[dict], list[str]]:
        if self.live_timeline is None:
            return [], []
        rows = self.live_timeline.query(user_input, limit=10)
        query = user_input.casefold()
        camera_terms = ("caméra", "camera", "webcam")
        screen_terms = ("écran", "ecran", "screen", "desktop", "moniteur")

        def priority(row):
            source = row.source.casefold()
            if any(term in query for term in camera_terms):
                return 0 if "live-camera" in source else 1
            if any(term in query for term in screen_terms):
                return 0 if "live-screen" in source else 1
            return 0

        rows = sorted(rows, key=priority)
        images: list[dict] = []
        context_lines: list[str] = []
        for row in rows:
            context_lines.append(f"[{row.source}/{row.kind}] {row.text} metadata={row.metadata}")
            path_raw = row.metadata.get("image_path") or row.metadata.get("screenshot_path")
            if not path_raw or len(images) >= self.max_images:
                continue
            path = Path(str(path_raw))
            if not path.is_file():
                continue
            mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            images.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{encoded}"},
            })
        return images, context_lines

    def respond(self, user_input: str, context: ContextSnapshot) -> str:
        text = user_input.strip()
        if not text:
            raise ValueError("empty vision input")
        images, context_lines = self._collect_images(text)
        if not images:
            raise RuntimeError("no fresh visual evidence available")

        content = [{"type": "text", "text": text}]
        content.extend(images)
        if context_lines:
            content.append({
                "type": "text",
                "text": "Contexte capteurs:\n" + "\n".join(context_lines),
            })

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Tu es le provider vision local de Jarjar. Décris seulement ce qui "
                        "est supporté par les images fraîches fournies. N'invente pas. "
                        "Tu n'as aucune autorité d'action."
                    ),
                },
                {"role": "user", "content": content},
            ],
            "temperature": 0.1,
            "max_tokens": self.max_tokens,
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
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                detail = ""
            raise RuntimeError(
                f"local vision HTTP {exc.code}: {detail[:1200]}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"local vision endpoint unavailable: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError("local vision request timed out") from exc
        try:
            packet = json.loads(raw.decode("utf-8"))
            answer = packet["choices"][0]["message"]["content"]
        except Exception as exc:
            raise RuntimeError("invalid local vision response") from exc
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("empty local vision response")
        return answer.strip()


def from_environment(*, live_timeline=None) -> LocalVisionCognition:
    return LocalVisionCognition(
        endpoint=os.getenv(
            "JARJAR_VISION_URL",
            "http://127.0.0.1:8081/v1/chat/completions",
        ),
        model=os.getenv("JARJAR_VISION_MODEL", "Qwen2.5-VL-3B-Instruct"),
        timeout_seconds=float(os.getenv("JARJAR_VISION_TIMEOUT", "180")),
        live_timeline=live_timeline,
        max_images=int(os.getenv("JARJAR_VISION_MAX_IMAGES", "1")),
        max_tokens=int(os.getenv("JARJAR_VISION_MAX_TOKENS", "96")),
    )
