"""Governed cognition bridge from Jarjar to the existing Obsidia stack.

Jarjar does not own Brody, Qwen, provider selection, or semantic routing.
It submits text to the canonical readonly Brody API boundary and consumes only
the returned final answer. Any provider escalation remains a stack decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from jarvis.contracts import ContextSnapshot


Transport = Callable[[Request, float], bytes]


def _default_transport(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:
        return response.read()


@dataclass
class ObsidiaStackCognition:
    endpoint: str = "http://127.0.0.1:8000/api/brody/chat"
    api_key: str = ""
    timeout_seconds: float = 20.0
    allow_provider: bool = True
    session_id: str = field(default_factory=lambda: f"jarjar-{uuid4().hex}")
    transport: Transport = _default_transport
    last_trace: dict = field(default_factory=dict, init=False)

    def respond(self, user_input: str, context: ContextSnapshot) -> str:
        text = user_input.strip()
        if not text:
            raise ValueError("empty cognition input")

        payload = {
            "message": text,
            "language": "fr",
            "session_id": self.session_id,
            # Important: this authorizes the STACK to consider its provider
            # path. Jarjar never selects or calls Qwen directly.
            "allow_provider": bool(self.allow_provider),
            "allow_memory_candidate": False,
            "allow_manual_apply": False,
            "compact": False,
            "debug": False,
            "debug_full": False,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        request = Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            raw = self.transport(request, self.timeout_seconds)
        except HTTPError as exc:
            raise RuntimeError(f"Obsidia cognition HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError("Obsidia cognition endpoint unavailable") from exc
        except TimeoutError as exc:
            raise RuntimeError("Obsidia cognition timeout") from exc

        try:
            packet = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError("invalid Obsidia cognition response") from exc

        if not isinstance(packet, dict):
            raise RuntimeError("invalid Obsidia cognition packet")

        self.last_trace = {
            "source": packet.get("source"),
            "voice_runtime": packet.get("voice_runtime"),
            "provider_status": packet.get("provider_status"),
            "provider_called": packet.get("provider_called"),
            "selected_provider": packet.get("selected_provider"),
            "fastpath": packet.get("fastpath"),
            "decision_authority": packet.get("decision_authority"),
            "readonly": packet.get("readonly"),
        }
        trace_bits = [
            f"{key}={value}"
            for key, value in self.last_trace.items()
            if value is not None
        ]
        print(
            "JARJAR_COGNITION: "
            + (" ".join(trace_bits) if trace_bits else "no routing metadata returned")
        )

        true_voice = packet.get("true_voice_snapshot")
        true_voice_answer = (
            true_voice.get("final_answer")
            if isinstance(true_voice, dict)
            else None
        )
        answer = (
            true_voice_answer
            or packet.get("response")
            or packet.get("final_answer")
        )
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("Obsidia cognition returned no conversational answer")

        return answer.strip()


def from_environment() -> ObsidiaStackCognition:
    return ObsidiaStackCognition(
        endpoint=os.getenv(
            "JARJAR_OBSIDIA_CHAT_URL",
            "http://127.0.0.1:8000/api/brody/chat",
        ),
        api_key=os.getenv("OBSIDIA_API_KEY", ""),
        timeout_seconds=float(os.getenv("JARJAR_OBSIDIA_TIMEOUT", "20")),
        allow_provider=os.getenv("JARJAR_OBSIDIA_ALLOW_PROVIDER", "1").strip().lower()
        not in {"0", "false", "no", "off"},
    )
