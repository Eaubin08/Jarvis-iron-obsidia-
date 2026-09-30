# Temporary cost-aware cognition routing V0

This router exists only while the canonical OpenJarvis/Obsidia router is not
yet ready to consume Jarjar's full live context.

Policy:

1. deterministic presence / fast intent: zero-cost local path;
2. project/Obsidia/corpus questions: Brody first;
3. general free-form questions: local Qwen first;
4. environment questions: local Qwen + structured live context first;
5. if the preferred provider is unavailable, fall back to the other provider.

Qwen is text-only in this V0. Camera metadata can prove that a fresh frame
exists and give dimensions/device identity, but Qwen2.5-Instruct does not see
the pixels. A later vision provider must be used for actual image semantics.

No cognition provider can execute actions. PC actions stay behind FastIntent,
ActionRouter and PermissionPolicy.

This router is temporary and should be deleted/replaced when the canonical
OpenJarvis/Obsidia routing seam can make the same cost/capability decision.
