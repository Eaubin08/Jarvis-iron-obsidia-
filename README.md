# Jarvis Iron Obsidia

Personal Iron-Man-style AI assistant project.

## Current scope

Jarvis is built first as a **standalone personal assistant** that can be used independently of the Obsidia stack.

Initial goals:
- natural voice interaction and wake word;
- screen, camera and activity perception;
- personal and perceptual memory;
- computer, browser, file and terminal control;
- agents and long-running tasks;
- desktop HUD / Iron-Man-style presence;
- extensible adapters for external projects and tools.

## Boundary

**No Obsidia / Sens / Cognition runtime integration in the initial build.**

The future connection to the Obsidia stack will be a separate integration phase after the current Sens/Cognition work is stabilized.

## Development

Active implementation work starts on `build/jarvis-v0`.

External projects are treated as donor projects. Code is not copied blindly: each candidate is audited for architecture, license, dependencies, maturity and fit before being classified as:

- `TAKE`
- `ADAPT`
- `REIMPLEMENT`
- `REFERENCE`
- `REJECT`
