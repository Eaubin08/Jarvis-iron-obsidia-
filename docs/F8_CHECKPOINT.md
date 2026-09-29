# F8 Checkpoint — Visual Operator Fallback

Status: IMPLEMENTED

## Scope

F8 adds a Jarvis-owned `VisualOperatorBackend` seam. Visual action remains a
fallback below structured native, browser, and accessibility-style backends and
above raw input.

The backend:

- exposes explicit `can_execute` semantics for `visual.*` capabilities;
- refreshes current visual state before consequential execution;
- records backend and evidence references in `ActionResult`;
- rejects historical Screenpipe/perceptual observation ids as live handles;
- keeps donor-specific visual operator objects behind an injected driver.

## Test Closure

T12: READY/PASS under focused automated tests.

W07: READY at contract level with fake visual provider. Physical visual
operator execution remains hardware/provider dependent and is not claimed.

T08/W10 boundary: reinforced by rejecting historical observation handles and
requiring current visual state refresh before action.

## Holds

No UI-TARS or other donor source is copied. No physical desktop visual action is
claimed as PASS.
