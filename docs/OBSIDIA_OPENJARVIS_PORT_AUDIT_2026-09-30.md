# OBSIDIA / OPENJARVIS PORT AUDIT — 2026-09-30

## Boundary

Canonical source inspected READ_ONLY:
`Eaubin08/obsidia-x108-proofs`

Target for all integration work:
`Eaubin08/Jarvis-iron-obsidia-` branch `build/jarvis-v0`

No canonical Obsidia file was modified.

## Main finding

Jarjar's temporary `CostAwareCognitionRouter` currently reimplements only a
small part of routing that already exists in the Obsidia stack.

The canonical stack already defines a pre-inference cascade:

```
user input
 -> deterministic router / IR / gates
 -> local/native stack route where sufficient
 -> semantic/native memory
 -> Brody
 -> external/model escalation only when necessary
```

This is the architecture Jarjar should consume/adapt instead of accumulating
new phrase regexes.

## Canonical components identified

### 1. Gateway / pre-inference routing
Source: `scripts/obsidia_gateway.py`

Documented cascade:
- Level 0: router / DENY / HOLD / CLARIFY / local status
- Level 2: semantic/native memory
- Level 1: Brody local
- Level 3: model escalation

The gateway records whether model calls were avoided and preserves
`decision_authority=KX108_ONLY`.

### 2. Canonical RouteDecision / RouteReceipt
Source: `scripts/obsidia_gateway_route_decision_v0.py`

Useful for Jarjar because it separates:
- STACK_NATIVE
- LLM_LANGUAGE
- LLM_REASONING
- LLM_ENGINEERING
- HUMAN_AUTHORITY
- UNKNOWN

The object is explicitly non-sovereign and cannot authorize execution.

### 3. Brody semantic query router
Source: `apps/obsidia_api/brody_semantic_query_router.py`

This already provides a richer semantic routing layer for Brody than Jarjar's
temporary project keyword matcher.

### 4. Brody domain raccord
Source: `apps/obsidia_api/brody_domain_raccord_adapter.py`

Already handles architecture, authority, runtime-state, negation, memory-write
boundaries and several Obsidia semantic domains while preserving readonly and
KX108_ONLY boundaries.

### 5. Native Memory response chain
Source: `apps/obsidia_api/brody_native_memory_response_adapter.py`

Canonical contract:
- schema `BRODY_NATIVE_MEMORY_RESPONSE_V1`
- source `OBSIDIA_NATIVE_MEMORY`
- readonly
- no memory/canonical write
- no ACT/verdict
- KX108_ONLY
- success may expose `BRODY_MEMORY_RESPONSE_CHAIN_PASS`

This is the target memory path. Graphiti/Neo4j fallback currently observed on
Jarjar's active Brody endpoint is legacy/degraded behavior, not the target
architecture.

## Port created in Jarjar

Copied as isolated snapshots under:

`src/jarvis/obsidia_port/`

- `obsidia_gateway_route_decision_v0.py`
- `brody_semantic_query_router.py`
- `brody_domain_raccord_adapter.py`
- `brody_native_memory_response_adapter.py`

Each copy carries its canonical source path and source blob SHA.

These copies are deliberately NOT wired into live Jarjar yet. Some imports and
runtime assumptions still point to the canonical Obsidia package/layout; wiring
them blindly would create regressions.

## Integration plan

1. Adapt imports/dependencies inside the isolated port only.
2. Build a Jarjar `ObsidiaPreInferenceAdapter` over the ported RouteDecision.
3. Replace the temporary regex-first cognition selection with the canonical
   route classes.
4. Bind STACK_NATIVE/Brody paths to the existing Jarjar cognition bridge.
5. Bind actions only after Jarjar's PermissionPolicy/ActionRouter, never
   directly from Brody/Qwen.
6. Bind Native Memory response consumption when the canonical runtime endpoint
   is available.
7. Keep Qwen as actual fallback/escalation instead of default cognition.
8. Add regression tests before removing the temporary router.

## Frozen boundary

Do not change `docs/VOICE_RUNTIME_CHECKPOINT_2026-09-30.md` parameters while
doing this integration.

Voice, wake, STT timing, anti-echo and session behavior are out of scope.
