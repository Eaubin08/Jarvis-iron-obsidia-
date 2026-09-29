# F5 MICROPHONE REAL GATE

Status: READY / PHYSICAL DEVICE REQUIRED

Jarvis owns the microphone boundary through `MicrophoneProvider`.
`SoundDeviceMicrophone` performs one bounded capture and returns canonical
mono 16 kHz PCM16 bytes.

It performs no wake-word detection, speech recognition or conversation logic.

## Real-device gate

Install:

    python -m pip install -e ".[dev,microphone]"

Run on a machine with an accessible microphone:

    $env:JARVIS_REAL_MIC_TEST = "1"
    python -m pytest -q tests/test_f5_microphone_integration.py

The standard CI skips this physical-device test by design because hosted runners
do not prove access to a real microphone.

A PASS from this gate proves only microphone capture -> PCM16 bytes. It does
not prove acoustic quality, wake-word accuracy or end-to-end conversational
voice behavior.
