# F2 CHECKPOINT — fast intent and capability registry

Date: 2026-09-29
Status: CLOSED

Implemented:
- deterministic FastIntentRouter
- LocalCapabilityRegistry
- ambiguity escalates instead of guessing
- first canonical capability: system.status

Verification:
GitHub Actions run 36603706034
Head de17a3b667531acab583309ef4c4e2b06f8bb2da
4/4 PASS on Windows/Linux, Python 3.11/3.13.

Follow-up implementation:
fast intent is now connected end-to-end to ActionRouter with a Jarvis-owned
SystemBackend. Tests explicitly fail if cognition is invoked for system.status.

Next:
validate the end-to-end fast-path CI, then begin F3 BrowserBackend.
