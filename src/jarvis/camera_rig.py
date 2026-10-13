"""Multi-camera rig for Jarjar F11.

Each physical camera remains an independent provider. The rig coordinates
capture only; it has no recognition, gesture, or action authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from jarvis.integrations.opencv_camera import OpenCVCameraProvider
from jarvis.perception import CameraObservation, CameraRuntime


@dataclass
class CameraSlot:
    camera_id: str
    runtime: CameraRuntime


class CameraRig:
    def __init__(self, slots: Iterable[CameraSlot]):
        self.slots = tuple(slots)
        if not self.slots:
            raise ValueError("camera rig requires at least one slot")
        ids = [slot.camera_id for slot in self.slots]
        if len(ids) != len(set(ids)):
            raise ValueError("camera_id values must be unique")

    @classmethod
    def from_device_indices(cls, indices: Iterable[int]) -> "CameraRig":
        slots = []
        for index in indices:
            provider = OpenCVCameraProvider(device_index=int(index))
            runtime = CameraRuntime(provider)
            slots.append(CameraSlot(camera_id=f"camera-{int(index)}", runtime=runtime))
        return cls(slots)

    def enable_all(self, *, permission_granted: bool) -> None:
        for slot in self.slots:
            slot.runtime.enable(permission_granted=permission_granted)

    def disable_all(self) -> None:
        for slot in self.slots:
            slot.runtime.disable()

    def snapshot_all(self) -> dict[str, CameraObservation]:
        observations: dict[str, CameraObservation] = {}
        for slot in self.slots:
            try:
                observations[slot.camera_id] = slot.runtime.snapshot()
            except Exception as exc:
                print(
                    f"JARJAR_CAMERA: {slot.camera_id} unavailable "
                    f"{type(exc).__name__}: {exc}"
                )
        return observations
