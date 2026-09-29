# Jarvis Iron — V0 Integration Test Matrix

Status: PRE-FREEZE

## Contract tests

T01 Jarvis boots with fake providers only.
T02 No donor import exists in Jarvis core.
T03 Each donor adapter maps into Jarvis-owned contracts.
T04 Provider failure returns explicit typed failure.
T05 Cancelling TTS permits barge-in.
T06 Fast deterministic intent bypasses cognition.
T07 Ambiguous intent escalates to cognition.
T08 Historical Screenpipe observation cannot be used as a live UI handle.
T09 ContextAssembler returns bounded context with provenance.
T10 Memory categories remain isolated.
T11 Cognition cannot directly execute an OS action.
T12 ActionRouter prefers structured/native backend over visual fallback.
T13 Permission denial prevents backend execution.
T14 ActionResult records backend and evidence.
T15 Long task can cancel/resume without donor-owned canonical state.
T16 HUD disconnect does not stop core.
T17 Donor service unavailable does not corrupt session state.
T18 Provider swap requires no JarvisCore change.

## Windows machine tests

W01 wake word -> STT latency.
W02 barge-in during TTS.
W03 follow-up without repeated wake word.
W04 exact command opens known application through structured backend.
W05 browser action uses DOM/Playwright before visual operator.
W06 UIA action targets correct window/control.
W07 visual fallback succeeds where UIA/DOM unavailable.
W08 multi-monitor coordinate correctness.
W09 Screenpipe query returns relevant recent context.
W10 screen context is refreshed before action.
W11 restart preserves durable memory but not ephemeral working state.
W12 microphone/camera permissions fail closed and visibly.

## Daily-use acceptance slice

User says a wake phrase,
asks Jarvis to inspect current activity,
asks a deterministic local action,
asks a contextual question about recent screen activity,
interrupts Jarvis while it is speaking,
then launches one bounded longer task.

Pass condition:
all steps work through Jarvis-owned contracts and no single donor owns the session.
