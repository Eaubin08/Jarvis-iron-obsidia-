# F9 Checkpoint — TaskRuntime

Status: IMPLEMENTED

## Scope

F9 adds a Jarvis-owned `TaskRuntime` with canonical in-process task state:

- `create(goal)`
- `step(task_id)`
- `cancel(task_id)`
- `resume(task_id)`

Task records include Jarvis task id, goal, status, steps, timestamps, artifacts,
evidence refs, explicit failures, and provider identity. External workers may
execute bounded steps, but they do not own canonical task/session state.

## Test Closure

T15: READY/PASS under focused automated tests.

Covered:

- create;
- step;
- cancel;
- resume;
- failed task;
- external provider unavailable without state corruption;
- external provider exception captured without losing canonical state;
- task event emission.

## Holds

No external agent donor is integrated in F9. Persistence beyond process memory
is not claimed for V0 TaskRuntime.
