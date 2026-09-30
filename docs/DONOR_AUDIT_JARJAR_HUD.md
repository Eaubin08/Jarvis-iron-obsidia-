# JARJAR HUD / AVATAR V0

Status: IMPLEMENTED / PHYSICAL UI GATE REQUIRED

## Donor findings

Two donor/reference projects were reviewed for the face/HUD layer:

- `Jayavisaag/JARVIS`: neural HUD, live state/telemetry, pywebview frontend,
  voice-first desktop companion patterns.
- `BhargavaKandala/JARVIS-V0.1`: V.A.U.L.T. HUD, animated core, transcript,
  state labels and background-thread voice runtime.

Neither audited repository exposes a clear reusable license at the repository
level. Their source is therefore treated as reference only; Jarjar's HUD code
is independently implemented.

## Jarjar V0 face

The Jarjar HUD provides:

- animated avatar/core;
- canonical visual states: IDLE, LISTENING, THINKING, SPEAKING, ERROR;
- text transcript;
- text input + SEND;
- VOICE ON/OFF;
- LISTEN trigger;
- background worker threads so cognition/voice cannot freeze Tk;
- injected text and voice handlers.

The HUD is presentation only. It cannot bypass JarvisCore, ActionRouter,
PermissionPolicy or the voice runtime.

## Upgrade seam

Today:

    JarjarHUD -> HUDController -> injected current runtime

Later:

    JarjarHUD -> HUDController -> Brody / Obsidia / Obsydur runtime

The UI and avatar do not need to be rewritten when cognition changes.

## Physical UI smoke test

Run:

```powershell
& 'C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m scripts.run_jarjar_hud_demo
```

Expected:

- Jarjar window opens;
- animated cyan avatar/core is visible;
- typing text and pressing Enter/SEND adds YOU + JARJAR transcript;
- VOICE ON/OFF toggles visibly;
- LISTEN runs a deterministic demo voice turn;
- window remains responsive during state changes.

This smoke test does not claim production cognition/voice wiring. That wiring
is the next step after the shell is physically verified.
