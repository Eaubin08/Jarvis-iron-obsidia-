import os

import pytest

from jarvis.integrations.screenpipe_timeline import ScreenpipeTimeline


@pytest.mark.skipif(
    os.environ.get("JARVIS_REAL_SCREENPIPE_TEST") != "1",
    reason="JARVIS_REAL_SCREENPIPE_TEST=1 required for live localhost Screenpipe",
)
def test_real_screenpipe_localhost_query_returns_historical_observations():
    base_url = os.environ.get("JARVIS_SCREENPIPE_URL", "http://127.0.0.1:3030")
    api_key = os.environ.get("JARVIS_SCREENPIPE_API_KEY") or os.environ.get(
        "SCREENPIPE_API_KEY"
    )
    query = os.environ.get("JARVIS_SCREENPIPE_QUERY", "")
    timeline = ScreenpipeTimeline(base_url=base_url, api_key=api_key)

    rows = timeline.query(query, limit=5)

    assert isinstance(rows, list)
    for row in rows:
        assert row.source == "screenpipe"
        assert row.live_handle is False
        assert row.timestamp.tzinfo is not None
