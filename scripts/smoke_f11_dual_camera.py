"""Physical F11 dual-camera smoke.

Scans a bounded range of camera indices and validates two independent fresh
captures. Capture-only; no recognition and no actions.
"""
from __future__ import annotations

import os
from pathlib import Path

from jarvis.camera_rig import CameraRig
from jarvis.integrations.opencv_camera import OpenCVCameraProvider


def _discover(max_index: int) -> list[int]:
    found = []
    for index in range(max_index + 1):
        provider = OpenCVCameraProvider(device_index=index)
        try:
            probe = provider.probe()
        except Exception as exc:
            print(f"F11_CAMERA_SCAN: index={index} error={type(exc).__name__}: {exc}")
            continue
        print(f"F11_CAMERA_SCAN: index={index} available={probe['available']}")
        if probe["available"]:
            found.append(index)
    return found


def main() -> int:
    explicit = os.getenv("JARJAR_CAMERA_INDICES", "").strip()
    if explicit:
        indices = [int(x.strip()) for x in explicit.split(",") if x.strip()]
    else:
        max_index = int(os.getenv("JARJAR_CAMERA_SCAN_MAX", "4"))
        indices = _discover(max_index)

    print(f"F11_CAMERAS_FOUND: count={len(indices)} indices={indices}")
    if len(indices) < 2:
        print("F11_DUAL_PHYSICAL: HOLD fewer-than-two-active-cameras")
        return 3

    selected = indices[:2]
    rig = CameraRig.from_device_indices(selected)
    rig.enable_all(permission_granted=True)

    try:
        observations = rig.snapshot_all()
    except Exception as exc:
        print(f"F11_DUAL_PHYSICAL: FAIL {type(exc).__name__}: {exc}")
        return 2

    for camera_id, obs in observations.items():
        path = Path(obs.metadata.get("image_path", ""))
        print(
            "F11_CAMERA_FRAME: "
            f"camera_id={camera_id} "
            f"device_index={obs.metadata.get('device_index')} "
            f"enabled={obs.enabled} "
            f"width={obs.metadata.get('width')} "
            f"height={obs.metadata.get('height')} "
            f"path={path} exists={path.is_file()}"
        )
        if not obs.enabled or not path.is_file():
            print("F11_DUAL_PHYSICAL: FAIL missing-camera-evidence")
            return 2

    print(f"F11_DUAL_SELECTED: indices={selected}")
    print("F11_DUAL_PHYSICAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
