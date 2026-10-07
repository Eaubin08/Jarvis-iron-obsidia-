"""Local OpenAI-compatible vision provider for Jarjar.

Designed for Qwen-VL-like local servers. It receives fresh local image evidence
from Jarjar's live timeline and returns text only. It has no action authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import base64
import json
import mimetypes
import os
from pathlib import Path
from uuid import uuid4
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
    screen_max_dimension: int = 1280
    vision_cache_dir: str | Path = "runtime_data/vision_inputs"
    _resolved_model: str | None = field(default=None, init=False, repr=False)

    def _discover_model(self) -> str:
        if self._resolved_model:
            return self._resolved_model
        models_endpoint = self.endpoint.rsplit("/chat/completions", 1)[0] + "/models"
        try:
            request = Request(models_endpoint, method="GET")
            with urlopen(request, timeout=min(self.timeout_seconds, 5.0)) as response:
                packet = json.loads(response.read().decode("utf-8"))
            rows = packet.get("data") if isinstance(packet, dict) else None
            if isinstance(rows, list) and rows:
                model_id = rows[0].get("id") if isinstance(rows[0], dict) else None
                if isinstance(model_id, str) and model_id.strip():
                    self._resolved_model = model_id.strip()
                    print(f"JARJAR_VISION_MODEL: discovered={self._resolved_model}")
                    return self._resolved_model
        except Exception as exc:
            print(f"JARJAR_VISION_MODEL: discovery_failed={type(exc).__name__}: {exc}")
        self._resolved_model = self.model
        return self._resolved_model

    def _prepare_visual_input(self, path: Path, source: str) -> Path:
        if "live-screen" not in source.casefold():
            return path

        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError(
                "Pillow is required for screen vision preprocessing"
            ) from exc

        with Image.open(path) as image:
            width, height = image.size
            longest = max(width, height)
            if longest <= self.screen_max_dimension:
                return path

            scale = self.screen_max_dimension / float(longest)
            resized = image.resize(
                (
                    max(1, round(width * scale)),
                    max(1, round(height * scale)),
                )
            )
            cache_dir = Path(self.vision_cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            output = cache_dir / f"screen-{uuid4().hex}.jpg"
            if resized.mode not in ("RGB", "L"):
                resized = resized.convert("RGB")
            resized.save(output, format="JPEG", quality=82, optimize=True)
            return output

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
            prepared_path = self._prepare_visual_input(path, row.source)
            mime = mimetypes.guess_type(prepared_path.name)[0] or "image/jpeg"
            encoded = base64.b64encode(prepared_path.read_bytes()).decode("ascii")
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
            "model": self._discover_model(),
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
        screen_max_dimension=int(
            os.getenv("JARJAR_VISION_SCREEN_MAX_DIMENSION", "1280")
        ),
    )
