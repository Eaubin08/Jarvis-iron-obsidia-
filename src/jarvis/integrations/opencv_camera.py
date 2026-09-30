"""Physical webcam provider for Jarjar F11.

Capture-only boundary. No face recognition, no gesture classification, no
action authority.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class OpenCVCameraProvider:
    name = "opencv-camera"

    def __init__(
        self,
        *,
        device_index: int = 0,
        evidence_dir: str | Path = "runtime_data/camera_snapshots",
        warmup_frames: int = 3,
    ):
        self.device_index = int(device_index)
        self.evidence_dir = Path(evidence_dir)
        self.warmup_frames = max(0, int(warmup_frames))

    def _cv2(self):
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError(
                "opencv-python is not installed; install the camera optional dependency"
            ) from exc
        return cv2

    def _open_capture(self, cv2):
        backend = getattr(cv2, "CAP_MSMF", None)
        if backend is not None:
            capture = cv2.VideoCapture(self.device_index, backend)
            if capture.isOpened():
                return capture
            capture.release()
        return cv2.VideoCapture(self.device_index)

    def probe(self) -> dict:
        cv2 = self._cv2()
        capture = self._open_capture(cv2)
        try:
            opened = bool(capture.isOpened())
            return {
                "available": opened,
                "device_index": self.device_index,
                "provider": self.name,
            }
        finally:
            capture.release()

    def snapshot(self) -> dict:
        cv2 = self._cv2()
        capture = self._open_capture(cv2)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(
                "camera unavailable or permission denied; check Windows camera privacy settings"
            )

        try:
            frame = None
            ok = False
            for _ in range(self.warmup_frames):
                ok, frame = capture.read()
                if not ok:
                    frame = None

            ok, frame = capture.read()
            if not ok or frame is None:
                raise RuntimeError("camera opened but no frame could be captured")

            height, width = frame.shape[:2]
            observation_id = f"camera_{uuid4().hex}"
            self.evidence_dir.mkdir(parents=True, exist_ok=True)
            path = self.evidence_dir / f"{observation_id}.jpg"
            if not cv2.imwrite(str(path), frame):
                raise RuntimeError("camera frame could not be written")

            return {
                "observation_id": observation_id,
                "timestamp": datetime.now(timezone.utc),
                "text": "fresh camera frame captured",
                "metadata": {
                    "device_index": self.device_index,
                    "width": int(width),
                    "height": int(height),
                    "image_path": str(path),
                    "fresh": True,
                    "face_recognition": False,
                    "gesture_classification": False,
                },
            }
        finally:
            capture.release()
