import os
import time
from threading import Event, Thread

import pytest

from jarvis.integrations.kokoro_engine import KokoroEngine
from jarvis.voice_runtime import ConversationVoiceRuntime, VoiceState


ENV = "JARVIS_REAL_BARGE_IN_TEST"


class UnusedSTT:
    def transcribe(self, audio):
        raise AssertionError("STT must not be used by the physical barge-in gate")


class PreSynthesizedPhysicalTTS:
    """Physical TTS test double: synthesis happens before speak(), playback stays real."""

    def __init__(self, engine, audio):
        self.engine = engine
        self.audio = audio

    def speak(self, text):
        if not text.strip():
            raise ValueError("speech text must not be empty")
        stop = Event()
        errors = []

        def run():
            try:
                self.engine.play(self.audio, stop)
            except BaseException as exc:
                errors.append(exc)

        thread = Thread(target=run, name="jarvis-physical-playback", daemon=True)
        thread.start()

        class Handle:
            def cancel(self):
                stop.set()

            def wait(self, timeout=None):
                thread.join(timeout)
                if errors:
                    raise errors[0]

            @property
            def stop(self):
                return stop

            @property
            def thread(self):
                return thread

        return Handle()


@pytest.mark.skipif(
    os.environ.get(ENV) != "1",
    reason="JARVIS_REAL_BARGE_IN_TEST=1 required for physical TTS interruption",
)
def test_physical_tts_playback_is_cancelled_by_barge_in():
    engine = KokoroEngine()

    # Synthesize before starting the timed interruption. This separates slow
    # model generation from the thing this gate is proving: live audio cutoff.
    audio = engine.synthesize(
        "This is a deliberately long Jarvis response used to verify physical "
        "barge in. You should hear this sentence begin, and then the playback "
        "must stop before I finish speaking the rest of this message."
    )

    runtime = ConversationVoiceRuntime(
        UnusedSTT(),
        PreSynthesizedPhysicalTTS(engine, audio),
    )

    handle = runtime.speak("pre-synthesized physical playback")
    assert runtime.state is VoiceState.SPEAKING

    # At this point audio playback has started; make the cutoff audible.
    time.sleep(2.0)
    runtime.barge_in()

    handle.wait(5.0)

    assert handle.stop.is_set()
    assert not handle.thread.is_alive()
    assert runtime.state is VoiceState.LISTENING
    assert runtime.follow_up_open is True
