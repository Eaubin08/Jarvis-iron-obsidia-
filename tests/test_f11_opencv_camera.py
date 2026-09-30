from jarvis.integrations.opencv_camera import OpenCVCameraProvider


class Capture:
    def __init__(self, opened=True, frames=None):
        self.opened = opened
        self.frames = list(frames or [])
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        if self.frames:
            return self.frames.pop(0)
        return False, None

    def release(self):
        self.released = True


class Frame:
    shape = (720, 1280, 3)


class CV2:
    CAP_MSMF = 1400

    def __init__(self, captures):
        self.captures = list(captures)
        self.writes = []

    def VideoCapture(self, *args):
        return self.captures.pop(0)

    def imwrite(self, path, frame):
        self.writes.append((path, frame))
        return True


class Provider(OpenCVCameraProvider):
    def __init__(self, cv2, **kwargs):
        super().__init__(**kwargs)
        self.fake_cv2 = cv2

    def _cv2(self):
        return self.fake_cv2


def test_probe_reports_available_and_releases():
    cap = Capture(opened=True)
    provider = Provider(CV2([cap]))
    result = provider.probe()
    assert result["available"] is True
    assert cap.released is True


def test_snapshot_fails_closed_when_camera_unavailable():
    cap1 = Capture(opened=False)
    cap2 = Capture(opened=False)
    provider = Provider(CV2([cap1, cap2]))
    try:
        provider.snapshot()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "permission denied" in str(exc)


def test_snapshot_returns_fresh_capture_metadata(tmp_path):
    frames = [(True, Frame()), (True, Frame())]
    cap = Capture(opened=True, frames=frames)
    cv2 = CV2([cap])
    provider = Provider(cv2, evidence_dir=tmp_path, warmup_frames=1)

    result = provider.snapshot()

    assert result["metadata"]["width"] == 1280
    assert result["metadata"]["height"] == 720
    assert result["metadata"]["fresh"] is True
    assert result["metadata"]["face_recognition"] is False
    assert result["metadata"]["gesture_classification"] is False
    assert cap.released is True
    assert len(cv2.writes) == 1
