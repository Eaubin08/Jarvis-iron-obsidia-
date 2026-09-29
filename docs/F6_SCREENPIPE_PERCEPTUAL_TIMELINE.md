# F6 SCREENPIPE PERCEPTUAL TIMELINE

Status: IMPLEMENTED / CONTRACT TESTED

Screenpipe is an external localhost historical perception service.

Jarvis owns the canonical contract:

    PerceptualTimeline.query(...)
        ↓
    PerceptualObservation[]

The Screenpipe adapter normalizes donor/service data into Jarvis-owned immutable
observations.

## Hard invariant

A historical Screenpipe result is never a live UI/action handle.

Even if donor payloads contain coordinates, element IDs or similar fields,
Jarvis normalizes the observation with:

    live_handle = false

Any consequential action must refresh current state through the relevant live
browser/Windows provider before execution.

## Current proof

- external HTTP boundary only;
- no Screenpipe import inside Jarvis core;
- bounded query limit;
- optional time-range query;
- normalized provenance/source;
- immutable historical observation type;
- historical results cannot become live action handles.

## Not yet claimed

- real localhost Screenpipe service round trip;
- ranking/relevance quality;
- continuous capture;
- F7 ContextAssembler consumption.
