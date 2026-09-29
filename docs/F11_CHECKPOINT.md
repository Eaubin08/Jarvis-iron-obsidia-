# F11 Checkpoint — Camera / Gesture

Status: IMPLEMENTED

## Scope

F11 adds Jarvis-owned camera and gesture perception boundaries:

- explicit camera enable/disable state;
- permission failure is represented as a fail-closed observation;
- provider output is normalized into `CameraObservation`;
- gesture interpretation is separate from action execution;
- gesture output becomes a canonical `ActionRequest` that must still cross the
  permission/action path.

No camera provider becomes canonical and no gesture provider can bypass
`ActionRouter`.

## Test Closure

W12: READY/PASS at contract level for camera permission fail-closed behavior.

Covered:

- disabled camera does not call provider;
- denied permission fails closed;
- enabled provider observation normalization;
- gesture interpretation separate from action execution;
- low-confidence gesture ignored.

## Holds

No physical camera device test is claimed. No gesture-driven OS action is
claimed without routing through Jarvis action contracts.
