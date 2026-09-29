from jarvis.perception import CameraRuntime, GestureInterpreter


class Camera:
    name = "fake-camera"

    def __init__(self):
        self.calls = []

    def snapshot(self):
        self.calls.append("snapshot")
        return {
            "observation_id": "cam-1",
            "text": "hand raised",
            "metadata": {"gesture": "pause", "confidence": 0.91},
        }


def test_camera_disabled_is_explicit_and_does_not_call_provider():
    camera = Camera()
    runtime = CameraRuntime(camera)

    observation = runtime.snapshot()

    assert observation.enabled is False
    assert observation.metadata["permission"] == "denied"
    assert camera.calls == []


def test_permission_failure_fails_closed():
    camera = Camera()
    runtime = CameraRuntime(camera)
    runtime.enable(permission_granted=False)

    observation = runtime.snapshot()

    assert observation.enabled is False
    assert observation.metadata["permission"] == "denied"
    assert camera.calls == []


def test_camera_observation_is_normalized_when_enabled():
    camera = Camera()
    runtime = CameraRuntime(camera)
    runtime.enable(permission_granted=True)

    observation = runtime.snapshot()

    assert observation.observation_id == "cam-1"
    assert observation.provider == "fake-camera"
    assert observation.enabled is True
    assert observation.text == "hand raised"
    assert camera.calls == ["snapshot"]


def test_gesture_interpretation_is_separate_from_action_execution():
    camera = Camera()
    runtime = CameraRuntime(camera, enabled=True, permission_granted=True)
    observation = runtime.snapshot()
    interpreter = GestureInterpreter()

    gesture = interpreter.interpret(observation)
    request = interpreter.to_action_request(gesture, session_id="s1")

    assert gesture.name == "pause"
    assert request.capability == "gesture.pause"
    assert request.source == "gesture_interpreter"
    assert request.session_id == "s1"
    assert request.arguments["source_observation_id"] == "cam-1"


def test_low_confidence_gesture_is_ignored():
    camera = Camera()
    runtime = CameraRuntime(camera, enabled=True, permission_granted=True)
    observation = runtime.snapshot()
    observation.metadata["confidence"] = 0.2

    assert GestureInterpreter().interpret(observation) is None
