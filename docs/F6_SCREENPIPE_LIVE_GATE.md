# F6 SCREENPIPE LIVE GATE

Status: READY / LOCAL SERVICE REQUIRED

This gate verifies the real localhost Screenpipe boundary without making
Screenpipe a Jarvis core dependency.

Requirements:

    Screenpipe service running locally

Enable:

    $env:JARVIS_REAL_SCREENPIPE_TEST = "1"

Optional overrides:

    $env:JARVIS_SCREENPIPE_URL = "http://127.0.0.1:3030"
    $env:JARVIS_SCREENPIPE_QUERY = ""

Run:

    python -m pytest -q tests/test_f6_screenpipe_integration.py -s

PASS proves:
- Jarvis can reach the real localhost Screenpipe service;
- the response can be normalized into Jarvis PerceptualObservation records;
- returned observations remain historical evidence only;
- live_handle is always false.

PASS does not prove:
- relevance/ranking quality;
- continuous capture quality;
- current-screen freshness;
- suitability of any historical coordinate/element metadata for action.

Current live state must still be refreshed through BrowserBackend or
NativeWindows before consequential execution.
