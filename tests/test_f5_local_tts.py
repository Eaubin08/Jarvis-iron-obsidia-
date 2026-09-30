import time

from jarvis.integrations.local_tts import LocalTTS


class FakeEngine:
    def __init__(self):
        self.synthesized = []
        self.play_started = False
        self.stopped = False

    def synthesize(self, text):
        self.synthesized.append(text)
        return b"audio"

    def play(self, audio, stop):
        assert audio == b"audio"
        self.play_started = True
        deadline = time.time() + 2
        while time.time() < deadline and not stop.is_set():
            time.sleep(0.01)
        self.stopped = stop.is_set()


class StreamingFakeEngine:
    def __init__(self):
        self.streamed = []
        self.synthesize_called = False

    def stream_speak(self, text, stop):
        self.streamed.append(text)

    def synthesize(self, text):
        self.synthesize_called = True
        return b"should-not-be-used"

    def play(self, audio, stop):
        raise AssertionError("fallback play must not run for streaming engine")


def test_local_tts_returns_cancellable_handle():
    engine = FakeEngine()
    handle = LocalTTS(engine).speak("Ready")
    deadline = time.time() + 1
    while time.time() < deadline and not engine.play_started:
        time.sleep(0.01)
    assert engine.play_started
    handle.cancel()
    handle.wait(1)
    assert engine.stopped
    assert engine.synthesized == ["Ready"]


def test_local_tts_prefers_streaming_engine():
    engine = StreamingFakeEngine()
    handle = LocalTTS(engine).speak("Bonjour")
    handle.wait(1)
    assert engine.streamed == ["Bonjour"]
    assert engine.synthesize_called is False


def test_local_tts_rejects_empty_text():
    try:
        LocalTTS(FakeEngine()).speak("   ")
    except ValueError:
        pass
    else:
        raise AssertionError("empty TTS text must fail")
