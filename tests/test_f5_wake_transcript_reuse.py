from jarvis.wake_input_runtime import WakeInputRuntime


class Mic:
    def capture(self, duration):
        return b"audio"


class CountingSTT:
    def __init__(self):
        self.calls = 0

    def transcribe(self, audio):
        self.calls += 1
        return "fresh transcript"


class TranscriptWake:
    def __init__(self, woke=True):
        self.woke = woke
        self.last_transcript = ""
        self.calls = 0

    def detect(self, audio):
        self.calls += 1
        self.last_transcript = "hey jarvis cached"
        return self.woke


class PlainWake:
    def detect(self, audio):
        return True


def test_transcript_wake_reuses_cached_stt_result():
    stt = CountingSTT()
    wake = TranscriptWake()
    runtime = WakeInputRuntime(Mic(), wake, stt)

    result = runtime.capture_once(1.0)

    assert result.woke is True
    assert result.transcript == "hey jarvis cached"
    assert stt.calls == 0


def test_non_transcript_wake_still_runs_stt_once():
    stt = CountingSTT()
    runtime = WakeInputRuntime(Mic(), PlainWake(), stt)

    result = runtime.capture_once(1.0)

    assert result.transcript == "fresh transcript"
    assert stt.calls == 1
