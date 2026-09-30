# F5 PHYSICAL VOICE E2E GATE

Status: PASS / PHYSICAL TARGET MACHINE VERIFIED

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
        +-------------------------------+
        |                               |
        v                               v
    TranscriptWakeWordProvider      OpenWakeWordProvider
    (default generic path)          (optional custom ONNX path)
        |                               |
        +---------------+---------------+
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
             deterministic cognition
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

## Default physical path

No custom wake-word model is required.

The default gate uses local Faster-Whisper to transcript-match a configurable
wake phrase. It stays fully local and preserves the canonical WakeWordProvider
boundary.

Enable the gate:

    $env:JARVIS_REAL_VOICE_E2E = "1"
    $env:JARVIS_WAKE_PHRASE = "hey jarvis"

Install the real providers:

    python -m pip install -e ".[dev,voice,microphone,tts]"

Run:

    python -m pytest -q tests/test_f5_physical_voice_e2e.py -s

During the three-second capture window, say the configured phrase and a short
command, for example:

    Hey Jarvis status

## Optional optimized custom ONNX path

If an explicitly reviewed custom wake-word model is available, set:

    $env:JARVIS_WAKEWORD_MODEL_PATH = "C:\path\to\reviewed-model.onnx"

When this variable is present the gate keeps using OpenWakeWordProvider instead
of transcript matching. No model is silently selected or downloaded.

## PASS meaning

A PASS proves, on that machine:

- physical microphone capture;
- PCM16 handoff;
- local wake phrase detection;
- real faster-whisper transcription;
- transition into Jarvis conversation state;
- cognition invocation;
- real Kokoro synthesis;
- local audio playback path;
- return to IDLE after speech completion.

The custom ONNX path remains asset-governed by assets/provenance.toml.


## Verified physical evidence

Target Windows machine result:

    1 passed in 40.58s

Observed path:

    Realtek microphone
    -> local transcript wake detection ("hey jarvis")
    -> faster-whisper
    -> VoiceIngressRuntime
    -> JarvisCore
    -> KokoroEngine
    -> physical speaker playback
    -> IDLE

The microphone issue encountered during bring-up was external to Jarvis: the
selected Windows input initially produced near-silence. After correcting the
Windows/Realtek input configuration, physical capture measured a strong signal
and the complete gate passed.

F5 physical voice is therefore closed. Physical barge-in remains a separate
acceptance gate.
