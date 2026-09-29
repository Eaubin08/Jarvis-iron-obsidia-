# F5 WAKE INPUT RUNTIME

Status: IMPLEMENTED / DETERMINISTICALLY TESTED

Canonical input composition:

    MicrophoneProvider
        |
        v
    PCM16 16 kHz mono
        |
        v
    WakeWordProvider
        |
        +-- false --> stop; STT is not called
        |
        +-- true
              |
              v
        SpeechToTextProvider
              |
              v
          transcript

`WakeInputRuntime` contains no engine-specific code.

Safety / conservation rules:
- the captured audio must not be empty;
- the same audio buffer seen by the wake-word provider is sent to STT;
- STT is unreachable when wake detection is false;
- an empty transcript after a positive wake detection fails closed.

This checkpoint does not claim a physical end-to-end run. That requires a real
microphone and an explicitly supplied reviewed wake-word model.
