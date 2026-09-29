# Donor Project Policy

Every external project is audited before code enters Jarvis.

## Verdicts

- **TAKE** — reuse a bounded component when license and architecture allow it.
- **ADAPT** — reuse behind a Jarvis-owned adapter.
- **REIMPLEMENT** — reproduce the required behavior without copying implementation.
- **REFERENCE** — architectural or UX inspiration only.
- **REJECT** — not suitable.

## Required checks

1. exact upstream repository;
2. exact commit/tag to pin;
3. license and attribution obligations;
4. runtime/dependency footprint;
5. security and permission model;
6. Windows compatibility;
7. offline/cloud behavior;
8. interface with Jarvis provider contracts;
9. tests needed before activation.

No donor project may directly own Jarvis core, memory schema, event model or public contracts.
