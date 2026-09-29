# screenpipe donor audit — Gate 0

Upstream observed: `screenpipe/screenpipe` (also surfaced through dp466/screenpipe).
Role candidate: continuous perceptual memory.
Current license state observed (2026): source-available Screenpipe Commercial License; personal non-commercial source use permitted, commercial source use requires a license.
Current decision: **EXTERNAL_SERVICE_ADAPTER_CANDIDATE**.

Useful surface:
- continuous screen/audio capture;
- local searchable timeline;
- REST API / SDK;
- agent context.

Strategy:
Prefer consuming its local API behind PerceptionProvider/MemoryProvider instead of copying source into Jarvis.

Reason:
This keeps the Jarvis core independent and reduces license coupling.
