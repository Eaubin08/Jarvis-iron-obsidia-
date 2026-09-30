# F5 PHYSICAL BARGE-IN GATE

Status: READY / LOCAL PHYSICAL RUN REQUIRED

This gate verifies that the real local TTS playback can be interrupted through
the Jarvis-owned ConversationVoiceRuntime.bar​ge_in() path.

It exercises:

    ConversationVoiceRuntime
        -> LocalTTS
        -> KokoroEngine
        -> physical speaker playback
        -> barge_in()
        -> SpeechHandle.cancel()
        -> sounddevice stop
        -> LISTENING

No donor owns the cancellation state.

## Run

Enable the physical test:

    $env:JARVIS_REAL_BARGE_IN_TEST = "1"

Run with the prepared Python runtime:

    python -m pytest -q tests/test_f5_physical_barge_in.py -s

Expected physical observation:

- Jarvis begins speaking a deliberately long sentence.
- Roughly two seconds later, playback stops before the sentence finishes.
- The automated assertions pass with runtime state LISTENING and the follow-up
  window still open.

## PASS meaning

A PASS plus audible early cutoff proves the real Kokoro/local-audio SpeechHandle
can be cancelled through the canonical Jarvis barge-in path.

It does not yet prove acoustic echo cancellation or simultaneous
microphone-during-speaker speech recognition. Those remain separate concerns.
