# J1 Checkpoint

## Current verdict

**J1-A PASS**
- canonical donor identified;
- exact donor SHA pinned.

**J1-B PASS STRUCTURAL**
- verified donor WebSocket text contract;
- Jarvis-owned transport implemented;
- donor internals are not imported.

**J1-C PREPARED / NOT MACHINE-VERIFIED**
- Windows bootstrap added;
- exact-SHA checkout guard added;
- isolated donor venv path added;
- health-check script added.

## Not yet claimed

J1-D/E/F require execution on the target Windows machine:
- real text round trip;
- real voice round trip;
- real bounded computer action.

GitHub-side code cannot prove microphone, speaker, Windows permissions, local
credential setup, or live desktop actuation.

## Next machine command

From a clone of this repository on `build/jarvis-v0`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_personal_jarvis.ps1 -InstallDependencies
```

Then launch the isolated donor and complete its provider/wake-word onboarding.
After it is running:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_personal_jarvis.ps1
```
