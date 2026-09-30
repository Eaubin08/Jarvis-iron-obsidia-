from jarvis.streaming_voice_ingress import StreamingVoiceIngress


class Mic:
    def __init__(self):
        self.stream_chunks = [b"a", b"wake"]
        self.utterances = [b"speech"]

    def iter_chunks(self, *, chunk_samples):
        yield from self.stream_chunks

    def capture_until_silence(self, **kwargs):
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
    follow_up_open = False

    def accept_transcript(self, text):
        return text


def test_streaming_wake_invokes_stt_only_after_detection():
    mic = Mic()
    wake = Wake()
    stt = STT()
    ingress = StreamingVoiceIngress(mic, wake, stt, Conversation())

    result = ingress.capture_and_begin_turn()

    assert result == "bonjour"
    assert wake.calls == [b"a", b"wake"]
    assert stt.calls == 1
    assert wake.resets == 1


def test_follow_up_skips_wake_detector():
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
