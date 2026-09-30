"""Physical F11 webcam smoke.

Captures exactly one fresh frame. No recognition and no action.
"""
from __future__ import annotations

import os
from pathlib import Path

from jarvis.integrations.opencv_camera import OpenCVCameraProvider
from jarvis.perception import CameraRuntime


def main() -> int:
    device_index = int(os.getenv("JARJAR_CAMERA_INDEX", "0"))
    provider = OpenCVCameraProvider(device_index=device_index)

    probe = provider.probe()
    print(
        "F11_CAMERA_PROBE: "
        f"provider={probe['provider']} device_index={probe['device_index']} "
        f"available={probe['available']}"
    )
    if not probe["available"]:
        print("F11_PHYSICAL: HOLD camera-unavailable-or-permission-denied")
        return 3

    runtime = CameraRuntime(provider)
    runtime.enable(permission_granted=True)

    try:
        observation = runtime.snapshot()
    except Exception as exc:
        print(f"F11_PHYSICAL: FAIL {type(exc).__name__}: {exc}")
        return 2

    image_path = Path(observation.metadata.get("image_path", ""))
    exists = image_path.is_file()
    print(
        "F11_CAMERA_FRAME: "
        f"enabled={observation.enabled} "
        f"width={observation.metadata.get('width')} "
        f"height={observation.metadata.get('height')} "
        f"path={image_path} exists={exists}"
    )

    if not observation.enabled or not exists:
        print("F11_PHYSICAL: FAIL no-evidence-frame")
        return 2

    print("F11_PHYSICAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
