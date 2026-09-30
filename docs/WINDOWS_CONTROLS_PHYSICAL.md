# Windows controls physical gate

Run after the structural tests are green:

```powershell
python -m scripts.smoke_windows_controls
```

This smoke is deliberately non-destructive:

- reads real Wi-Fi state;
- reads real Bluetooth device state;
- proves radio toggles resolve to `SENSITIVE -> ASK` without executing them;
- opens an empty Notepad instance;
- maximizes and restores only that instance;
- moves it to monitor 2 when available;
- closes it.

Expected final marker:

```text
WINDOWS_CONTROLS_PHYSICAL: PASS
```
