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


class FakeMicrophone:
    def __init__(self, audio=b"follow-up-audio"):
        self.audio = audio
        self.calls = []

    def capture(self, duration_seconds):
        self.calls.append(duration_seconds)
        return self.audio


class FollowUpSTT:
    def __init__(self, text="second turn"):
        self.text = text
        self.calls = []

    def transcribe(self, audio):
        self.calls.append(audio)
        return self.text


def test_follow_up_bypasses_wake_word_and_uses_microphone_stt_directly():
    microphone = FakeMicrophone()
    stt = FollowUpSTT("  second turn  ")
    wake_input = FakeWakeInput(WakeInputResult(woke=False))
    wake_input.microphone = microphone
    wake_input.stt = stt

    conversation = ConversationVoiceRuntime(stt, FakeTTS())
    conversation.follow_up_open = True

    transcript = VoiceIngressRuntime(wake_input, conversation).capture_follow_up(0.75)

    assert transcript == "second turn"
    assert microphone.calls == [0.75]
    assert stt.calls == [b"follow-up-audio"]
    assert wake_input.calls == []
    assert conversation.state is VoiceState.THINKING
    assert conversation.follow_up_open is False


def test_follow_up_fails_closed_when_window_not_open():
    wake_input = FakeWakeInput(WakeInputResult(woke=False))
    wake_input.microphone = FakeMicrophone()
    wake_input.stt = FollowUpSTT()
    conversation = ConversationVoiceRuntime(wake_input.stt, FakeTTS())

    with pytest.raises(RuntimeError, match="follow-up window is not open"):
        VoiceIngressRuntime(wake_input, conversation).capture_follow_up(0.5)

    assert wake_input.microphone.calls == []
