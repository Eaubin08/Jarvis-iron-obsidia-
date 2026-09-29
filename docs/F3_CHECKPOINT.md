# F3 CHECKPOINT — structured browser

Date: 2026-09-29
Status: CONTRACT PASS / REAL BROWSER TEST PENDING

Implemented:
- Jarvis-owned BrowserBackend
- injectable BrowserDriver protocol
- optional PlaywrightDriver isolated under integrations/
- browser.navigate
- browser.read
- browser.click
- browser.fill
- no coordinate-based control in structured browser backend

Contract verification:
GitHub Actions run 36604048683
Head 81c49c27f0b3bf854684a254d8441e5bcfd301aa
4/4 PASS on Windows/Linux, Python 3.11/3.13.

Real-browser gate:
A dedicated Windows CI job installs the optional browser dependency and
Chromium, then runs tests/test_f3_playwright_integration.py against a local
HTML fixture. F3 is not CLOSED until that job passes.
