"""Physical W08 multi-monitor smoke test.

Read-only: enumerates active Windows displays and captures the complete virtual
desktop. It never moves the pointer and never clicks.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from jarvis.integrations.pyautogui_visual_driver import PyAutoGUIVisualDriver
from jarvis.monitor_layout import WindowsMonitorProvider


def main() -> int:
    provider = WindowsMonitorProvider()
    layout = provider.layout()

    print(f"W08_MONITORS: count={len(layout.monitors)}")
    for index, monitor in enumerate(layout.monitors, start=1):
        print(
            "W08_MONITOR: "
            f"index={index} id={monitor.monitor_id} primary={monitor.primary} "
            f"left={monitor.left} top={monitor.top} "
            f"right={monitor.right} bottom={monitor.bottom} "
            f"width={monitor.width} height={monitor.height}"
        )

    print(
        "W08_VIRTUAL_DESKTOP: "
        f"left={layout.left} top={layout.top} "
        f"right={layout.right} bottom={layout.bottom} "
        f"width={layout.width} height={layout.height}"
    )

    evidence_dir = Path("runtime_data") / "w08_physical"
    driver = PyAutoGUIVisualDriver(
        evidence_dir=evidence_dir,
        monitor_provider=provider,
    )
    state = driver.snapshot()
    screenshot_path = Path(state["screenshot_path"])

    with Image.open(screenshot_path) as image:
        image_size = tuple(image.size)

    expected = (layout.width, layout.height)
    print(f"W08_CAPTURE: path={screenshot_path}")
    print(f"W08_CAPTURE_SIZE: actual={image_size} expected={expected}")

    if image_size != expected:
        print("W08_PHYSICAL: FAIL capture-size-mismatch")
        return 2

    if len(layout.monitors) < 2:
        print("W08_PHYSICAL: HOLD only-one-active-monitor")
        return 3

    print("W08_PHYSICAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
