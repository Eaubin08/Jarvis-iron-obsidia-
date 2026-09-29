# F7 Checkpoint — ContextAssembler + Memory Separation

Status: IMPLEMENTED

## Scope

F7 adds Jarvis-owned context and memory primitives without changing the frozen
architecture:

- `WorkingMemory` remains session-local and ephemeral.
- `PersonalMemory`, `ProjectMemory`, and `EpisodicMemory` use a Jarvis-owned
  deterministic JSONL backend.
- `PerceptualTimeline` stays separate and is queried as external observation
  evidence, not copied into durable memory.
- `ContextAssembler` builds bounded snapshots with provenance.
- `TextRuntime` can use `ContextAssembler` while preserving the existing
  `MemoryProvider` compatibility path.

## Test Closure

T09: READY/PASS under focused automated tests.

T10: READY/PASS under focused automated tests.

W11: READY/PASS as restart simulation with durable JSONL storage and ephemeral
working memory.

## Holds

No physical hardware proof is claimed by F7. Perceptual observations are still
historical context and not live UI handles.
