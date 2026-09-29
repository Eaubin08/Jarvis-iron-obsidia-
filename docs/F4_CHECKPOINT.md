# F4 CHECKPOINT — structured Windows action

Date: 2026-09-29
Status: CLOSED

Implemented:
- NativeWindowsBackend contract
- Win32Driver
- UIADriver
- app.open / window.list / window.focus
- structured control interaction through UI Automation
- no visual or coordinate fallback inside F4

Verification:
Final run 36605096362 = SUCCESS
- Ubuntu 3.11 core = PASS
- Ubuntu 3.13 core = PASS
- Windows 3.11 core = PASS
- Windows 3.13 core = PASS
- real Chromium = PASS
- real Win32 = PASS
- real UI Automation = PASS

UIA proof uses a native Win32 fixture exposing Edit, Button and Static controls.
The test writes into Edit, invokes Button through UI Automation and observes
the resulting Static text without screen coordinates.

Verdict:
F4 = CLOSED

Next:
F5 voice pipeline on target Windows.
