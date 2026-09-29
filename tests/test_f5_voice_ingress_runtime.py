import pytest

from jarvis.voice_ingress_runtime import VoiceIngressRuntime
from jarvis.voice_runtime import ConversationVoiceRuntime, VoiceState
from jarvis.wake_input_runtime import WakeInputResult


class FakeWakeInput:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def capture_once(self, duration_seconds):
        self.calls.append(duration_seconds)
        return self.result


class FakeSTT:
    def transcribe(self, audio):
        raise AssertionError("ConversationVoiceRuntime STT must not be called by ingress")


class FakeTTS:
    def speak(self, text):
        raise AssertionError("TTS is outside the ingress checkpoint")


def test_no_wake_leaves_conversation_idle():
    conversation = ConversationVoiceRuntime(FakeSTT(), FakeTTS())
    wake_input = FakeWakeInput(WakeInputResult(woke=False))

    transcript = VoiceIngressRuntime(wake_input, conversation).capture_and_begin_turn(0.5)

    assert transcript is None
    assert wake_input.calls == [0.5]
    assert conversation.state is VoiceState.IDLE


def test_wake_moves_validated_transcript_into_thinking_state_without_second_stt():
    conversation = ConversationVoiceRuntime(FakeSTT(), FakeTTS())
    wake_input = FakeWakeInput(WakeInputResult(woke=True, transcript="  hello Jarvis  "))

    transcript = VoiceIngressRuntime(wake_input, conversation).capture_and_begin_turn(0.25)

    assert transcript == "hello Jarvis"
    assert conversation.state is VoiceState.THINKING
    assert conversation.follow_up_open is False


def test_positive_wake_without_transcript_fails_closed():
    conversation = ConversationVoiceRuntime(FakeSTT(), FakeTTS())
    wake_input = FakeWakeInput(WakeInputResult(woke=True, transcript=None))

    with pytest.raises(ValueError, match="no transcript"):
        VoiceIngressRuntime(wake_input, conversation).capture_and_begin_turn(0.25)


def test_accept_transcript_rejects_empty_text():
    conversation = ConversationVoiceRuntime(FakeSTT(), FakeTTS())

    with pytest.raises(ValueError, match="empty transcript"):
        conversation.accept_transcript("   ")
