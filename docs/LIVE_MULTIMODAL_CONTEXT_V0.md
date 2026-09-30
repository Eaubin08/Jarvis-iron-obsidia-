# Live multimodal context V0

Status: STRUCTURAL IMPLEMENTED / COGNITION CAUSALITY HOLD

Jarjar can now normalize fresh local environment evidence into the same
`PerceptualObservation` contract already used by Screenpipe.

Current live sources:

- current Windows multi-monitor topology;
- fresh frame from canonical camera-0;
- fresh frame from canonical camera-1.

`CompositePerceptualTimeline` can combine those observations with historical
Screenpipe context.

## Safety boundary

All observations use `live_handle=false` for context consumption. A context
observation ID or image path is not permission to click, execute, identify a
person, or trigger a gesture action.

There is no face recognition and no cross-camera identity inference.

## Current HOLD

The validated Jarjar -> Obsidia bridge currently calls `/api/brody/chat`
using the stack's canonical message/session contract. It does not yet have a
canonical field for injecting Jarjar's live multimodal context packet.

Therefore:

```text
LIVE SCREEN/CAMERA CONTEXT ASSEMBLY = IMPLEMENTED
LIVE CONTEXT CAUSAL TO BRODY ANSWER = NOT YET PROVEN
```

Do not concatenate camera/screen metadata into the human message merely to
force this integration. Wait for the governed OpenJarvis/Obsidia context
ingress seam.
