# F5 PHYSICAL VOICE E2E GATE

Status: READY / LOCAL PHYSICAL RUN REQUIRED

This is the final physical gate for the current F5 voice chapter.

It composes the real runtime path:

    physical microphone
        |
        v
    SoundDeviceMicrophone
        |
        v
    PCM16 16 kHz mono
        |
        v
    OpenWakeWordProvider
        |
        v
    explicitly supplied wake-word model
        |
        v
    FasterWhisperSTT
        |
        v
    VoiceIngressRuntime
        |
        v
    JarvisCore
        |
        v
    deterministic cognition response
        |
        v
    ConversationVoiceRuntime
        |
        v
    LocalTTS
        |
        v
    KokoroEngine
        |
        v
    physical audio playback

## Requirements

No wake-word asset is bundled or downloaded.

The operator must provide an already reviewed model:

    $env:JARVIS_WAKEWORD_MODEL_PATH = "C:\path\to\reviewed-model.onnx"

The physical gate is enabled explicitly:

    $env:JARVIS_REAL_VOICE_E2E = "1"

Install the real providers:

    python -m pip install -e ".[dev,voice,wakeword,microphone,tts]"

Run:

    python -m pytest -q tests/test_f5_physical_voice_e2e.py -s

During the three-second capture window, speak the phrase corresponding to the
reviewed wake-word model.

## PASS meaning

A PASS proves, on that machine and for that supplied model:

- physical microphone capture;
- PCM16 handoff;
- real openWakeWord inference;
- real faster-whisper transcription;
- transition into Jarvis conversation state;
- cognition invocation;
- real Kokoro synthesis;
- local audio playback path;
- return to IDLE after speech completion.

It does not promote the supplied wake-word model to canonical status.
Canonical model provenance remains governed by `assets/provenance.toml`.
