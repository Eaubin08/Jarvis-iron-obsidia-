import math
import struct

from jarvis.integrations.faster_whisper_stt import FasterWhisperSTT


def test_real_faster_whisper_model_loads_and_transcribes_valid_pcm():
    # One second of deterministic low-amplitude tone. The assertion is about the
    # real engine/model execution path, not linguistic accuracy.
    samples = []
    for i in range(16000):
        value = int(300 * math.sin(2 * math.pi * 440 * i / 16000))
        samples.append(struct.pack("<h", value))
    pcm = b"".join(samples)

    stt = FasterWhisperSTT("tiny.en", device="cpu", compute_type="int8")
    transcript = stt.transcribe(pcm)

    assert isinstance(transcript, str)
    assert stt._model is not None
