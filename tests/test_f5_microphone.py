import sys
import types

import pytest

from jarvis.integrations.microphone import SoundDeviceMicrophone


class FakeRecording:
    def __init__(self, payload):
        self.payload = payload
        self.astype_calls = []

    def astype(self, dtype, copy):
        self.astype_calls.append((dtype, copy))
        return self

    def tobytes(self):
        return self.payload


class FakeSoundDevice(types.ModuleType):
    def __init__(self):
        super().__init__("sounddevice")
        self.rec_calls = []
        self.wait_calls = 0
        self.recording = FakeRecording(b"\x01\x00" * 160)

    def rec(self, frames, *, samplerate, channels, dtype, device):
        self.rec_calls.append(
            {
                "frames": frames,
                "samplerate": samplerate,
                "channels": channels,
                "dtype": dtype,
                "device": device,
            }
        )
        return self.recording

    def wait(self):
        self.wait_calls += 1


def test_microphone_returns_pcm16_mono_bytes(monkeypatch):
    fake = FakeSoundDevice()
    monkeypatch.setitem(sys.modules, "sounddevice", fake)

    mic = SoundDeviceMicrophone(sample_rate=16000, device=3)
    audio = mic.capture(0.01)

    assert audio == b"\x01\x00" * 160
    assert fake.rec_calls == [
        {
            "frames": 160,
            "samplerate": 16000,
            "channels": 1,
            "dtype": "int16",
            "device": 3,
        }
    ]
    assert fake.wait_calls == 1
    assert fake.recording.astype_calls == [("<i2", False)]


def test_microphone_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        SoundDeviceMicrophone(sample_rate=0)
    with pytest.raises(ValueError):
        SoundDeviceMicrophone(channels=2)


def test_microphone_rejects_non_positive_duration():
    mic = SoundDeviceMicrophone()
    with pytest.raises(ValueError):
        mic.capture(0)
