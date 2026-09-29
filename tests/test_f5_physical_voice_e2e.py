import os
from pathlib import Path

import pytest

from jarvis.core import JarvisCore
from jarvis.integrations.faster_whisper_stt import FasterWhisperSTT
from jarvis.integrations.kokoro_engine import KokoroEngine
from jarvis.integrations.local_tts import LocalTTS
from jarvis.integrations.microphone import SoundDeviceMicrophone
from jarvis.integrations.openwakeword_provider import OpenWakeWordProvider
from jarvis.integrations.transcript_wakeword_provider import TranscriptWakeWordProvider
from jarvis.voice_ingress_runtime import VoiceIngressRuntime
from jarvis.voice_runtime import ConversationVoiceRuntime, VoiceState
from jarvis.voice_turn_runtime import VoiceTurnRuntime
from jarvis.wake_input_runtime import WakeInputRuntime


E2E_ENV = "JARVIS_REAL_VOICE_E2E"
MODEL_ENV = "JARVIS_WAKEWORD_MODEL_PATH"
PHRASE_ENV = "JARVIS_WAKE_PHRASE"
CAPTURE_SECONDS_ENV = "JARVIS_VOICE_CAPTURE_SECONDS"


class DeterministicCognition:
    def respond(self, user_input, context):
        assert user_input.strip()
        return "Ready."


class EmptyMemory:
    class Snapshot:
        summary = ""
        metadata = {}
        provenance = ()

    def context(self):
        return self.Snapshot()

    def remember(self, event):
        return None


@pytest.mark.skipif(
    os.environ.get(E2E_ENV) != "1",
    reason="physical voice E2E requires JARVIS_REAL_VOICE_E2E=1",
)
def test_physical_voice_turn_micro_wake_stt_cognition_kokoro():
    microphone = SoundDeviceMicrophone(sample_rate=16000)
    stt = FasterWhisperSTT("small", device="cpu", compute_type="int8", language="en")

    model_value = os.environ.get(MODEL_ENV)
    transcript_wake = None
    if model_value:
        model_path = Path(model_value).expanduser().resolve()
        assert model_path.is_file(), f"wake-word model not found: {model_path}"
        wake_word = OpenWakeWordProvider(model_path, threshold=0.5)
    else:
        wake_phrase = os.environ.get(PHRASE_ENV, "hey jarvis")
        transcript_wake = TranscriptWakeWordProvider(stt, wake_phrase)
        wake_word = transcript_wake

    tts = LocalTTS(KokoroEngine())
    conversation = ConversationVoiceRuntime(stt, tts)

    wake_input = WakeInputRuntime(microphone, wake_word, stt)
    ingress = VoiceIngressRuntime(wake_input, conversation)
    core = JarvisCore(DeterministicCognition(), EmptyMemory())
    runtime = VoiceTurnRuntime(ingress, core, conversation)

    duration = float(os.environ.get(CAPTURE_SECONDS_ENV, "5.0"))
    handle = runtime.run_once(duration)

    diagnostic = ""
    if transcript_wake is not None:
        diagnostic = (
            f" Whisper heard: {transcript_wake.last_transcript!r}; "
            f"normalized: {transcript_wake.last_normalized_transcript!r}."
        )

    assert handle is not None, (
        "wake phrase was not detected; speak the configured wake phrase during capture."
        + diagnostic
    )
    assert conversation.state is VoiceState.SPEAKING

    handle.wait(30)
    conversation.speech_finished()

    assert conversation.state is VoiceState.IDLE
