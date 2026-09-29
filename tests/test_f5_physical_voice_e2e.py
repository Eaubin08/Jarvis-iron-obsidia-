import os
from pathlib import Path

import pytest

from jarvis.core import JarvisCore
from jarvis.integrations.faster_whisper_stt import FasterWhisperSTT
from jarvis.integrations.kokoro_engine import KokoroEngine
from jarvis.integrations.local_tts import LocalTTS
from jarvis.integrations.microphone import SoundDeviceMicrophone
from jarvis.integrations.openwakeword_provider import OpenWakeWordProvider
from jarvis.voice_ingress_runtime import VoiceIngressRuntime
from jarvis.voice_runtime import ConversationVoiceRuntime, VoiceState
from jarvis.voice_turn_runtime import VoiceTurnRuntime
from jarvis.wake_input_runtime import WakeInputRuntime


E2E_ENV = "JARVIS_REAL_VOICE_E2E"
MODEL_ENV = "JARVIS_WAKEWORD_MODEL_PATH"


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
    os.environ.get(E2E_ENV) != "1" or not os.environ.get(MODEL_ENV),
    reason=(
        "physical voice E2E requires JARVIS_REAL_VOICE_E2E=1 and "
        "JARVIS_WAKEWORD_MODEL_PATH"
    ),
)
def test_physical_voice_turn_micro_wake_stt_cognition_kokoro():
    model_path = Path(os.environ[MODEL_ENV]).expanduser().resolve()
    assert model_path.is_file(), f"wake-word model not found: {model_path}"

    microphone = SoundDeviceMicrophone(sample_rate=16000)
    wake_word = OpenWakeWordProvider(model_path, threshold=0.5)
    stt = FasterWhisperSTT("tiny", device="cpu", compute_type="int8")
    tts = LocalTTS(KokoroEngine())
    conversation = ConversationVoiceRuntime(stt, tts)

    wake_input = WakeInputRuntime(microphone, wake_word, stt)
    ingress = VoiceIngressRuntime(wake_input, conversation)
    core = JarvisCore(DeterministicCognition(), EmptyMemory())
    runtime = VoiceTurnRuntime(ingress, core, conversation)

    handle = runtime.run_once(3.0)

    assert handle is not None, (
        "wake word was not detected; speak the reviewed wake phrase during capture"
    )
    assert conversation.state is VoiceState.SPEAKING

    handle.wait(30)
    conversation.speech_finished()

    assert conversation.state is VoiceState.IDLE
