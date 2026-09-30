from datetime import datetime, timezone

from jarvis.camera_rig import CameraRig, CameraSlot
from jarvis.contracts import PerceptualObservation
from jarvis.integrations.live_environment_timeline import (
    CompositePerceptualTimeline,
    LiveEnvironmentTimeline,
)
from jarvis.monitor_layout import Monitor, MonitorLayout
from jarvis.perception import CameraRuntime


class Monitors:
    def layout(self):
        return MonitorLayout((
            Monitor("primary", 0, 0, 1920, 1080, True),
            Monitor("right", 1920, 0, 3200, 720, False),
        ))


class Camera:
    def __init__(self, name, observation_id, width, height):
        self.name = name
        self.observation_id = observation_id
        self.width = width
        self.height = height

    def snapshot(self):
        return {
            "observation_id": self.observation_id,
            "timestamp": datetime(2026, 9, 30, 2, 0, tzinfo=timezone.utc),
            "text": "fresh camera frame captured",
            "metadata": {
                "width": self.width,
                "height": self.height,
                "image_path": f"{self.observation_id}.jpg",
            },
        }


def rig():
    value = CameraRig((
        CameraSlot("camera-0", CameraRuntime(Camera("c0", "obs-0", 640, 480))),
        CameraSlot("camera-1", CameraRuntime(Camera("c1", "obs-1", 1280, 720))),
    ))
    value.enable_all(permission_granted=True)
    return value


def test_live_environment_emits_monitor_and_two_camera_observations():
    timeline = LiveEnvironmentTimeline(
        monitor_provider=Monitors(),
        camera_rig=rig(),
    )

    rows = timeline.query("what is around me", limit=10)

    assert len(rows) == 3
    assert rows[0].source == "live-desktop"
    assert rows[0].metadata["monitor_count"] == 2
    assert rows[1].source == "live-camera:camera-0"
    assert rows[1].metadata["width"] == 640
    assert rows[2].source == "live-camera:camera-1"
    assert rows[2].metadata["width"] == 1280
    assert all(row.live_handle is False for row in rows)


class Historical:
    def query(self, query, *, start=None, end=None, limit=20):
        return [
            PerceptualObservation(
                observation_id="old",
                source="screenpipe",
                kind="ocr",
                timestamp=datetime(2026, 9, 29, tzinfo=timezone.utc),
                text="historical context",
                live_handle=True,
            )
        ][:limit]


def test_composite_keeps_live_and_historical_context_non_actionable():
    composite = CompositePerceptualTimeline(
        LiveEnvironmentTimeline(monitor_provider=Monitors()),
        Historical(),
    )

    rows = composite.query("x", limit=5)

    assert [x.source for x in rows] == ["live-desktop", "screenpipe"]
    assert all(x.live_handle is False for x in rows)


def test_composite_is_bounded():
    composite = CompositePerceptualTimeline(
        LiveEnvironmentTimeline(monitor_provider=Monitors(), camera_rig=rig()),
        Historical(),
    )

    rows = composite.query("x", limit=2)

    assert len(rows) == 2
