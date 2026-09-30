import pytest

from jarvis.voice_runtime import ConversationVoiceRuntime, VoiceState
from jarvis.voice_turn_runtime import VoiceTurnRuntime


class FakeIngress:
    def __init__(self, transcript):
        self.transcript = transcript
        self.calls = []

    def capture_and_begin_turn(self, duration_seconds):
        self.calls.append(duration_seconds)
        return self.transcript


class FakeCore:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def handle_text(self, text):
        self.calls.append(text)
        return self.response


class FakeSTT:
    def transcribe(self, audio):
        raise AssertionError("STT must not be called by VoiceTurnRuntime")


class FakeSpeech:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class FakeTTS:
    def __init__(self):
        self.calls = []
        self.handle = FakeSpeech()

    def speak(self, text):
        self.calls.append(text)
        return self.handle


def test_no_wake_short_circuits_before_cognition_and_tts():
    ingress = FakeIngress(None)
    core = FakeCore("unused")
    tts = FakeTTS()
    conversation = ConversationVoiceRuntime(FakeSTT(), tts)

    result = VoiceTurnRuntime(ingress, core, conversation).run_once(0.5)

    assert result is None
    assert core.calls == []
    assert tts.calls == []
    assert conversation.state is VoiceState.IDLE


def test_transcript_flows_to_cognition_then_tts():
    ingress = FakeIngress("hello Jarvis")
    core = FakeCore("  Ready.  ")
    tts = FakeTTS()
    conversation = ConversationVoiceRuntime(FakeSTT(), tts)
    conversation.state = VoiceState.THINKING

    handle = VoiceTurnRuntime(ingress, core, conversation).run_once(0.25)

    assert core.calls == ["hello Jarvis"]
    assert tts.calls == ["Ready."]
    assert handle is tts.handle
    assert conversation.state is VoiceState.SPEAKING
    assert conversation.follow_up_open is True


def test_empty_cognition_response_fails_closed_before_tts():
    ingress = FakeIngress("hello")
    core = FakeCore("   ")
    tts = FakeTTS()
    conversation = ConversationVoiceRuntime(FakeSTT(), tts)

    with pytest.raises(ValueError, match="empty cognition response"):
        VoiceTurnRuntime(ingress, core, conversation).run_once(0.25)

    assert tts.calls == []


def test_speech_finished_returns_to_idle_after_turn():
    ingress = FakeIngress("hello")
    core = FakeCore("ready")
    tts = FakeTTS()
    conversation = ConversationVoiceRuntime(FakeSTT(), tts)

    VoiceTurnRuntime(ingress, core, conversation).run_once(0.25)
    assert conversation.state is VoiceState.SPEAKING

    conversation.speech_finished()
    assert conversation.state is VoiceState.IDLE


class FakeFollowUpIngress:
    def __init__(self, transcript):
        self.transcript = transcript
        self.calls = []

    def capture_follow_up(self, duration_seconds):
        self.calls.append(duration_seconds)
        return self.transcript


def test_follow_up_turn_goes_directly_to_cognition_and_tts():
    ingress = FakeFollowUpIngress("second turn")
    core = FakeCore("continuing")
    tts = FakeTTS()
    conversation = ConversationVoiceRuntime(FakeSTT(), tts)
    conversation.follow_up_open = True

    handle = VoiceTurnRuntime(ingress, core, conversation).run_follow_up_once(0.5)

    assert ingress.calls == [0.5]
    assert core.calls == ["second turn"]
    assert tts.calls == ["continuing"]
    assert handle is tts.handle
    assert conversation.state is VoiceState.SPEAKING
    assert conversation.follow_up_open is True
