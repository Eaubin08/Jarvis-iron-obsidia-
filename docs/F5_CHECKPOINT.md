# F5 CHECKPOINT — VOICE

Status: CODE/CI CLOSED — PHYSICAL E2E HOLD

Branch: `build/jarvis-v0`

Canonical closure commit before checkpoint:
`020fd2286cfb7bdd9caf6d46f4d54d2573514ec3`

Standard CI proof:
`36614462845` — SUCCESS

## Closed

- SpeechToTextProvider boundary
- FasterWhisperSTT adapter
- real faster-whisper model gate
- TextToSpeechProvider boundary
- LocalTTS cancellable adapter
- KokoroEngine
- real Kokoro synthesis gate
- MicrophoneProvider boundary
- SoundDeviceMicrophone
- bounded mono 16 kHz PCM16 contract
- WakeWordProvider boundary
- OpenWakeWordProvider
- explicit model_path requirement
- no bundled wake-word model
- no implicit wake-word model download
- asset provenance/license registry
- hey_jarvis classified DEV/PERSONAL ONLY
- WakeInputRuntime
- VoiceIngressRuntime
- ConversationVoiceRuntime
- VoiceTurnRuntime
- deterministic full-turn tests
- opt-in physical voice E2E gate

## Canonical path

    physical microphone
        ↓
    SoundDeviceMicrophone
        ↓
    PCM16 16 kHz mono
        ↓
    OpenWakeWordProvider
        ↓
    explicit external model
        ↓
    FasterWhisperSTT
        ↓
    WakeInputRuntime
        ↓
    VoiceIngressRuntime
        ↓
    ConversationVoiceRuntime / THINKING
        ↓
    JarvisCore
        ↓
    response
        ↓
    LocalTTS
        ↓
    KokoroEngine
        ↓
    SPEAKING
        ↓
    speech_finished()
        ↓
    IDLE

## Remaining HOLD

Only the physical end-to-end execution is not yet claimed.

Required local conditions:

- accessible physical microphone;
- explicitly reviewed wake-word model;
- `JARVIS_WAKEWORD_MODEL_PATH`;
- `JARVIS_REAL_VOICE_E2E=1`;
- real wake phrase spoken during the capture window;
- local audio output available.

A physical PASS does not automatically promote the supplied wake-word model to
canonical production status. Model provenance and deployment rights remain a
separate gate under `assets/provenance.toml`.
