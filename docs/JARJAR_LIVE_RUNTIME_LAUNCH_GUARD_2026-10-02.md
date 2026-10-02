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


## Last proven daily-use cognition baseline

Recovered from the 2026-10-01 working checkpoint:

- repository: `C:\Users\User\Desktop\Jarvis-iron-obsidia-`
- branch: `work/f5-generic-wake`
- exact HEAD: `de95095ca0e6740af78cfae2aad406132c42cb37`
- Python: `C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
- `JARJAR_BOUNDED_STRUCTURED_ROUTING_V0=1`
- `JARJAR_LOCAL_BRODY=1`

Critical implementation fact: this baseline calls the vendored `LocalBrodyRuntimeAdapter` first. HTTP Brody on 8012/8000 is fallback only. Therefore a daily-use launch must first prove:

```text
JARJAR_LOCAL_BRODY: PASS
memory=OBSIDIA_NATIVE_MEMORY
authority=KX108_ONLY
readonly=True
```

If `JARJAR_LOCAL_BRODY: using HTTP Brody fallback` appears for a normal Obsidia question, the local native runtime did not engage and the launch is NOT equivalent to the 2026-10-01 proven baseline.

### Safe exact recovery

To avoid disturbing development worktrees, create/use a detached worktree at the exact proven commit:

```powershell
cd C:\Users\User\Desktop\Jarvis-iron-obsidia-
git worktree add --detach C:\Users\User\Desktop\Jarvis-iron-obsidia-live de95095

cd C:\Users\User\Desktop\Jarvis-iron-obsidia-live
$env:JARJAR_BOUNDED_STRUCTURED_ROUTING_V0="1"
$env:JARJAR_LOCAL_BRODY="1"

& 'C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m scripts.run_jarjar_live
```

Do not promote this detached recovery worktree as a development branch. It is a reproducible daily-use baseline and diagnostic reference.
