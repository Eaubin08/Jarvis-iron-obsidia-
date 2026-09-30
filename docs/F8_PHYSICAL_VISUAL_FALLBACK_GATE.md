# F8 PHYSICAL VISUAL FALLBACK GATE

Status: READY / LOCAL PHYSICAL RUN REQUIRED

This gate verifies W07 without touching personal applications or websites.

The test creates a temporary local Tk window containing one button, then routes
a canonical `visual.click` request through:

    ActionRouter
      -> VisualOperatorBackend
      -> fresh PyAutoGUI screenshot
      -> bounded coordinate click
      -> local test button

The backend stores the fresh screenshot under
`runtime_data/visual_snapshots/` and returns both the visual-state receipt and
the screenshot evidence reference.

Historical Screenpipe observations are still rejected by the existing F8
contract and are never reused as live action handles.

## Install

    python -m pip install -e ".[visual]"

## Run

    $env:JARVIS_REAL_VISUAL_TEST = "1"
    python -m pytest -q tests/test_f8_physical_visual_fallback.py -s

A small "Jarvis Visual Gate" window should appear briefly and its CLICK ME
button should be physically clicked.

## PASS meaning

A PASS proves on the target Windows machine that:

- a fresh physical screen snapshot was acquired before action;
- the visual backend executed a bounded real mouse click;
- the click hit the intended local test target;
- ActionRouter returned `visual.operator`;
- fresh visual-state and screenshot evidence references were emitted.

This is a coordinate visual fallback proof. It does not yet claim OCR/object
detection, semantic screen understanding, or multi-monitor coordinate
correctness.
