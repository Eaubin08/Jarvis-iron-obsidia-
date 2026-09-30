# F5 PHYSICAL FOLLOW-UP GATE

Status: READY / LOCAL PHYSICAL RUN REQUIRED

This gate verifies W03: after one wake-triggered voice turn, Jarvis accepts a
second physical microphone turn without requiring the wake phrase again.

Canonical path:

    first turn:
    microphone -> wake phrase -> STT -> cognition -> French TTS
                                      |
                                      v
                              follow_up_open = true

    second turn:
    microphone -> STT -> cognition -> French TTS
                 (NO wake-word detector call)

The runtime fails closed if the follow-up window is not open.

## Run

    $env:JARVIS_REAL_FOLLOW_UP_TEST = "1"
    $env:JARVIS_VOICE_CAPTURE_SECONDS = "5"

    python -m pytest -q tests/test_f5_physical_follow_up.py -s

During TOUR 1 say:

    Hey Jarvis status

After Jarvis answers "Je vous écoute.", TOUR 2 is announced. Then say, without
repeating the wake phrase:

    donne le statut

## PASS meaning

A PASS proves on the target machine that:

- the first turn required wake detection;
- Jarvis opened the follow-up window after speaking;
- the second microphone capture went directly to STT;
- the wake detector call count remained exactly one across both turns;
- the second transcript reached cognition;
- Jarvis generated and played the second French response.

This does not yet prove an automatically timed conversational listening window,
echo cancellation, or interruption while the microphone is simultaneously
listening. Those are separate gates.
