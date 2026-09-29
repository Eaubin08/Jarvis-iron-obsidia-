# V0 Final Checkpoint

Status: READY WITH HOLDS

Branch: `build/jarvis-v0`

## Regression Evidence

Latest full available regression:

`python -m pytest -p no:cacheprovider --basetemp <codex-writable-temp>`

Result:

- 93 passed
- 5 skipped
- 5 failed

The five failures are environment/physical integration gates, not regressions
from F7-F12:

- `tests/test_f4_uia_integration.py`: `win32api` missing for fixture.
- `tests/test_f4_win32_integration.py`: `win32con` / `win32gui` missing.
- `tests/test_f5_stt_integration.py`: `faster_whisper` missing.
- `tests/test_f5_tts_integration.py`: `kokoro` missing.

## Contract Matrix

| TEST | STATUS | EVIDENCE | HOLD REASON |
| --- | --- | --- | --- |
| T01 Jarvis boots with fake providers only | PASS | `tests/test_standalone_boundary.py`, `tests/test_f1_text_runtime.py` | |
| T02 No donor import exists in Jarvis core | PASS | `tests/test_standalone_boundary.py` | |
| T03 Each donor adapter maps into Jarvis-owned contracts | PASS | F3-F6 adapter tests, F8 visual seam tests | |
| T04 Provider failure returns explicit typed failure | PASS | `tests/test_f1_text_runtime.py`, voice/provider tests | |
| T05 Cancelling TTS permits barge-in | PASS | `tests/test_f5_voice_runtime.py` | |
| T06 Fast deterministic intent bypasses cognition | PASS | `tests/test_f2_runtime_bypass.py` | |
| T07 Ambiguous intent escalates to cognition | PASS | `tests/test_f2_fast_intent.py`, `tests/test_f2_runtime_bypass.py` | |
| T08 Historical Screenpipe observation cannot be used as a live UI handle | PASS | `tests/test_f6_screenpipe_timeline.py`, `tests/test_f8_visual_operator.py` | |
| T09 ContextAssembler returns bounded context with provenance | PASS | `tests/test_f7_context_memory.py` | |
| T10 Memory categories remain isolated | PASS | `tests/test_f7_context_memory.py` | |
| T11 Cognition cannot directly execute an OS action | PASS | `tests/test_f2_runtime_bypass.py`, action routing contracts | |
| T12 ActionRouter prefers structured/native backend over visual fallback | PASS | `tests/test_f8_visual_operator.py`, `tests/test_f0_contracts.py` | |
| T13 Permission denial prevents backend execution | PASS | `tests/test_f0_contracts.py` | |
| T14 ActionResult records backend and evidence | PASS | `tests/test_f8_visual_operator.py`, F3/F4 backend tests | |
| T15 Long task can cancel/resume without donor-owned canonical state | PASS | `tests/test_f9_task_runtime.py` | |
| T16 HUD disconnect does not stop core | PASS | `tests/test_f10_hud_client.py` | |
| T17 Donor service unavailable does not corrupt session state | PASS | provider failure tests and TaskRuntime unavailable-provider test | |
| T18 Provider swap requires no JarvisCore change | PASS | fake providers/adapters across F1-F12 tests | |

## Windows / Machine Matrix

| TEST | STATUS | EVIDENCE | HOLD REASON |
| --- | --- | --- | --- |
| W01 wake word -> STT latency | HOLD | Wake/STT contract tests exist | Physical wake/STT latency not executed on target hardware. |
| W02 barge-in during TTS | READY | Voice runtime cancellation tests | Physical TTS playback/barge-in not executed. |
| W03 follow-up without repeated wake word | READY | Voice conversation state tests | Physical voice loop not executed. |
| W04 exact command opens known application through structured backend | HOLD | `tests/test_f4_windows_backend.py` unit path PASS | Real Win32 integration blocked by missing `pywin32`. |
| W05 browser action uses DOM/Playwright before visual operator | READY | F3 browser tests and F8 routing tests | Live browser profile/action not executed here. |
| W06 UIA action targets correct window/control | HOLD | Unit seam exists | Real UIA fixture blocked by missing `win32api`/Windows integration dependency. |
| W07 visual fallback succeeds where UIA/DOM unavailable | READY | F8 fake visual fallback tests | Physical visual operator provider not integrated/executed. |
| W08 multi-monitor coordinate correctness | NOT YET CLAIMED | None | No physical multi-monitor visual test executed. |
| W09 Screenpipe query returns relevant recent context | READY | F6 timeline normalization/integration gate | Live localhost Screenpipe service not executed in final run. |
| W10 screen context is refreshed before action | PASS | F8 visual state refresh tests | |
| W11 restart preserves durable memory but not ephemeral working state | PASS | `tests/test_f7_context_memory.py` | |
| W12 microphone/camera permissions fail closed and visibly | READY | F5 microphone tests and F11 camera fail-closed tests | Physical microphone/camera permissions not executed. |

## Daily-Use Acceptance Slice

| STEP | STATUS | EVIDENCE | HOLD REASON |
| --- | --- | --- | --- |
| wake word | READY | F5 wake input/provider tests | Physical wake word not executed. |
| speech input | READY | F5 STT adapter/unit tests | Real `faster_whisper` missing in final environment. |
| bounded context assembly | PASS | F7 ContextAssembler tests | |
| cognition or deterministic routing | PASS | F1/F2 runtime tests | |
| spoken reply | READY | F5 TTS/runtime tests | Real `kokoro` missing in final environment. |
| interruption/barge-in | READY | F5 voice cancellation tests | Physical audio not executed. |
| deterministic local action | PASS | F2/F0 local action routing tests | |
| browser/native action through structured backend | READY | F3/F4 structured backend unit tests | Real browser/Win32 integration not fully executed in final environment. |
| recent Screenpipe context query | READY | F6 Screenpipe query tests | Live Screenpipe localhost not executed in final run. |
| bounded long-running task | PASS | F9 TaskRuntime tests | |

Pass condition status:

READY WITH HOLDS. The available automated contract layer shows that operations
cross Jarvis-owned contracts and no donor owns canonical session/task/action
state. Physical voice, Windows UIA/Win32, real STT/TTS model, visual-operator,
multi-monitor, and live Screenpipe proofs remain explicitly held unless run on a
compatible machine with the optional dependencies/services installed.
