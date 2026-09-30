"""Physical smoke for the local vision endpoint.

Requires scripts/start_qwen_vl.ps1 (or equivalent local server) to already be
running on JARJAR_VISION_URL. Uses one fresh camera image when available.
"""
from __future__ import annotations

import os

from jarvis.camera_rig import CameraRig
from jarvis.contracts import ContextSnapshot
from jarvis.integrations.live_environment_timeline import LiveEnvironmentTimeline
from jarvis.integrations.local_vision_cognition import from_environment
from jarvis.integrations.pyautogui_visual_driver import PyAutoGUIVisualDriver
from jarvis.monitor_layout import WindowsMonitorProvider


def main() -> int:
    camera_indices = tuple(
        int(x.strip())
        for x in os.getenv("JARJAR_CAMERA_INDICES", "0,1").split(",")
        if x.strip()
    )
    rig = CameraRig.from_device_indices(camera_indices)
    rig.enable_all(permission_granted=True)
    timeline = LiveEnvironmentTimeline(
        monitor_provider=WindowsMonitorProvider(),
        camera_rig=rig,
        visual_driver=PyAutoGUIVisualDriver(),
    )
    vision = from_environment(live_timeline=timeline)
    vision.max_images = 1

    print(
        "VISION_SMOKE: "
        f"endpoint={vision.endpoint} model={vision.model} "
        f"camera_indices={camera_indices}"
    )
    try:
        answer = vision.respond(
            "Décris très brièvement uniquement ce que tu peux réellement observer dans cette image.",
            ContextSnapshot("physical vision smoke"),
        )
    except Exception as exc:
        print(f"VISION_PHYSICAL: FAIL {type(exc).__name__}: {exc}")
        return 2

    print("VISION_RESPONSE_BEGIN")
    print(answer)
    print("VISION_RESPONSE_END")
    print("VISION_PHYSICAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
