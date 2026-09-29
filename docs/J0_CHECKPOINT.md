# J0 Checkpoint

Status: **STRUCTURAL PASS**

## Closed

- repository bootstrapped;
- dedicated `build/jarvis-v0` branch;
- standalone Jarvis package skeleton;
- Jarvis-owned provider contracts;
- explicit no-Obsidia-runtime boundary;
- donor policy;
- first donor Gate-0 audits;
- zero mandatory runtime dependencies in core.

## Current architectural invariant

```text
DONOR PROJECT -> ADAPTER -> JARVIS CONTRACT -> JARVIS CORE
```

Never:

```text
JARVIS CORE -> DONOR INTERNALS
```

## J1 target

Produce the first daily-usable Jarvis runtime without waiting for HUD, camera,
mobile or future Obsidia integration.

Preferred first donor: Personal Jarvis, subject to exact module/commit audit.

J1 success means:
1. Jarvis launches on Windows;
2. user can talk or type to it;
3. it can answer;
4. at least one bounded computer capability works;
5. donor implementation remains replaceable behind Jarvis contracts.
