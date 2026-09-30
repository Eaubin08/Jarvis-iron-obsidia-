"""Launch Jarjar HUD with the real local microphone/STT/TTS chain.

Cognition remains a replaceable V0 provider. Brody/Obsidia are deliberately
not required for this standalone desktop milestone.
"""
from __future__ import annotations

import os
import threading

from jarvis.core import JarvisCore
from jarvis.hud_app import run_hud
from jarvis.hud_controller import HUDController
from jarvis.hud_live_runtime import HUDLiveVoiceBridge
from jarvis.hud_state import HUDModel, HUDState
from jarvis.integrations.faster_whisper_stt import FasterWhisperSTT
from jarvis.integrations.kokoro_engine import KokoroEngine
from jarvis.integrations.local_tts import LocalTTS
from jarvis.integrations.microphone import SoundDeviceMicrophone
from jarvis.integrations.transcript_wakeword_provider import TranscriptWakeWordProvider
from jarvis.providers.local_stub import StubCognition, StubMemory
from jarvis.voice_ingress_runtime import VoiceIngressRuntime
from jarvis.voice_runtime import ConversationVoiceRuntime
from jarvis.wake_input_runtime import WakeInputRuntime


def build_live_controller() -> HUDController:
    model = HUDModel()
    microphone = SoundDeviceMicrophone(sample_rate=16000)
    stt = FasterWhisperSTT(
        os.getenv("JARVIS_STT_MODEL", "tiny"),
        device="cpu",
        compute_type="int8",
        language=os.getenv("JARVIS_STT_LANGUAGE", "fr") or None,
    )
    wake = TranscriptWakeWordProvider(
        stt,
        os.getenv("JARVIS_WAKE_PHRASE", "hey jarvis"),
    )
    kokoro = KokoroEngine(lang_code="f", voice="ff_siwis")
    conversation = ConversationVoiceRuntime(
        stt,
        LocalTTS(kokoro),
    )
    ingress = VoiceIngressRuntime(
        WakeInputRuntime(microphone, wake, stt),
        conversation,
    )
    core = JarvisCore(StubCognition(), StubMemory())
    bridge = HUDLiveVoiceBridge(
        ingress=ingress,
        core=core,
        conversation=conversation,
        capture_seconds=float(os.getenv("JARVIS_VOICE_CAPTURE_SECONDS", "2.5")),
    )

    # Load the heavier local models while the HUD is appearing so the first
    # real interaction does not pay all initialization cost.
    def warm_models():
        for provider in (stt, kokoro):
            try:
                provider.warmup()
            except Exception as exc:
                model.append("SYSTEM", f"warmup {type(provider).__name__}: {exc}")

    threading.Thread(target=warm_models, name="jarjar-model-warmup", daemon=True).start()

    controller_ref = {}

    def text_handler(text: str) -> str:
        reply = core.handle_text(text).strip()
        controller = controller_ref["controller"]
        if controller.model.voice_enabled:
            controller.model.set_state(HUDState.SPEAKING)
            bridge.speak_text_reply(reply)
        return reply

    controller = HUDController(
        model=model,
        text_handler=text_handler,
        voice_turn_handler=bridge.run_wake_turn,
        follow_up_turn_handler=bridge.run_follow_up_turn,
    )
    controller_ref["controller"] = controller
    return controller


if __name__ == "__main__":
    run_hud(build_live_controller())
