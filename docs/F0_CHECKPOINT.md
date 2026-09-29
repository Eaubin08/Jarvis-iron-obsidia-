# F0 CHECKPOINT — Canonical contracts/events

Date: 2026-09-29
Status: IMPLEMENTED / TESTS AUTHORED / MACHINE EXECUTION PENDING

## Implemented

- expanded JarvisEvent identity/session/correlation fields
- ContextSnapshot provenance
- ActionRequest target/source/session/task/risk/idempotency
- ActionResult backend/timestamps/evidence
- Capability contract
- CapabilityRegistry contract
- PermissionPolicy contract
- ActionBackend contract
- split wake/STT/TTS contracts
- in-process Jarvis EventBus
- Jarvis-owned ActionRouter
- backend priority independent of donor identity

## Compatibility

Existing:
- StubMemory / StubCognition
- PersonalJarvisCognition
- PersonalJarvisWebSocketTransport

continue to consume compatible ContextSnapshot/CognitionProvider surfaces.

Legacy VoiceProvider remains temporarily as a compatibility seam.
It is not the frozen voice architecture.

## Tests authored

tests/test_f0_contracts.py covers:
- event identity/time/session
- context provenance
- action risk/idempotency
- structured backend priority
- permission denial blocks execution
- event bus routing without donor/UI

Existing standalone and Personal Jarvis adapter tests remain present.

## Verdict

F0_IMPLEMENTATION = PASS STRUCTURAL
F0_MACHINE_TEST = PENDING

Do not advance the checkpoint to fully CLOSED until pytest is executed in a
real checkout/CI environment and passes.

Next after machine verification:
F1 — local text runtime + fake providers + canonical event emission.
