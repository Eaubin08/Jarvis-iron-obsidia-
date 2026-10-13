# RECONCILE V1 REGISTER — Jarvis-iron-obsidia-

Branch: `reconcile/jarvis-iron-obsidia-v1`
Date: 2026-10-13
Status: **RECONCILED — CI NOT GREEN — NO FREEZE TAG — PHYSICAL VALIDATION PENDING**

This register records what the reconciliation branch contains, where each element comes from, what was left out and why, and the test results. No source branch was modified. Nothing was deleted. Nothing was merged into `main`.

## 1. Base

| Item | Value |
|---|---|
| Base branch | `main` |
| Base SHA | `64a39b84853959c4002ed93dd66af936cc04ba0d` |
| Freeze carried by the base | tag `jarjar-qwen-runtime-freeze-20261008` (tag object `359513a2161e2a1b9079e0776f18fae70af5230b`) |
| Why this base | 10 of the 12 other branches are ancestors of it; the two remaining lineages fork from it |

## 2. Integrated

| # | Source | Source SHA | Method | Resulting commit | Content |
|---|---|---|---|---|---|
| 1 | `fix/qwen-live-main-20261007` | `8fad2f434e458f8f3aa5fb7b49240c253e7d843d` | merge commit (no squash, no rebase) | `42780c29c4cbad3900e339c38987c36eeeac07a0` | 9 commits, fork point `538b36b99976e4450a730766a686f27a431f0b99` |

Original commits preserved in the history of this branch:

| SHA | Subject | File |
|---|---|---|
| `05564415daa4e607b514916d6a7f6f52fc4463eb` | Discover llama-server model id and expose Qwen HTTP failures | `src/jarvis/integrations/local_qwen_cognition.py` |
| `27003d4ff88db04e869c37eb62d80c3296373a2d` | Surface Qwen provider errors in Jarjar routing | `src/jarvis/cognition_bridge.py` |
| `6cbde4b28a2ac04843546847e94c69c081c5fd0c` | Bound local Qwen generation and allow CPU inference latency | `src/jarvis/integrations/local_qwen_cognition.py` |
| `7478f89981f222d8a869e53dd01dc7390c1cf43a` | Keep screen vision alive when a camera slot fails | `src/jarvis/camera_rig.py` |
| `fbed88c5bbc44ba094beff719f7f9e8fb18fdb17` | Expose Jarjar vision provider failures | `src/jarvis/cognition_bridge.py` |
| `6575bf325a482b1056b7c962ffe018003e2fea72` | Bound live utterances and raise default speech noise floor | `src/jarvis/live_runtime.py` |
| `aab6ea5ed783d69f8aa648971c1eee6c1436280e` | Preserve thinking and speaking HUD states during concurrent voice listening | `src/jarvis/hud_controller.py` |
| `3715985b82fb107a91d1c11d28902852303ec374` | Discover active Qwen-VL model from llama-server | `src/jarvis/integrations/local_vision_cognition.py` |
| `8fad2f434e458f8f3aa5fb7b49240c253e7d843d` | Probe a wider default set of local camera indices | `src/jarvis/live_runtime.py` |

Tree check after the merge (`42780c29`): identical to `main` except 6 files, all 6 byte-identical to the source branch:
`src/jarvis/camera_rig.py`, `src/jarvis/cognition_bridge.py`, `src/jarvis/hud_controller.py`, `src/jarvis/integrations/local_qwen_cognition.py`, `src/jarvis/integrations/local_vision_cognition.py`, `src/jarvis/live_runtime.py`.

## 3. Reconciliation-only commits (exist in no source branch)

| SHA | Purpose |
|---|---|
| `b9b56d2b663bb2916e2f97a9434618cae4275b5f` | `.github/workflows/ci.yml`: push trigger extended to `reconcile/**`; `test` job installs `pillow>=10` |
| `e553999a58c192323960cab12257657f3b635cb3` | adds this register |
| (this commit) | register updated with the Python 3.13 finding |

## 4. Already contained in the base (nothing to integrate)

| Branch | SHA | Evidence |
|---|---|---|
| `build/jarvis-v0` | `cd17269b40131dbcf710d6da35e1e732b3bcf06f` | ancestor of `main` |
| `exp/bounded-runtime-v0` | `de95095ca0e6740af78cfae2aad406132c42cb37` | ancestor of `main` |
| `work/f5-generic-wake` | `de95095ca0e6740af78cfae2aad406132c42cb37` | same SHA as above |
| `exp/final-surface-capability-priority-v0` | `3fb7a52ee6905fca7deb65b363986de2e809b562` | ancestor of `main` |
| `work/jarjar-g1-governed-move` | `ae3839a3aa415b0ed342ce4b939d479b8ac3b720` | ancestor of `main` |
| `work/jarjar-g2-governed-create-dir` | `319a5d9aac15abed09c0d47b0fd5f702d771d328` | ancestor of `main` |
| `work/jarjar-g3-physical-write-patch` | `3af1b64b3ece68887dfa3c2a433fa0cb6940029d` | ancestor of `main` |
| `work/jarjar-g4-governed-rollback-move` | `0d9a7ba31a0e255302f89a4f30ba4ba5f889a4c9` | ancestor of `main` |
| `work/jarjar-g5-apply-patch-rollback` | `9bdf15302b43d4d18f52afb2d0c2b889ec175ecf` | ancestor of `main` |
| `fix/windows-g3-line-endings-20261008` | `2b0a17ce45b19bca8633f54293064e6981d926c7` | PR #1 squash-merged as `64a39b84`; its 2 files are byte-identical in `main`. The branch remains the only holder of the 3 original commits |

