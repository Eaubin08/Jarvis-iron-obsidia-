import io
import wave

from jarvis.integrations.kokoro_engine import KokoroEngine


def test_real_kokoro_model_generates_wav_audio():
    engine = KokoroEngine(lang_code="a", voice="af_heart")
    audio = engine.synthesize("Jarvis is ready.")

    assert audio[:4] == b"RIFF"
    with wave.open(io.BytesIO(audio), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 24000
        assert wav.getnframes() > 1000
