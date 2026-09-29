# F12 Checkpoint — Mobile / Device Bridge

Status: IMPLEMENTED

## Scope

F12 adds a minimal Jarvis-owned device/mobile bridge protocol:

- authenticated session boundary;
- device connect/disconnect events;
- logical command model aligned with HUD/client commands;
- device `action.request` converts to canonical `ActionRequest`;
- non-action/raw commands cannot bypass `ActionRouter`;
- disconnect removes only the device session and does not corrupt core/event bus
  state.

No donor-internal calls cross the bridge.

## Test Closure

READY/PASS under focused automated tests.

Covered:

- failed authentication closes transport and rejects commands;
- authenticated command becomes canonical request;
- disconnect does not corrupt event bus;
- non-action raw command cannot bypass action routing.

## Holds

No physical phone transport, push channel, or network pairing is claimed. F12 is
the minimal V0 protocol boundary.
