# J1 — First usable runtime

## Decision

Run Personal Jarvis as an **independent donor runtime** and connect it to
Jarvis Iron through a transport adapter.

Do not vendor or fork the donor into Jarvis Core.

Pinned audit target:

`PersonalJarvis/PersonalJarvis@53d8c4d16f7baf5cfbfb2e02896fae4b89c4628f`

## Why this path

The donor already provides:
- desktop application;
- voice and wake phrase;
- model/provider setup;
- agents;
- MCP;
- computer use;
- headless API/browser mode;
- Windows support.

Jarvis Iron keeps ownership of:
- its contracts;
- its future event model;
- its future memory model;
- donor selection;
- future Obsidia integration seam.

## J1 gates

### J1-A — CLOSED
Pin exact upstream and establish adapter boundary.

### J1-B — NEXT
Verify the donor's supported public HTTP/WebSocket chat surface and implement
a concrete transport without importing donor internals.

### J1-C
Add a Windows bootstrap that:
1. checks Python/Git;
2. installs the pinned donor into an isolated directory;
3. launches it;
4. checks readiness;
5. starts Jarvis Iron.

### J1-D
Prove one text round trip.

### J1-E
Prove one voice round trip.

### J1-F
Prove one bounded computer action through the donor's own approval/safety path.

## Explicit non-goals

- no HUD merge;
- no screenpipe yet;
- no camera;
- no mobile;
- no Obsidia/Sens/Cognition runtime.
