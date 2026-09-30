"""Launch Jarjar HUD with streaming wake word + local STT/TTS."""
from __future__ import annotations

import os

from jarvis.core import JarvisCore
from jarvis.hud_app import run_hud
from jarvis.hud_controller import HUDController
from jarvis.hud_live_runtime import HUDLiveVoiceBridge
from jarvis.hud_state import HUDModel, HUDState
from jarvis.integrations.faster_whisper_stt import FasterWhisperSTT
from jarvis.integrations.kokoro_engine import KokoroEngine
from jarvis.integrations.local_tts import LocalTTS
from jarvis.integrations.microphone import SoundDeviceMicrophone
from jarvis.integrations.openwakeword_provider import OpenWakeWordProvider
from jarvis.cognition_bridge import CostAwareCognitionRouter
from jarvis.camera_rig import CameraRig
from jarvis.integrations.live_environment_timeline import LiveEnvironmentTimeline
from jarvis.integrations.local_qwen_cognition import from_environment as qwen_cognition_from_environment
from jarvis.integrations.local_vision_cognition import from_environment as vision_cognition_from_environment
from jarvis.integrations.pyautogui_visual_driver import PyAutoGUIVisualDriver
from jarvis.integrations.obsidia_stack_cognition import from_environment as obsidia_cognition_from_environment
from jarvis.monitor_layout import WindowsMonitorProvider
from jarvis.providers.local_stub import StubCognition, StubMemory
from jarvis.streaming_voice_ingress import StreamingVoiceIngress
from jarvis.voice_runtime import ConversationVoiceRuntime


def build_live_controller() -> HUDController:
    model = HUDModel()
    microphone = SoundDeviceMicrophone(sample_rate=16000)
    stt = FasterWhisperSTT(
        os.getenv("JARVIS_STT_MODEL", "tiny"),
        device="cpu",
        compute_type="int8",
        language=os.getenv("JARVIS_STT_LANGUAGE", "fr") or None,
    )
    wake = OpenWakeWordProvider.builtin(
        os.getenv("JARVIS_WAKEWORD_MODEL", "hey_jarvis"),
        threshold=float(os.getenv("JARVIS_WAKEWORD_THRESHOLD", "0.32")),
        inference_framework="onnx",
    )
    kokoro = KokoroEngine(lang_code="f", voice="ff_siwis")

    print("JARJAR_BOOT: loading openWakeWord...")
    wake.warmup()
    print("JARJAR_BOOT: loading Whisper...")
    stt.warmup()
    print("JARJAR_BOOT: loading Kokoro...")
    kokoro.warmup()
    print(f"JARJAR_BOOT: voice stack ready (wake threshold={wake.threshold:.2f})")

    conversation = ConversationVoiceRuntime(stt, LocalTTS(kokoro))
    ingress = StreamingVoiceIngress(
        microphone=microphone,
        wake_word=wake,
        stt=stt,
        conversation=conversation,
        max_utterance_seconds=float(os.getenv("JARVIS_MAX_UTTERANCE_SECONDS", "8.0")),
        silence_seconds=float(os.getenv("JARVIS_END_SILENCE_SECONDS", "0.35")),
        rms_threshold=int(os.getenv("JARVIS_SPEECH_RMS_THRESHOLD", "300")),
        wake_speech_start_timeout=float(os.getenv("JARVIS_WAKE_SPEECH_TIMEOUT", "3.0")),
        follow_up_start_timeout=float(os.getenv("JARVIS_FOLLOW_UP_TIMEOUT", "4.0")),
    )
    local_presence = StubCognition()
    governed_stack = obsidia_cognition_from_environment()

    live_timeline = None
    if os.getenv("JARJAR_LIVE_CONTEXT", "1").strip().lower() not in {"0", "false", "no", "off"}:
        camera_indices = tuple(
            int(x.strip())
            for x in os.getenv("JARJAR_CAMERA_INDICES", "0,1").split(",")
            if x.strip()
        )
        camera_rig = CameraRig.from_device_indices(camera_indices)
        camera_rig.enable_all(permission_granted=True)
        live_timeline = LiveEnvironmentTimeline(
            monitor_provider=WindowsMonitorProvider(),
            camera_rig=camera_rig,
            visual_driver=PyAutoGUIVisualDriver(),
        )

    qwen = qwen_cognition_from_environment(live_timeline=live_timeline)
    vision = vision_cognition_from_environment(live_timeline=live_timeline)
    cognition = CostAwareCognitionRouter(
        local_presence=local_presence,
        governed_stack=governed_stack,
        qwen=qwen,
        vision=vision,
    )
    core = JarvisCore(cognition, StubMemory())
    print(
        "JARJAR_BOOT: cognition bridge ready "
        f"(Obsidia={governed_stack.endpoint}, provider-routing={'on' if governed_stack.allow_provider else 'off'})"
    )
    print(
        "JARJAR_BOOT: cost router ready "
        f"(Qwen={qwen.endpoint}, live-context={'on' if live_timeline is not None else 'off'})"
    )
    print(
        "JARJAR_BOOT: vision route ready "
        f"(Vision={vision.endpoint}, model={vision.model})"
    )
    bridge = HUDLiveVoiceBridge(
        ingress=ingress,
        core=core,
        conversation=conversation,
        capture_seconds=0.1,
    )

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
    model.append("SYSTEM", "Voix prête. Dis « Hey Jarvis » ; je réponds, puis parle normalement.")
    return controller


if __name__ == "__main__":
    print("JARJAR_BOOT: building live controller")
    controller = build_live_controller()
    print("JARJAR_BOOT: controller ready, launching HUD")
    run_hud(controller)
    print("JARJAR_BOOT: HUD exited")
