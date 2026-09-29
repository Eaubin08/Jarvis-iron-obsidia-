"""Screenpipe localhost adapter for Jarvis PerceptualTimeline.

Screenpipe is treated as an external historical observation service. Returned
records are normalized into immutable Jarvis observations and are never live
UI/action handles.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import urlopen

from ..contracts import PerceptualObservation


class ScreenpipeTimeline:
    def __init__(self, base_url: str = "http://127.0.0.1:3030"):
        self.base_url = base_url.rstrip("/")

    def query(
        self,
        query: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> list[PerceptualObservation]:
        if limit <= 0:
            raise ValueError("limit must be positive")

        params = {"q": query, "limit": str(limit)}
        if start is not None:
            params["start_time"] = self._iso(start)
        if end is not None:
            params["end_time"] = self._iso(end)

        url = f"{self.base_url}/search?{urlencode(params)}"
        with urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if isinstance(payload, dict):
            rows = payload.get("data", [])
        elif isinstance(payload, list):
            rows = payload
        else:
            raise ValueError("screenpipe search response must be an object or list")

        if not isinstance(rows, list):
            raise ValueError("screenpipe search response must contain a list")

        return [self._normalize(row) for row in rows[:limit]]

    @staticmethod
    def _iso(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    @staticmethod
    def _normalize(row: dict) -> PerceptualObservation:
        content = row.get("content") if isinstance(row, dict) else None
        if isinstance(content, dict):
            data = content
        elif isinstance(row, dict):
            data = row
        else:
            raise ValueError("screenpipe observation must be an object")

        timestamp_raw = (
            data.get("timestamp")
            or data.get("created_at")
            or row.get("timestamp")
            or row.get("created_at")
        )
        if not timestamp_raw:
            raise ValueError("screenpipe observation missing timestamp")

        timestamp = datetime.fromisoformat(str(timestamp_raw).replace("Z", "+00:00"))
        text = str(
            data.get("text")
            or data.get("ocr_text")
            or data.get("transcription")
            or ""
        )
        kind = str(data.get("type") or row.get("type") or "observation")
        observation_id = str(
            data.get("id")
            or row.get("id")
            or f"screenpipe:{timestamp.isoformat()}:{hash(text)}"
        )

        metadata = {
            "app_name": data.get("app_name"),
            "window_name": data.get("window_name"),
            "file_path": data.get("file_path"),
            "device_name": data.get("device_name"),
        }
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return PerceptualObservation(
            observation_id=observation_id,
            source="screenpipe",
            kind=kind,
            timestamp=timestamp,
            text=text,
            metadata=metadata,
            live_handle=False,
        )
