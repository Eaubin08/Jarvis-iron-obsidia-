import os

import pytest

from jarvis.integrations.microphone import SoundDeviceMicrophone


@pytest.mark.skipif(
    os.environ.get("JARVIS_REAL_MIC_TEST") != "1",
    reason="JARVIS_REAL_MIC_TEST=1 required for physical microphone capture",
)
def test_real_microphone_capture_returns_pcm16_bytes():
    audio = SoundDeviceMicrophone(sample_rate=16000).capture(0.25)

    assert audio
    assert len(audio) % 2 == 0
    assert len(audio) >= 16000 * 2 // 8
