# JARJAR MULTI-PROVIDER PHYSICAL CHECKPOINT

Date: 2026-09-30

## Physical routing gate

Validated on the target Windows machine with real local providers:

- general free-form question -> Qwen text on `127.0.0.1:8080`;
- visual desktop question -> Qwen-VL on `127.0.0.1:8081`;
- Obsidia/project question -> Brody/Obsidia on `127.0.0.1:8000`;
- deterministic system command -> FastIntent + ActionRouter.

Observed proof:

```text
ROUTE_GENERAL: qwen
ROUTE_VISUAL: vision
JARJAR_COGNITION: source=REAL_BRODY_RUNTIME_NO_GRAPHITI voice_runtime=BRODY_OBSIDIEN_V1_4_12A decision_authority=KX108_ONLY readonly=True
ROUTE_OBSIDIA: brody
ROUTE_ACTION: action_router
ACTION_RESPONSE: JARVIS_IRON_STATUS: READY
JARJAR_ROUTE_E2E: PASS
```

## Related physical gates already closed

- Qwen-VL camera image understanding: PASS.
- Qwen-VL dual-screen desktop understanding: PASS.
- Qwen text runtime: PASS.
- Brody bridge: PASS.
- Multi-monitor capture: PASS.
- Dual-camera capture: PASS.
- Voice STT/TTS/wake stack: PASS with half-duplex UX HOLD.

## Authority boundary

Qwen, Qwen-VL and Brody remain cognition providers only.

Actions still require:

`FastIntent/Intent -> PermissionPolicy -> ActionRouter -> compatible backend`

No cognition provider receives direct action authority.

## Quality caveat

This checkpoint proves routing/runtime execution, not factual correctness of all
model outputs. The Qwen text smoke produced an inaccurate explanation of why
the sky appears blue; factual quality/calibration remains a separate concern.

## Next gate

Run the global regression suite before expanding PC/device capabilities.
