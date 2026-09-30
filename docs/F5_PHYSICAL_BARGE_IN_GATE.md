# F5 PHYSICAL BARGE-IN GATE

Status: PASS / PHYSICAL PLAYBACK VERIFIED; FRENCH VOICE RETEST REQUIRED

This gate verifies that real local speaker playback can be interrupted through
the Jarvis-owned ConversationVoiceRuntime.barge_in() path.

The first physical attempt exposed an important distinction: Kokoro synthesis
can take longer than the two-second interruption delay. Cancelling during that
generation phase sets the SpeechHandle stop flag, but there may be no audible
playback yet and the synthesis thread can still be alive.

Therefore this gate deliberately separates synthesis from playback:

    KokoroEngine(lang_code='f', voice='ff_siwis').synthesize()
        -> complete WAV prepared first
        -> ConversationVoiceRuntime.speak()
        -> real KokoroEngine.play()
        -> physical speakers
        -> wait about 2 seconds
        -> barge_in()
        -> SpeechHandle.cancel()
        -> sounddevice stop
        -> LISTENING

The physical playback cancellation gate already passed on the target machine (`1 passed in 28.83s`). The French rerun keeps the same boundary while switching Jarvis to the supported Kokoro French voice `ff_siwis`. This proves the current V0 barge-in contract at the playback boundary without
misclassifying Kokoro generation latency as a playback cancellation failure.

## Run

Enable the physical test:

    $env:JARVIS_REAL_BARGE_IN_TEST = "1"

Run:

    python -m pytest -q tests/test_f5_physical_barge_in.py -s

Expected physical observation:

- there may be an initial synthesis delay before any sound;
- Jarvis then begins speaking;
- approximately two seconds after playback starts, the voice stops before the
  sentence finishes;
- pytest passes;
- runtime ends in LISTENING with follow-up open.

## PASS meaning

A PASS plus audible early cutoff proves:

- real Kokoro-generated audio is played locally;
- the canonical Jarvis SpeechHandle cancellation reaches physical playback;
- sounddevice playback stops;
- ConversationVoiceRuntime transitions to LISTENING;
- follow-up remains open.

This does NOT yet prove cancellation of Kokoro while synthesis itself is in
progress, nor acoustic echo cancellation / simultaneous microphone recognition.
Those are separate capabilities and must not be claimed by this gate.


## French Jarvis voice

The default Jarvis Kokoro adapter now uses:

    lang_code = "f"
    voice = "ff_siwis"

This matches the current Kokoro-82M French catalogue. French currently has one
published voice in that catalogue, so voice choice is intentionally explicit
rather than guessed.
