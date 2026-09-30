"""Fresh local environment observations for Jarjar context.

These observations are contextual evidence only. They are never valid action
handles and carry no recognition or decision authority.
"""
from __future__ import annotations

from datetime import datetime, timezone

from jarvis.contracts import PerceptualObservation


class LiveEnvironmentTimeline:
    def __init__(self, *, monitor_provider=None, camera_rig=None):
        self.monitor_provider = monitor_provider
        self.camera_rig = camera_rig

    def query(self, query: str, *, start=None, end=None, limit: int = 20):
        if limit <= 0:
            raise ValueError("limit must be positive")

        now = datetime.now(timezone.utc)
        rows: list[PerceptualObservation] = []

        if self.monitor_provider is not None:
            layout = self.monitor_provider.layout()
            monitor_text = "; ".join(
                (
                    f"{m.monitor_id} "
                    f"{m.width}x{m.height} "
                    f"at ({m.left},{m.top})"
                    + (" primary" if m.primary else "")
                )
                for m in layout.monitors
            )
            rows.append(
                PerceptualObservation(
                    observation_id=f"live-desktop:{now.isoformat()}",
                    source="live-desktop",
                    kind="monitor_layout",
                    timestamp=now,
                    text=(
                        f"{len(layout.monitors)} active monitor(s); "
                        f"virtual desktop {layout.width}x{layout.height}; "
                        f"{monitor_text}"
                    ),
                    metadata={
                        "monitor_count": len(layout.monitors),
                        "left": layout.left,
                        "top": layout.top,
                        "right": layout.right,
                        "bottom": layout.bottom,
                        "width": layout.width,
                        "height": layout.height,
                        "fresh": True,
                    },
                    live_handle=False,
                )
            )

        if self.camera_rig is not None:
            observations = self.camera_rig.snapshot_all()
            for camera_id, observation in observations.items():
                metadata = dict(observation.metadata)
                metadata["camera_id"] = camera_id
                metadata["fresh"] = True
                rows.append(
                    PerceptualObservation(
                        observation_id=observation.observation_id,
                        source=f"live-camera:{camera_id}",
                        kind="camera_frame",
                        timestamp=observation.timestamp,
                        text=observation.text or "fresh camera frame captured",
                        metadata=metadata,
                        live_handle=False,
                    )
                )

        return rows[:limit]


class CompositePerceptualTimeline:
    """Merge timelines without turning historical/live context into action handles."""

    def __init__(self, *timelines):
        self.timelines = tuple(t for t in timelines if t is not None)

    def query(self, query: str, *, start=None, end=None, limit: int = 20):
        if limit <= 0:
            raise ValueError("limit must be positive")

        rows = []
        for timeline in self.timelines:
            remaining = limit - len(rows)
            if remaining <= 0:
                break
            found = timeline.query(
                query,
                start=start,
                end=end,
                limit=remaining,
            )
            for row in found:
                # Contextual observation identity must never become an action handle.
                if row.live_handle:
                    row = PerceptualObservation(
                        observation_id=row.observation_id,
                        source=row.source,
                        kind=row.kind,
                        timestamp=row.timestamp,
                        text=row.text,
                        metadata=dict(row.metadata),
                        live_handle=False,
                    )
                rows.append(row)
                if len(rows) >= limit:
                    break
        return rows
