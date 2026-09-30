import os
import time

import pytest

from jarvis.integrations.kokoro_engine import KokoroEngine
from jarvis.integrations.local_tts import LocalTTS
from jarvis.voice_runtime import ConversationVoiceRuntime, VoiceState


ENV = "JARVIS_REAL_BARGE_IN_TEST"


class UnusedSTT:
    def transcribe(self, audio):
        raise AssertionError("STT must not be used by the physical barge-in gate")


@pytest.mark.skipif(
    os.environ.get(ENV) != "1",
    reason="JARVIS_REAL_BARGE_IN_TEST=1 required for physical TTS interruption",
)
def test_physical_tts_is_cancelled_by_barge_in():
    runtime = ConversationVoiceRuntime(UnusedSTT(), LocalTTS(KokoroEngine()))

    handle = runtime.speak(
        "This is a deliberately long Jarvis response used to verify physical "
        "barge in. The speech should stop before this sentence finishes. "
        "If you can still hear this final sentence, interruption did not work."
    )
    assert runtime.state is VoiceState.SPEAKING

    # Give synthesis/playback enough time to become audible on the target machine.
    time.sleep(2.0)
    runtime.barge_in()

    handle.wait(10.0)

    assert handle.stop.is_set()
    assert not handle.thread.is_alive()
    assert runtime.state is VoiceState.LISTENING
    assert runtime.follow_up_open is True
