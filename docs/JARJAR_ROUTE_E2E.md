# Jarjar physical routing E2E

This gate proves the current V0 split with real local providers:

- general free-form -> local Qwen text;
- visual question -> local Qwen-VL;
- Obsidia/project question -> Brody/Obsidia bridge;
- deterministic command -> FastIntent + ActionRouter.

Run with Qwen text on port 8080, Qwen-VL on port 8081, and the Obsidia API on
port 8000:

```powershell
python -m scripts.smoke_jarjar_route_e2e
```

Expected route markers:

```text
ROUTE_GENERAL: qwen
ROUTE_VISUAL: vision
ROUTE_OBSIDIA: brody
ROUTE_ACTION: action_router
JARJAR_ROUTE_E2E: PASS
```

The action gate uses only the read-only `system.status` capability. No visual,
LLM, or Brody provider gets action authority.
