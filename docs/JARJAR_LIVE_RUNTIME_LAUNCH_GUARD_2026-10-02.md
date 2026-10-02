# JARJAR LIVE RUNTIME LAUNCH GUARD

Status: ACTIVE INCIDENT GUARD
Date: 2026-10-02

## Why this file exists

Jarjar can boot successfully (wake/STT/TTS/HUD all green) while being connected to a stale Brody/Obsidia runtime. A successful HUD launch is therefore NOT proof that the cognition runtime is canonical.

Observed stale signature:

```text
Graphiti V20
Neo4j readonly
LOCAL_GRAPHITI_INDEX_FALLBACK
native_memory_active=False
legacy_memory_active=True
JARJAR_BRODY_LINK: DEGRADED
```

This stale state must never be accepted as a successful Jarjar launch.

## Mandatory preflight before daily-use Jarjar

1. Do not infer the Brody endpoint from an old freeze, a remembered port, or whichever port happens to answer.
2. Do not change Python environments merely because Jarjar fails to import a dependency; first recover the last proven launch environment.
3. Resolve the intended Obsidia checkout/branch/HEAD from the current checkpoint.
4. Inspect the process already listening on the candidate Brody port. A live uvicorn process may be stale even when HTTP 200.
5. Probe `/api/brody/chat` before launching Jarjar.
6. Accept the cognition runtime only when the returned trace proves the current canonical memory/runtime contract.

For the current Native Memory contract, required acceptance signals are:

```text
native_memory_active=True
legacy_memory_active=False
memory_source_mode=OBSIDIA_NATIVE_MEMORY
decision_authority=KX108_ONLY
readonly=True
JARJAR_BRODY_LINK: OK
```

Forbidden acceptance signals:

```text
LOCAL_GRAPHITI_INDEX_FALLBACK
local_graphiti_index
legacy_memory_active=True
native_memory_active=False
JARJAR_BRODY_LINK: DEGRADED
```

If any forbidden signal appears: STOP. Do not retune voice, do not modify Jarjar cognition code, and do not switch ports blindly. Identify and replace the stale Brody process/check-out first.

## Separation of concerns

- Jarjar worktrees such as `Jarvis-iron-obsidia-g4` are development/proof worktrees.
- Brody/Obsidia runtime provenance must be verified independently.
- G-series executor proofs do not prove the live cognition server is current.
- Voice/HUD success does not prove Brody correctness.

## Incident 2026-10-02

A restart sequence successfully launched Jarjar voice/HUD but connected it to stale Brody instances on both discovered ports during troubleshooting. The stale runtime returned an obsolete Graphiti/Neo4j project explanation. This was a runtime provenance error, not evidence that G0-G4 executor work regressed.

Permanent rule: launch instructions are not considered canonical until they include BOTH:
- exact executable + working directory + branch/HEAD provenance;
- a Brody preflight proving the expected memory/runtime signature.
