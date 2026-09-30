"""Multi-monitor desktop topology.

Coordinates are expressed in Windows virtual-desktop space. Secondary monitors
may therefore have negative x/y origins. This module has no action authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Monitor:
    monitor_id: str
    left: int
    top: int
    right: int
    bottom: int
    primary: bool = False

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x < self.right and self.top <= y < self.bottom


@dataclass(frozen=True)
class MonitorLayout:
    monitors: tuple[Monitor, ...]

    def __post_init__(self) -> None:
        if not self.monitors:
            raise ValueError("monitor layout cannot be empty")

    @property
    def left(self) -> int:
        return min(m.left for m in self.monitors)

    @property
    def top(self) -> int:
        return min(m.top for m in self.monitors)

    @property
    def right(self) -> int:
        return max(m.right for m in self.monitors)

    @property
    def bottom(self) -> int:
        return max(m.bottom for m in self.monitors)

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def monitor_for_point(self, x: int, y: int) -> Monitor | None:
        for monitor in self.monitors:
            if monitor.contains(x, y):
                return monitor
        return None

    def by_id(self, monitor_id: str) -> Monitor | None:
        for monitor in self.monitors:
            if monitor.monitor_id == monitor_id:
                return monitor
        return None


class MonitorProvider(Protocol):
    def layout(self) -> MonitorLayout: ...


class WindowsMonitorProvider:
    """Enumerate active Windows monitors using user32.EnumDisplayMonitors."""

    def layout(self) -> MonitorLayout:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        monitors: list[Monitor] = []

        MONITORINFOF_PRIMARY = 1

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        callback_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HMONITOR,
            wintypes.HDC,
            ctypes.POINTER(wintypes.RECT),
            wintypes.LPARAM,
        )

        def callback(hmonitor, _hdc, _rect, _data):
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if not user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
                return True
            rect = info.rcMonitor
            monitors.append(
                Monitor(
                    monitor_id=f"win32:{int(hmonitor)}",
                    left=int(rect.left),
                    top=int(rect.top),
                    right=int(rect.right),
                    bottom=int(rect.bottom),
                    primary=bool(info.dwFlags & MONITORINFOF_PRIMARY),
                )
            )
            return True

        cb = callback_type(callback)
        if not user32.EnumDisplayMonitors(0, 0, cb, 0):
            raise RuntimeError("EnumDisplayMonitors failed")
        if not monitors:
            raise RuntimeError("no active monitors found")
        monitors.sort(key=lambda m: (not m.primary, m.left, m.top, m.monitor_id))
        return MonitorLayout(tuple(monitors))
