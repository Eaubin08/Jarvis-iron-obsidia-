# Open Interpreter 01 donor audit — Gate 0

Upstream: `openinterpreter/01`
Role candidate: multi-device voice / hardware presence.
License observed: AGPL-3.0.
Current decision: **REFERENCE_FIRST / ADAPT_WITH_LICENSE_REVIEW**.

Useful surface:
- voice interface;
- desktop/mobile/ESP32 clients;
- code execution, web, files and third-party software control.

Risk:
- upstream explicitly describes the project as experimental and lacking basic safeguards;
- AGPL obligations make direct transplantation materially different from permissive donors.

V0 rule: no direct code import until licensing and isolation strategy are reviewed.
