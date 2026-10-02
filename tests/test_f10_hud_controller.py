from jarvis.hud_controller import HUDController
from jarvis.hud_state import HUDModel, HUDState


def test_text_turn_updates_transcript_and_returns_idle():
    model = HUDModel()
    controller = HUDController(model, lambda text: f"echo:{text}")

    reply = controller.submit_text("bonjour")

    assert reply == "echo:bonjour"
    snap = model.snapshot()
    assert snap["state"] == "idle"
    assert snap["messages"] == [
        {"speaker": "YOU", "text": "bonjour"},
        {"speaker": "JARJAR", "text": "echo:bonjour"},
    ]


def test_voice_turn_returns_idle_after_completed_voice_handler():
    model = HUDModel()
    controller = HUDController(
        model,
        lambda text: text,
        voice_turn_handler=lambda: ("salut", "bonjour"),
    )

    result = controller.run_voice_turn()

    assert result == ("salut", "bonjour")
    assert model.state is HUDState.IDLE
    controller.voice_finished()
    assert model.state is HUDState.IDLE


def test_follow_up_handler_has_separate_seam():
    model = HUDModel()
    controller = HUDController(
        model,
        lambda text: text,
        voice_turn_handler=lambda: ("wake", "one"),
        follow_up_turn_handler=lambda: ("suite", "two"),
    )

    result = controller.run_follow_up_turn()

    assert result == ("suite", "two")
    assert model.snapshot()["messages"][-2:] == [
        {"speaker": "YOU", "text": "suite"},
        {"speaker": "JARJAR", "text": "two"},
    ]


def test_voice_can_be_disabled_fail_closed():
    model = HUDModel()
    controller = HUDController(model, lambda text: text, voice_turn_handler=lambda: None)
    assert controller.toggle_voice() is False

    try:
        controller.run_voice_turn()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "disabled" in str(exc)


def test_empty_text_fails_without_fake_message():
    model = HUDModel()
    controller = HUDController(model, lambda text: text)

    try:
        controller.submit_text(" ")
        assert False, "expected ValueError"
    except ValueError:
        pass

    assert model.snapshot()["messages"] == []


def test_hud_model_tracks_conversation_session_separately_from_voice_state():
    model = HUDModel()
    assert model.snapshot()["session_open"] is False

    model.set_session_open(True)
    model.set_state(HUDState.LISTENING)
    snap = model.snapshot()
    assert snap["session_open"] is True
    assert snap["state"] == "listening"

    model.set_voice_enabled(False)
    assert model.snapshot()["session_open"] is False
