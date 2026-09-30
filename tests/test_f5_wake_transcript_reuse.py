from jarvis.wake_input_runtime import WakeInputRuntime


class SequenceMic:
    def __init__(self, chunks):
        self.chunks = list(chunks)

    def capture(self, duration):
        return self.chunks.pop(0)


class CountingSTT:
    def __init__(self):
        self.calls = 0

    def transcribe(self, audio):
        self.calls += 1
        return "fresh transcript"


class RecordingWake:
    def __init__(self, wake_on=b"AB"):
        self.inputs = []
        self.last_transcript = ""
        self.wake_on = wake_on

    def detect(self, audio):
        self.inputs.append(audio)
        if self.wake_on in audio:
            self.last_transcript = "hey jarvis bonjour"
            return True
        self.last_transcript = ""
        return False


def test_transcript_wake_reuses_cached_stt_result():
    mic = SequenceMic([b"AB"])
    stt = CountingSTT()
    wake = RecordingWake()
    runtime = WakeInputRuntime(mic, wake, stt)

    result = runtime.capture_once(1.0)

    assert result.woke is True
    assert result.transcript == "hey jarvis bonjour"
    assert stt.calls == 0


def test_rolling_buffer_detects_wake_split_across_two_windows():
    mic = SequenceMic([b"A", b"B"])
    stt = CountingSTT()
    wake = RecordingWake(wake_on=b"AB")
    runtime = WakeInputRuntime(mic, wake, stt)

    first = runtime.capture_once(1.0)
    second = runtime.capture_once(1.0)

    assert first.woke is False
    assert second.woke is True
    assert wake.inputs == [b"A", b"AB"]


def test_successful_wake_clears_rolling_audio():
    mic = SequenceMic([b"A", b"B", b"C"])
    stt = CountingSTT()
    wake = RecordingWake(wake_on=b"AB")
    runtime = WakeInputRuntime(mic, wake, stt)

    assert runtime.capture_once(1.0).woke is False
    assert runtime.capture_once(1.0).woke is True
    assert runtime.capture_once(1.0).woke is False
    assert wake.inputs[-1] == b"C"
