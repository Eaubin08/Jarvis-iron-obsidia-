"""OpenAI-compatible UI-TARS visual grounding provider.

Works with a local vLLM UI-TARS server or any compatible remote endpoint.
No provider-specific SDK is required.
"""
from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError


GROUNDING_PROMPT = """You are a GUI grounding model. Given the screenshot and user instruction,
return exactly one click action targeting the requested UI element.

Output format:
Action: click(start_box='(x,y)')

User Instruction:
{instruction}
"""


class OpenAICompatibleUITARSGrounder:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str = "empty",
        timeout_seconds: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()
        self.api_key = api_key
        self.timeout_seconds = float(timeout_seconds)
        if not self.base_url:
            raise ValueError("UI-TARS base_url is required")
        if not self.model:
            raise ValueError("UI-TARS model is required")

    def ground(self, *, screenshot_path: str, instruction: str) -> str:
        path = Path(screenshot_path)
        if not path.is_file():
            raise ValueError(f"screenshot not found: {path}")
        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError("grounding instruction is required")

        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        image_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        image_url = f"data:{mime};base64,{image_b64}"

        payload = {
            "model": self.model,
            "temperature": 0.0,
            "max_tokens": 256,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": GROUNDING_PROMPT.format(instruction=instruction.strip()),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                }
            ],
        }

        response = self._post_json("/chat/completions", payload)
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("UI-TARS endpoint returned no assistant content") from exc
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("UI-TARS endpoint returned empty assistant content")
        return content.strip()

    def _post_json(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=self.timeout_seconds) as response:
                data = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"UI-TARS HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"UI-TARS endpoint unavailable: {exc.reason}") from exc

        try:
            decoded = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("UI-TARS endpoint returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise RuntimeError("UI-TARS endpoint returned invalid response object")
        return decoded
