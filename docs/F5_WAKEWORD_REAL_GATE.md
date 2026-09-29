# F5 WAKE-WORD REAL GATE

Status: READY / EXTERNAL ASSET REQUIRED

The real openWakeWord integration gate is intentionally asset-external.

## Contract

The test `tests/test_f5_wakeword_integration.py`:

- uses the real `openwakeword` package;
- loads a real model from `JARVIS_WAKEWORD_MODEL_PATH`;
- requires that path to exist before the provider is constructed;
- passes real PCM16 samples through `OpenWakeWordProvider.detect`;
- does not download a model;
- does not bundle a model;
- does not infer or silently select a default model.

## Run

Install the optional runtime:

    python -m pip install -e ".[dev,wakeword]"

Provide an explicitly reviewed model asset:

    $env:JARVIS_WAKEWORD_MODEL_PATH = "C:\\path\\to\\reviewed-model.onnx"
    python -m pytest -q tests/test_f5_wakeword_integration.py

Without `JARVIS_WAKEWORD_MODEL_PATH`, the real-model test is skipped by design.

## Licensing boundary

`hey_jarvis` or another upstream openWakeWord pre-trained model may be used only
when its license permits the intended context. It is not bundled and is not the
canonical Jarvis Iron production asset.

The final canonical target remains a Jarvis-owned or otherwise deployment-safe
model whose provenance, hash, license and rights are recorded in
`assets/provenance.toml`.
