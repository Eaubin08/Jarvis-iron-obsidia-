# F5 WAKE-WORD REAL GATE

Status: READY / GENERIC LOCAL PATH AVAILABLE

Jarvis Iron supports two local wake-word paths behind the same canonical
WakeWordProvider contract.

## 1. Generic transcript-match path

The default physical gate can use TranscriptWakeWordProvider with the already
integrated local Faster-Whisper STT provider.

Properties:

- configurable phrase;
- no custom wake-word model required;
- fully local;
- no cloud audio path;
- no donor runtime dependency;
- no hidden model selection;
- keeps WakeInputRuntime unchanged.

Focused automated coverage:

    python -m pytest -q tests/test_f5_transcript_wakeword_provider.py

Physical full-turn gate:

    $env:JARVIS_REAL_VOICE_E2E = "1"
    $env:JARVIS_WAKE_PHRASE = "hey jarvis"
    python -m pytest -q tests/test_f5_physical_voice_e2e.py -s

## 2. Optional custom OpenWakeWord path

The existing OpenWakeWordProvider remains supported for an explicitly supplied
custom ONNX model.

    $env:JARVIS_WAKEWORD_MODEL_PATH = "C:\path\to\reviewed-model.onnx"
    python -m pytest -q tests/test_f5_wakeword_integration.py

No OpenWakeWord named model is bundled or silently downloaded.

## Donor calibration

The pinned Personal Jarvis donor ships no built-in named wake word. Its generic
strategy prefers a user-owned custom ONNX model when available, otherwise a
local generic recognizer path. Jarvis Iron adopts the architectural principle
without importing donor runtime state or donor-specific objects.

## Licensing boundary

The optional custom ONNX path remains governed by assets/provenance.toml.
The transcript-match path introduces no new wake-word model asset.
