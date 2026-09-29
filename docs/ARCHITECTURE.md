# Jarvis Iron — Architecture V0

## Principle

Jarvis is its own product and runtime.

External repositories are **donor projects**, never architectural authorities.
Obsidia is **not** a runtime dependency during V0.

## Internal flow

```text
Human
  |
Voice / UI
  |
Perception -> Context / Memory
  |               |
  +-----> Jarvis Core <----- CognitionProvider
              |
         ActionProvider
              |
   PC / Browser / Files / Tools
```

## Stable provider boundaries

- `CognitionProvider`
- `MemoryProvider`
- `PerceptionProvider`
- `ActionProvider`
- `VoiceProvider`

Donor integrations must live behind these boundaries.

## Build order

J0 — architecture and contracts
J1 — usable voice/cognition donor
J2 — donor adapter
J3 — daily voice / wake-word
J4 — computer/browser/files
J5 — screen perception
J6 — personal memory
J7 — agents/tasks/artifacts
J8 — HUD V0
J9 — camera/perception
J10 — remote/mobile

Future Obsidia integration is a separate phase.
