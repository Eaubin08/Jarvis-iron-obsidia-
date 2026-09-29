# F7 CONTEXT + MEMORY SEPARATION

Status: IMPLEMENTATION STARTED

## Scope

F7 introduces Jarvis-owned context assembly and isolated memory categories:

- WorkingMemory
- PersonalMemory
- ProjectMemory
- EpisodicMemory
- PerceptualTimeline

## Invariants

- each memory category has an independent store;
- clearing or querying one category does not mutate another;
- PerceptualTimeline remains external historical evidence;
- ContextAssembler returns a bounded ContextSnapshot;
- every included item has a provenance reference;
- no donor-specific object crosses into the snapshot;
- no memory category receives implicit writes from another category.

## Current slice

Implemented:
- MemoryItem canonical record;
- four isolated in-memory category stores;
- bounded ContextAssembler by item count and character count;
- provenance for memory and perceptual items;
- tests for T09 and T10.

Not yet claimed:
- durable storage backend;
- retention policies;
- admission policy engine;
- TextRuntime migration from legacy MemoryProvider.context();
- restart persistence W11.
