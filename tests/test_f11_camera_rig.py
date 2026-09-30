from jarvis.camera_rig import CameraRig, CameraSlot
from jarvis.perception import CameraRuntime


class Camera:
    def __init__(self, name, observation_id):
        self.name = name
        self.observation_id = observation_id
        self.calls = 0

    def snapshot(self):
        self.calls += 1
        return {
            "observation_id": self.observation_id,
            "text": "frame",
            "metadata": {"camera": self.name},
        }


def test_camera_rig_captures_two_independent_cameras():
    a = Camera("a", "obs-a")
    b = Camera("b", "obs-b")
    rig = CameraRig((
        CameraSlot("front", CameraRuntime(a)),
        CameraSlot("side", CameraRuntime(b)),
    ))
    rig.enable_all(permission_granted=True)

    observations = rig.snapshot_all()

    assert set(observations) == {"front", "side"}
    assert observations["front"].observation_id == "obs-a"
    assert observations["side"].observation_id == "obs-b"
    assert a.calls == 1
    assert b.calls == 1


def test_camera_rig_permission_denial_fails_closed_per_camera():
    a = Camera("a", "obs-a")
    b = Camera("b", "obs-b")
    rig = CameraRig((
        CameraSlot("front", CameraRuntime(a)),
        CameraSlot("side", CameraRuntime(b)),
    ))
    rig.enable_all(permission_granted=False)

    observations = rig.snapshot_all()

    assert observations["front"].enabled is False
    assert observations["side"].enabled is False
    assert a.calls == 0
    assert b.calls == 0
