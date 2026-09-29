"""WebSocket transport for a separately running Personal Jarvis.

Wire contract verified against the upstream functional smoke test:
- connect to /ws
- send a JSON text-message envelope
- wait for ResponseGenerated
- fail on brain ErrorOccurred

This module intentionally knows the donor wire protocol. Jarvis Core does not.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from jarvis.contracts import ContextSnapshot


class DonorUnavailable(RuntimeError):
    pass


class DonorProtocolError(RuntimeError):
    pass


@dataclass
class PersonalJarvisWebSocketTransport:
    """Synchronous adapter around an injectable WebSocket connection factory."""

    connect: Callable[[str, float], Any]
    url: str = "ws://127.0.0.1:47821/ws"
    timeout_s: float = 30.0

    def chat(self, text: str, context: ContextSnapshot) -> str:
        try:
            ws = self.connect(self.url, self.timeout_s)
        except Exception as exc:
            raise DonorUnavailable(f"cannot connect to Personal Jarvis: {exc}") from exc

        try:
            # Upstream emits a welcome frame. It is not semantically required.
            try:
                ws.recv()
            except Exception:
                pass

            ws.send(
                json.dumps(
                    {
                        "type": "message",
                        "kind": "text",
                        "content": text,
                        "metadata": {
                            "thread_id": "jarvis-iron",
                            "jarvis_iron_context": context.summary,
                        },
                    }
                )
            )

            while True:
                raw = ws.recv()
                obj = json.loads(raw)
                if not isinstance(obj, dict):
                    continue

                if obj.get("type") != "event":
                    continue

                event_name = obj.get("event_name")
                payload = obj.get("payload") or {}

                if event_name == "ErrorOccurred":
                    layer = payload.get("layer") or payload.get("source_layer")
                    if layer == "brain":
                        message = payload.get("message") or payload.get("error_type") or "brain error"
                        raise DonorProtocolError(str(message))
                    continue

                if event_name == "ResponseGenerated":
                    reply = str(payload.get("text") or "").strip()
                    if not reply:
                        raise DonorProtocolError("Personal Jarvis returned an empty response")
                    return reply
        except (DonorProtocolError, DonorUnavailable):
            raise
        except Exception as exc:
            raise DonorProtocolError(f"Personal Jarvis websocket failure: {exc}") from exc
        finally:
            try:
                ws.close()
            except Exception:
                pass
