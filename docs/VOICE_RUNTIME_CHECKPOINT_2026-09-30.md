# VOICE RUNTIME CHECKPOINT — 2026-09-30

Status: FROZEN_WORKING_BASELINE

This checkpoint records the Jarjar voice behavior accepted after the 2026-09-30 debugging loop.

## Freeze rule

Do not retune or refactor the voice path unless a new test reproduces a specific voice defect.

Changes to routing, cognition, Brody, Qwen, Windows actions, music, vision, HUD content, or project knowledge must not alter the validated voice parameters below.

## Validated behavior

- One `Hey Jarvis` opens a conversational session.
- Follow-up turns do not require repeating the wake word.
- Wake capture releases the openWakeWord stream before opening the utterance recorder.
- Speech start requires sustained voice confirmation, not a single RMS spike.
- Long utterances can continue while speech continues.
- Natural hesitations and pauses are tolerated before closing a user turn.
- Empty follow-up windows do not immediately close the session.
- Session closes after bounded real inactivity and returns to wake monitoring.
- Self-echo filtering remains active.
- Incomplete Whisper fragments ending in ellipsis can be held and merged with the next follow-up.
- True duplex/barge-in while Jarjar is speaking remains HOLD; do not reactivate casually.
- TV/background-speaker discrimination remains HOLD for a later speaker-gate/calibration pass.

## Current timing / thresholds

- wake threshold: `0.32`
- speech RMS threshold: `300`
- speech confirmation: `3 x 50 ms = 150 ms`
- end-of-turn silence: `2.00 s`
- wake speech-start timeout: `6.0 s`
- follow-up speech-start timeout: `3.0 s`
- conversation idle timeout: `13.0 s`
- max utterance safety cap: `120.0 s`
- post-TTS cooldown: `0.10 s`

The 120 s value is a safety cap only. Normal turns must end by sustained silence, not by the cap.

## Relevant stabilization commits

- `1f5f62e` — clear follow-up state after empty wake transcript
- `85f1e77` — reset HUD/session after empty wake turn
- `d00a249` — self-echo protection
- `bbdea92` — microphone capture diagnostics
- `47705cb` — STT diagnostics / relaxed extreme no-speech gate
- `b1ad208` — sustained speech confirmation before utterance start
- `233e7a9` then `785b8ac` — natural pause tolerance, final value 2.00 s
- `44cc44a` — reduce post-TTS deaf gap to 0.10 s
- `8c82a4c` — hold/merge clearly incomplete Whisper follow-up fragments
- `955fcfd` — always-listening watchdog
- `7536bde` — wake microphone stream readiness diagnostics

## Known HOLD items

### HOLD — true duplex / barge-in
Goal later: keep listening while Jarjar speaks and allow the user to interrupt without Jarjar hearing its own TTS.
Existing self-echo logic should be reused.
Do not enable concurrent capture until a dedicated speaker/echo pass is performed.

### HOLD — television / other-speaker discrimination
TV speech can still be interpreted as user speech.
Future work should use speaker identification / personal calibration rather than phrase blacklists.

### HOLD — wake sensitivity
User sometimes needs to say `Hey Jarvis` relatively loudly.
Current threshold is accepted for now. Do not retune while the rest of the voice stack is stable.

## Not voice bugs

The following observed problems belong to other layers and must be fixed without changing this voice baseline:

- Qwen sometimes returns irrelevant vision/image fallback answers for non-visual questions.
- Some project/Obsidia questions can be misrouted to LOCAL/GUARD.
- Brody currently reaches a legacy Graphiti fallback on the detected runtime instead of canonical Native Memory.
- Structured Windows actions work for some commands (for example volume), but opening/controlling the multimedia player is not yet fully routed/executed.
- General understanding/project self-knowledge requires separate cognition/routing work.

## Regression guard

Before changing any voice file, compare against this checkpoint and preserve the accepted behaviors above unless the task explicitly targets voice.

Preferred next work: cognition/routing/action layers only.
