import json
from datetime import datetime, timezone

import pytest

from jarvis.integrations.screenpipe_timeline import ScreenpipeTimeline


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_screenpipe_query_normalizes_historical_observation(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["auth"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        return FakeResponse(
            {
                "data": [
                    {
                        "id": "obs-1",
                        "type": "OCR",
                        "content": {
                            "timestamp": "2026-09-29T18:00:00Z",
                            "text": "Jarvis architecture",
                            "app_name": "Code",
                            "window_name": "README.md",
                        },
                    }
                ]
            }
        )

    monkeypatch.setattr(
        "jarvis.integrations.screenpipe_timeline.urlopen", fake_urlopen
    )

    timeline = ScreenpipeTimeline(api_key="secret-token")
    rows = timeline.query(
        "Jarvis",
        start=datetime(2026, 9, 29, 17, 0, tzinfo=timezone.utc),
        limit=5,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.observation_id == "obs-1"
    assert row.source == "screenpipe"
    assert row.kind == "OCR"
    assert row.text == "Jarvis architecture"
    assert row.metadata["app_name"] == "Code"
    assert row.live_handle is False
    assert "q=Jarvis" in seen["url"]
    assert "limit=5" in seen["url"]
    assert seen["auth"] == "Bearer secret-token"
    assert seen["timeout"] == 5


def test_screenpipe_query_omits_authorization_without_api_key(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["auth"] = request.get_header("Authorization")
        return FakeResponse([])

    monkeypatch.setattr(
        "jarvis.integrations.screenpipe_timeline.urlopen", fake_urlopen
    )

    ScreenpipeTimeline().query("x")
    assert seen["auth"] is None


def test_screenpipe_history_can_never_be_live_handle(monkeypatch):
    def fake_urlopen(request, timeout):
        return FakeResponse(
            [
                {
                    "id": "obs-2",
                    "timestamp": "2026-09-29T18:00:00+00:00",
                    "text": "button coordinates 10,20",
                    "live_handle": True,
                }
            ]
        )

    monkeypatch.setattr(
        "jarvis.integrations.screenpipe_timeline.urlopen", fake_urlopen
    )

    row = ScreenpipeTimeline().query("button")[0]
    assert row.live_handle is False


def test_screenpipe_query_rejects_non_positive_limit():
    with pytest.raises(ValueError):
        ScreenpipeTimeline().query("x", limit=0)
