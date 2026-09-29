import pytest

from jarvis.wake_input_runtime import WakeInputRuntime


class FakeMicrophone:
    def __init__(self, audio=b"pcm"):
        self.audio = audio
        self.calls = []

    def capture(self, duration_seconds):
        self.calls.append(duration_seconds)
        return self.audio


class FakeWakeWord:
    def __init__(self, detected):
        self.detected = detected
        self.calls = []

    def detect(self, audio):
        self.calls.append(audio)
        return self.detected


class FakeSTT:
    def __init__(self, transcript="hello"):
        self.transcript = transcript
        self.calls = []

    def transcribe(self, audio):
        self.calls.append(audio)
        return self.transcript


def test_no_wake_does_not_call_stt():
    mic = FakeMicrophone(b"pcm16")
    wake = FakeWakeWord(False)
    stt = FakeSTT()

    result = WakeInputRuntime(mic, wake, stt).capture_once(0.5)

    assert result.woke is False
    assert result.transcript is None
    assert mic.calls == [0.5]
    assert wake.calls == [b"pcm16"]
    assert stt.calls == []


def test_wake_passes_same_audio_to_stt():
    mic = FakeMicrophone(b"pcm16")
    wake = FakeWakeWord(True)
    stt = FakeSTT("  Jarvis online  ")

    result = WakeInputRuntime(mic, wake, stt).capture_once(0.25)

    assert result.woke is True
    assert result.transcript == "Jarvis online"
    assert wake.calls == [b"pcm16"]
    assert stt.calls == [b"pcm16"]


def test_empty_microphone_audio_fails_closed():
    runtime = WakeInputRuntime(FakeMicrophone(b""), FakeWakeWord(True), FakeSTT())

    with pytest.raises(ValueError, match="empty audio"):
        runtime.capture_once(0.25)


def test_empty_transcript_after_wake_fails_closed():
    runtime = WakeInputRuntime(FakeMicrophone(), FakeWakeWord(True), FakeSTT("   "))

    with pytest.raises(ValueError, match="empty transcript"):
        runtime.capture_once(0.25)
