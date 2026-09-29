import pytest

from jarvis.integrations.transcript_wakeword_provider import TranscriptWakeWordProvider


class FakeSTT:
    def __init__(self, transcript):
        self.transcript = transcript
        self.calls = []

    def transcribe(self, audio):
        self.calls.append(audio)
        return self.transcript


def test_detects_configured_phrase_case_and_punctuation_insensitive():
    stt = FakeSTT("Okay... HEY, Jarvis! status please")
    provider = TranscriptWakeWordProvider(stt, "hey jarvis")

    assert provider.detect(b"pcm") is True
    assert stt.calls == [b"pcm"]


@pytest.mark.parametrize(
    "transcript",
    [
        "J'arvisse, hey, J'arvisse.",
        "J'ai revis statue, et j'ai revis statue.",
        "J'ai revis status.",
    ],
)
def test_default_hey_jarvis_accepts_observed_local_whisper_variants(transcript):
    provider = TranscriptWakeWordProvider(FakeSTT(transcript), "hey jarvis")
    assert provider.detect(b"pcm") is True


def test_does_not_match_partial_or_unrelated_phrase():
    assert TranscriptWakeWordProvider(FakeSTT("jarvis status"), "hey jarvis").detect(b"pcm") is False
    assert TranscriptWakeWordProvider(FakeSTT("hey there"), "hey jarvis").detect(b"pcm") is False
    assert TranscriptWakeWordProvider(FakeSTT("j ai revis"), "bonjour atlas").detect(b"pcm") is False


def test_phrase_is_configurable():
    provider = TranscriptWakeWordProvider(FakeSTT("bonjour atlas lance le statut"), "bonjour atlas")
    assert provider.detect(b"pcm") is True


def test_empty_audio_is_rejected_before_stt():
    stt = FakeSTT("hey jarvis")
    provider = TranscriptWakeWordProvider(stt)

    with pytest.raises(ValueError):
        provider.detect(b"")
    assert stt.calls == []


def test_empty_phrase_is_rejected():
    with pytest.raises(ValueError):
        TranscriptWakeWordProvider(FakeSTT("anything"), "   ")