## 5. Excluded, kept as is

| Branch | SHA | Reason |
|---|---|---|
| `exp/semantic-focus-query-roles-v0` | `ccb802a26f891b68656d1367476988d43dd892eb` | Duplicate. Its 2 own commits (`9816a91fd02a5e74cfbfc33bb639f908d93837de`, `ccb802a26f891b68656d1367476988d43dd892eb`) are line-for-line identical patches to `05564415` and `27003d4f`, applied on an older base (`51737b28d4ca5c72f29df9d741f99f6a85892ee7`). Their content is covered by integration #1 |

## 6. Tests

CI run `38348917752` on `b9b56d2b663bb2916e2f97a9434618cae4275b5f` (workflow "Jarvis Iron CI", push). Run `38349270872` on the register commit `e553999a58c192323960cab12257657f3b635cb3` gives the same results:

| Job | Result |
|---|---|
| `test (windows-latest, 3.11)` | FAILURE — 1 failed, 506 passed, 10 skipped |
| `test (windows-latest, 3.13)` | FAILURE — collection errors: `ModuleNotFoundError: No module named 'audioop'` |
| `test (ubuntu-latest, 3.11)` | FAILURE — 1 failed, 506 passed, 10 skipped |
| `test (ubuntu-latest, 3.13)` | FAILURE — collection errors: `ModuleNotFoundError: No module named 'audioop'` |
| `browser-integration` | success |
| `windows-integration` | success |
| `voice-stt-integration` | success |
| `voice-tts-integration` | success |

The Pillow collection error that hid the suite on `main` is resolved on this branch. Two distinct problems were hidden behind it.

**A. Python 3.13 only.** The `audioop` standard-library module was removed in Python 3.13; `tests/test_f5_microphone.py`, `tests/test_f5_microphone_integration.py` and other F5 tests fail at collection, so the suite does not run on 3.13. None of the 9 integrated commits touches microphone code: this problem is carried by the base (`main`), not by the integration. No fix was applied.

**B. Python 3.11, both OS.** The suite runs; one test fails:

```
FAILED tests/test_f10_hud_controller.py::test_voice_turn_returns_idle_after_completed_voice_handler
AssertionError: assert <HUDState.LISTENING: 'listening'> is <HUDState.IDLE: 'idle'>
```

Cause, established by reading the code (not by a run on `main`): commit `aab6ea5ed783d69f8aa648971c1eee6c1436280e`, which comes from the source branch, removes the final `set_state(IDLE / LISTENING)` after a completed voice handler in `HUDController._run_voice_handler`. The test file is unchanged and identical on `main`, on the source branch and here (blob `fe587a68bb9d7d1cd8812b0f190f84fb9e0e74d6`). The failure is therefore carried by the source branch itself, not created by the merge.

Not decided here: whether `aab6ea5e` is an intended behaviour change whose test was not updated, or a regression. No fix was applied.

## 7. Open items

| Item | Status |
|---|---|
| `test_voice_turn_returns_idle_after_completed_voice_handler` | FAILING on this branch (from source commit `aab6ea5e`); decision required |
| Python 3.13 support (`audioop` removed) | suite cannot be collected on 3.13; inherited from `main`; decision required |
| Freeze tag on this branch | NOT created (CI not verified) |
| Physical validation on FIXE (Qwen text, Qwen-VL camera, Qwen-VL screen, Jarjar route E2E) | PENDING — this branch is not the state validated by `jarjar-qwen-runtime-freeze-20261008` |
| CI on `main` | still red (Pillow missing from `.[dev]`); `main` untouched by design |
| Obsidia port provenance | `docs/OBSIDIA_OPENJARVIS_PORT_AUDIT_2026-09-30.md` names the source repository and per-file blob SHA; no X-108 commit SHA is pinned |

## 8. Guarantees

- `main` is still at `64a39b84853959c4002ed93dd66af936cc04ba0d`.
- The 13 pre-existing branches and 2 tags are at the same SHA as before the operation.
- No PR was opened, closed or merged. No force-push, rebase or squash.
