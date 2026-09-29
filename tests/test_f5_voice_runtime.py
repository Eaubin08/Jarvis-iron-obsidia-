from jarvis.voice_runtime import ConversationVoiceRuntime, VoiceState


class FakeSTT:
    def __init__(self, text="hello"):
        self.text = text
        self.audio = None

    def transcribe(self, audio):
        self.audio = audio
        return self.text


class FakeSpeech:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class FakeTTS:
    def __init__(self):
        self.text = None
        self.handle = FakeSpeech()

    def speak(self, text):
        self.text = text
        return self.handle


def test_transcribe_turn_is_provider_neutral():
    stt = FakeSTT("hello jarvis")
    runtime = ConversationVoiceRuntime(stt, FakeTTS())
    assert runtime.transcribe_turn(b"audio") == "hello jarvis"
    assert stt.audio == b"audio"
    assert runtime.state is VoiceState.IDLE


def test_speech_opens_follow_up_window():
    tts = FakeTTS()
    runtime = ConversationVoiceRuntime(FakeSTT(), tts)
    runtime.speak("ready")
    assert runtime.state is VoiceState.SPEAKING
    assert runtime.follow_up_open
    assert tts.text == "ready"


def test_barge_in_cancels_active_speech_without_destroying_turn_runtime():
    tts = FakeTTS()
    runtime = ConversationVoiceRuntime(FakeSTT(), tts)
    handle = runtime.speak("long response")
    runtime.barge_in()
    assert handle.cancelled
    assert runtime.state is VoiceState.LISTENING
    assert runtime.follow_up_open


def test_empty_transcript_fails_closed():
    runtime = ConversationVoiceRuntime(FakeSTT("   "), FakeTTS())
    try:
        runtime.transcribe_turn(b"audio")
    except ValueError:
        pass
    else:
        raise AssertionError("empty transcript must fail")


def test_accept_transcript_enters_thinking_without_calling_stt():
    stt = FakeSTT("must not be used")
    runtime = ConversationVoiceRuntime(stt, FakeTTS())

    assert runtime.accept_transcript("  ready  ") == "ready"
    assert stt.audio is None
    assert runtime.state is VoiceState.THINKING
    assert runtime.follow_up_open is False
