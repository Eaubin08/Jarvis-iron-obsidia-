# F6 CHECKPOINT — PERCEPTUAL TIMELINE

Status: CODE IMPLEMENTED — LIVE SERVICE HOLD

Closed in code:
- Jarvis-owned PerceptualObservation
- Jarvis-owned PerceptualTimeline contract
- ScreenpipeTimeline external localhost adapter
- bounded search
- timestamp normalization
- provenance normalization
- historical/live separation
- T08 invariant: historical Screenpipe observation cannot be used as a live UI handle

Live gate:
- tests/test_f6_screenpipe_integration.py
- JARVIS_REAL_SCREENPIPE_TEST=1
- JARVIS_SCREENPIPE_URL optional override

Hold:
- real Screenpipe localhost round trip on target machine: NOT YET CLAIMED

Next after live-service proof:
F7 — ContextAssembler + memory separation.
