# F6 CHECKPOINT — PERCEPTUAL TIMELINE

Status: CLOSED — CODE / CI / LIVE LOCALHOST PASS

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

Verified live proof:
- target machine: Windows
- Screenpipe localhost: http://127.0.0.1:3030
- authenticated /search boundary: PASS
- pytest: tests/test_f6_screenpipe_integration.py
- result: 1 passed in 0.30s

CI:
- authenticated Screenpipe adapter commit: 1401934aba82db81b0527a4e87656218135a6f59
- GitHub Actions run: 36620875366
- conclusion: SUCCESS

Hold:
- none for the F6 integration boundary

Next after live-service proof:
F7 — ContextAssembler + memory separation.
