# F6 SCREENPIPE LIVE GATE

Status: READY / LOCAL SERVICE + AUTH REQUIRED

This gate verifies the real localhost Screenpipe boundary without making
Screenpipe a Jarvis core dependency.

Requirements:

    Screenpipe service running locally

Enable:

    $env:JARVIS_REAL_SCREENPIPE_TEST = "1"

Configure endpoint:

    $env:JARVIS_SCREENPIPE_URL = "http://127.0.0.1:3030"

If Screenpipe API auth is enabled, provide the token only through an environment
variable:

    $env:JARVIS_SCREENPIPE_API_KEY = "<token>"

The integration test also accepts SCREENPIPE_API_KEY as a compatibility source.
The token is never written to the repository or logged by the adapter.

Run:

    python -m pytest -q tests/test_f6_screenpipe_integration.py -s

PASS proves:
- Jarvis can reach the real localhost Screenpipe service;
- authenticated /search works;
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
