from jarvis.streaming_voice_ingress import StreamingVoiceIngress


class Mic:
    def __init__(self, utterances=None):
        self.stream_chunks = [b"a", b"wake"]
        self.utterances = list(utterances or [b"speech"])
        self.capture_kwargs = []

    def iter_chunks(self, *, chunk_samples):
        yield from self.stream_chunks

    def capture_until_silence(self, **kwargs):
        self.capture_kwargs.append(kwargs)
        return self.utterances.pop(0)


class Wake:
    def __init__(self):
        self.calls = []
        self.resets = 0

    def reset(self):
        self.resets += 1

    def detect(self, audio):
        self.calls.append(audio)
        return audio == b"wake"


class STT:
    def __init__(self):
        self.calls = 0

    def transcribe(self, audio):
        self.calls += 1
        return "bonjour"


class Conversation:
    def __init__(self):
        self.follow_up_open = False

    def accept_transcript(self, text):
        self.follow_up_open = False
        return text


def test_streaming_wake_captures_post_wake_utterance_with_whisper():
    mic = Mic()
    wake = Wake()
    stt = STT()
    ingress = StreamingVoiceIngress(mic, wake, stt, Conversation())

    result = ingress.capture_and_begin_turn()

    assert result == "bonjour"
    assert wake.calls == [b"a", b"wake"]
    assert stt.calls == 1
    assert wake.resets == 1
    assert len(mic.capture_kwargs) == 1
    assert mic.capture_kwargs[0]["speech_start_timeout"] == 3.0


def test_follow_up_skips_wake_detector_and_uses_short_start_timeout():
    mic = Mic()
    wake = Wake()
    stt = STT()
    conversation = Conversation()
    conversation.follow_up_open = True
    ingress = StreamingVoiceIngress(mic, wake, stt, conversation)

    result = ingress.capture_follow_up()

    assert result == "bonjour"
    assert wake.calls == []
    assert stt.calls == 1
    assert mic.capture_kwargs[0]["speech_start_timeout"] == 2.0


def test_follow_up_inactivity_keeps_idle_window_open():
    mic = Mic(utterances=[b""])
    wake = Wake()
    stt = STT()
    conversation = Conversation()
    conversation.follow_up_open = True
    ingress = StreamingVoiceIngress(mic, wake, stt, conversation)

    try:
        ingress.capture_follow_up()
        assert False, "expected empty follow-up"
    except ValueError as exc:
        assert "empty follow-up" in str(exc)

    assert conversation.follow_up_open is True
    assert stt.calls == 0
