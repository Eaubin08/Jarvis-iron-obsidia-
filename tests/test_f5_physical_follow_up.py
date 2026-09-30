import os

import pytest

from jarvis.core import JarvisCore
from jarvis.integrations.faster_whisper_stt import FasterWhisperSTT
from jarvis.integrations.kokoro_engine import KokoroEngine
from jarvis.integrations.local_tts import LocalTTS
from jarvis.integrations.microphone import SoundDeviceMicrophone
from jarvis.integrations.transcript_wakeword_provider import TranscriptWakeWordProvider
from jarvis.voice_ingress_runtime import VoiceIngressRuntime
from jarvis.voice_runtime import ConversationVoiceRuntime, VoiceState
from jarvis.voice_turn_runtime import VoiceTurnRuntime
from jarvis.wake_input_runtime import WakeInputRuntime


ENV = "JARVIS_REAL_FOLLOW_UP_TEST"
CAPTURE_SECONDS_ENV = "JARVIS_VOICE_CAPTURE_SECONDS"


class CountingWakeWord:
    def __init__(self, provider):
        self.provider = provider
        self.calls = 0

    def detect(self, audio):
        self.calls += 1
        return self.provider.detect(audio)


class FrenchDeterministicCognition:
    def __init__(self):
        self.inputs = []

    def respond(self, user_input, context):
        self.inputs.append(user_input)
        if len(self.inputs) == 1:
            return "Je vous écoute."
        return "Deuxième demande reçue."


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
    os.environ.get(ENV) != "1",
    reason="JARVIS_REAL_FOLLOW_UP_TEST=1 required for physical follow-up",
)
def test_physical_follow_up_does_not_require_second_wake_phrase():
    microphone = SoundDeviceMicrophone(sample_rate=16000)
    stt = FasterWhisperSTT("tiny", device="cpu", compute_type="int8")
    wake_word = CountingWakeWord(TranscriptWakeWordProvider(stt, "hey jarvis"))

    conversation = ConversationVoiceRuntime(stt, LocalTTS(KokoroEngine()))
    ingress = VoiceIngressRuntime(
        WakeInputRuntime(microphone, wake_word, stt),
        conversation,
    )
    cognition = FrenchDeterministicCognition()
    runtime = VoiceTurnRuntime(
        ingress,
        JarvisCore(cognition, EmptyMemory()),
        conversation,
    )

    duration = float(os.environ.get(CAPTURE_SECONDS_ENV, "5.0"))

    print("\nTOUR 1: dites 'Hey Jarvis status'")
    first = runtime.run_once(duration)
    assert first is not None, "first wake phrase was not detected"
    assert wake_word.calls == 1

    first.wait(30.0)
    conversation.speech_finished()
    assert conversation.follow_up_open is True

    print("\nTOUR 2: parlez sans dire 'Hey Jarvis' (ex: 'donne le statut')")
    second = runtime.run_follow_up_once(duration)

    # Core proof for W03: second physical capture did not invoke wake detection.
    assert wake_word.calls == 1
    assert len(cognition.inputs) == 2
    assert cognition.inputs[1].strip()
    assert conversation.state is VoiceState.SPEAKING

    second.wait(30.0)
    conversation.speech_finished()
    assert conversation.state is VoiceState.IDLE
