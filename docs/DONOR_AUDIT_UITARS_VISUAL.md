# UI-TARS DONOR AUDIT — VISUAL GROUNDING

Status: PARTIAL ADOPTION / GROUNDING CONTRACT ONLY

Upstream donors:
- ByteDance `UI-TARS` (Apache-2.0)
- ByteDance `UI-TARS-desktop` (Apache-2.0)

## What is useful

UI-TARS exposes a desktop action language around screenshots, including click,
double-click, right-click, drag, hotkey, typing, scroll, wait and finished.
Its grounding mode can emit only the next action without requiring the full
agent reasoning loop.

For Qwen2.5-VL-based models, coordinates are expressed in the resized image
space and must be projected back to the original screenshot dimensions.

## What Jarvis adopts now

Jarvis adopts only:

- the screenshot -> semantic instruction -> grounded action seam;
- the UI-TARS coordinate smart-resize/reprojection concept;
- strict parsing of a single grounded click action;
- execution through the existing Jarvis visual driver.

New Jarvis-owned pieces:

- `visual_grounding.py`
- `UITARSGroundedVisualDriver`
- capability `visual.semantic_click`

## What Jarvis explicitly does NOT adopt

- UI-TARS agent loop as Jarvis authority;
- generated Python/PyAutoGUI code execution;
- unrestricted multi-action strings;
- donor task/session state;
- donor browser operator where Playwright already has higher priority;
- multi-monitor claims.

## Safety / architecture

The semantic grounder never executes actions itself.

Flow:

    ActionRouter
      -> PermissionPolicy
      -> VisualOperatorBackend
      -> fresh screenshot
      -> UI-TARS-compatible grounding provider
      -> strict parsed GroundedAction
      -> bounded PyAutoGUIVisualDriver action

Historical Screenpipe observations remain invalid as live handles.

The current donor documentation explicitly warns that UI-TARS Desktop is
single-monitor oriented and multi-monitor setups may fail. W08 therefore
remains open and must not be inferred from this integration.

## Next

1. Run unit tests for parser/reprojection/grounded driver.
2. Add a model-provider adapter only when a concrete local or remote UI-TARS
   endpoint is selected.
3. Physical semantic-click gate on a disposable local UI.
4. Continue to Agent Zero after visual grounding closure.
