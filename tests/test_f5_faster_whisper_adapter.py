import sys
import types

from jarvis.integrations.faster_whisper_stt import FasterWhisperSTT


class Segment:
    def __init__(self, text):
        self.text = text


class FakeWhisperModel:
    created = []

    def __init__(self, model_size, *, device, compute_type):
        self.created.append((model_size, device, compute_type))

    def transcribe(self, path, vad_filter):
        assert path.endswith(".wav")
        assert vad_filter is True
        return [Segment(" hello "), Segment(" Jarvis ")], {"language": "en"}


def test_adapter_is_lazy_and_returns_joined_transcript(monkeypatch):
    module = types.ModuleType("faster_whisper")
    module.WhisperModel = FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", module)

    stt = FasterWhisperSTT("tiny", device="cpu", compute_type="int8")
    assert FakeWhisperModel.created == []

    transcript = stt.transcribe(b"\x00\x00" * 160)
    assert transcript == "hello Jarvis"
    assert FakeWhisperModel.created == [("tiny", "cpu", "int8")]


def test_empty_audio_fails_before_model_load():
    stt = FasterWhisperSTT()
    try:
        stt.transcribe(b"")
    except ValueError:
        pass
    else:
        raise AssertionError("empty audio must fail")
