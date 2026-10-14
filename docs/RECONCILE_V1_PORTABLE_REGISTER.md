# RECONCILE V1 PORTABLE REGISTER — Jarvis-iron-obsidia-

Branch: `reconcile/jarvis-iron-obsidia-v1-portable`
Date: 2026-10-14
Status: **ORGANIZATION_RECONCILED — RUNTIME_NOT_CERTIFIED**

Organizational closure tag: `org-reconciled/jarvis-iron-obsidia-v1-portable-20261014`, placed on the commit that contains this version of the register. It certifies the Git organization only (provenance, integration, exclusions). **It is not a runtime freeze**: CI is red and physical validation has not been done.

This register is complementary to `docs/RECONCILE_V1_REGISTER.md`, which stays unchanged and remains the record of `reconcile/jarvis-iron-obsidia-v1`. It records the integration of the G2/G3 governed executors that existed only on the laptop until 2026-10-13. No source branch was modified. Nothing was deleted. Nothing was merged into `main`.

## 1. Sources and merge

| Item | Value |
|---|---|
| Parent 1 | `reconcile/jarvis-iron-obsidia-v1` @ `227e0a86724b1e05743c939ca17f4b00cafc7c79` |
| Parent 2 | `backup/portable-20261013/main` @ `a1abae1397e37a9cf2aace6b2a8d11f75994c04d` |
| Common ancestor | `ae08101296c1834448ebee4420ada1646766a35d` (tag `llama-b11193-portable`) |
| Merge commit | `b1f3eb19b86e3cbf5f8bbcc8663f8c1c69fda64d` |
| Method | `git merge --no-ff`, two parents, no squash, no rebase, built in a throwaway clone |
| Merge tree | `7b515aba1f5049b2265c7b7ffbda602dac4080ea`, identical to the tree simulated beforehand with `git merge-tree` |
| Conflicts | none; the two sides modify no file in common (12 files on parent 1, 16 files on parent 2, since the common ancestor) |

## 2. Provenance of the 12 G2/G3 commits

The 12 commits were made on the local `main` of the laptop clone, on top of `ae081012`, on 2026-10-06 and 2026-10-07. They were never pushed to `main`. They were published unchanged on 2026-10-13 as `backup/portable-20261013/main`, and are preserved here with their original SHA.

| SHA | Date | Subject |
|---|---|---|
| `d7e7bfb33d4b0f00c9b4c6c905b5409984f5f362` | 2026-10-06 | feat(uia): add verified radio selection executor |
| `9b5bcc8d3e83f78ecbc9701859eb2f7c5b5a0eed` | 2026-10-06 | feat(uia): add verified tab selection executor |
| `c25a52d0c3ff6325fdd377d22ab4878dbceaf640` | 2026-10-06 | feat(browser): add stable page and session identity |
| `0352b60b092959ef6161b64e2036fe01ea106be9` | 2026-10-06 | fix(browser): close selector count identity contract |
| `662b042e540315ae98fb4311489121dee46a31a0` | 2026-10-06 | feat(browser): add bounded link activation executor |
| `9b065399a4e5908a1dadda85df70c97d4eb01b01` | 2026-10-06 | feat(browser): add verified disclosure state executor |
| `e6dfa66099da793dbc064e37311c30f3e968712d` | 2026-10-06 | feat(browser): add verified checkbox state executor |
| `7ce054d1ac643da418d794d06d5655f4600c681d` | 2026-10-07 | feat(browser): add verified radio selection executor |
| `1f728a06c5fbcfe4202042c0534bb51c2d0c69a0` | 2026-10-07 | feat(browser): add verified option selection executor |
| `f216c86a3156ae8c75465a1b0ea3092122c6a1c5` | 2026-10-07 | feat(browser): add verified field value executor |
| `67fb5e66c437116a682b9d5e653331a8cdb36fdf` | 2026-10-07 | feat(browser): add observed get form submission executor |
| `a1abae1397e37a9cf2aace6b2a8d11f75994c04d` | 2026-10-07 | docs(browser): freeze governed browser v0 boundaries |

## 3. Functions and executors integrated

Files changed by the integration (16 files, +4687 / -49 against the common ancestor): `src/jarvis/browser.py`, `src/jarvis/integrations/playwright_driver.py`, `src/jarvis/integrations/uia_identity.py`, `src/jarvis/structured_ui.py`, `docs/G3_BROWSER_V0_FREEZE.md`, 10 new test files and `tests/test_g2_0_uia_stable_identity.py`.

**G2 — UI Automation**

- `select_radio_by_identity`, `select_tab_by_identity`, `read_selected_by_identity` (verified selection through the SelectionItem pattern).

**G3 — Browser**

- Stable page and session identity; selector count identity contract closed.
- 14 actions added to the browser surface: `browser.inspect_element`, `browser.activate_link`, `browser.inspect_disclosure`, `browser.set_disclosure`, `browser.inspect_checkbox`, `browser.set_checked`, `browser.inspect_radio`, `browser.select_radio`, `browser.inspect_select`, `browser.select_option`, `browser.inspect_field`, `browser.set_field_value`, `browser.inspect_form_submission`, `browser.submit_get_navigation`.
- The boundaries of this surface are stated in `docs/G3_BROWSER_V0_FREEZE.md`.

These actions are the ones called by the X-108 browser bridge (`scripts/jarjar_browser_bridge_v0.py` in `obsidia-x108-proofs`); before this branch they existed on no GitHub branch other than the backup.

## 4. Test results

### 4.1 Local run before publication

Command: the "Core and contract tests" command of `.github/workflows/ci.yml`, run on Windows 11, Python 3.13.3, on exported trees (no physical or live test).

| Tree | Result |
|---|---|
| `backup/portable-20261013/main` (`a1abae13`) | 634 passed, 9 skipped |
| `reconcile/jarvis-iron-obsidia-v1` (`227e0a86`) | 1 failed, 507 passed, 9 skipped |
| Merge tree `7b515aba` | 1 failed, 633 passed, 9 skipped |

The 11 G2/G3 test files (150 tests) pass on the merge tree.

### 4.2 Pre-existing HUD failure

```
FAILED tests/test_f10_hud_controller.py::test_voice_turn_returns_idle_after_completed_voice_handler
AssertionError: assert <HUDState.LISTENING: 'listening'> is <HUDState.IDLE: 'idle'>
```

This is the single failure on the merge tree. It is the same failure as on parent 1 and is already recorded as an OPEN_TECHNICAL_ITEM in `docs/RECONCILE_V1_REGISTER.md` (source commit `aab6ea5ed783d69f8aa648971c1eee6c1436280e`). It does not occur on parent 2. It is carried by parent 1, not created by this merge. No fix was applied.

### 4.3 GitHub CI

CI run `38498184076` on `db13ccf58c503ddd6d4090165d090bf7fe8763c6` (workflow "Jarvis Iron CI", push). Conclusion: failure.

| Job | Result |
|---|---|
| `test (windows-latest, 3.11)` | FAILURE — 35 failed, 598 passed, 10 skipped |
| `test (ubuntu-latest, 3.11)` | FAILURE — 35 failed, 598 passed, 10 skipped |
| `test (windows-latest, 3.13)` | FAILURE — 5 collection errors: `ModuleNotFoundError: No module named 'audioop'` |
| `test (ubuntu-latest, 3.13)` | FAILURE — 5 collection errors: `ModuleNotFoundError: No module named 'audioop'` |
| `browser-integration` | success |
| `windows-integration` | success |
| `voice-stt-integration` | success |
| `voice-tts-integration` | success |

The 35 failures on Python 3.11 are, on both OS:

- 1 × `tests/test_f10_hud_controller.py::test_voice_turn_returns_idle_after_completed_voice_handler` — the pre-existing HUD failure of section 4.2.
- 34 × `tests/test_g3_a1_page_identity_red.py` — `ModuleNotFoundError: No module named 'playwright'`. **New on this branch.** This test file comes from parent 2 (commit `c25a52d0`). Its helper `_inject_page` patches `playwright.sync_api.sync_playwright`, which requires the `playwright` package to be importable, while the `test` job installs only `.[dev]` and `playwright` belongs to the `browser` extra. The same 34 tests pass in the local run of section 4.1, where `playwright` is installed. This is a CI dependency gap revealed by the integration, not a behaviour failure observed in the executors. No fix was applied.

The Python 3.13 result is the inherited `audioop` item; the suite does not run on 3.13.

## 5. Open items

| Item | Status |
|---|---|
| HUD state after a completed voice turn | **OPEN_TECHNICAL_ITEM**, inherited from `reconcile/jarvis-iron-obsidia-v1`, not fixed |
| Python 3.13 — `audioop` removed from the standard library | **OPEN_TECHNICAL_ITEM**, inherited, not fixed |
| `tests/test_g3_a1_page_identity_red.py` needs `playwright` in the core `test` job | **OPEN_TECHNICAL_ITEM**, new on this branch: 34 tests fail in CI on Python 3.11 for a missing dependency. Supposed remedy, not applied: install the `browser` extra in the `test` job, or move the file to the browser job |
| Physical validation: G2 UIA radio and tab selection on real applications | **PENDING** |
| Physical validation: G3 browser executors on real sites | **PENDING** |
| Physical validation: Qwen text, Qwen-VL camera, Qwen-VL screen, Jarjar route E2E | **PENDING** (unchanged from the v1 register) |
| Runtime freeze tag on this branch | NOT created. The certified runtime freeze remains `jarjar-qwen-runtime-freeze-20261008` on `main` |

## 6. Work kept separate

| Item | Where | Status |
|---|---|---|
| B2 — local merge commit `f29664a9daa9853f2dc2c9be33818ba17d986e9d` on `build/jarvis-v0` | laptop clone only | NOT published, NOT integrated: `docs/V0_FINAL_CHECKPOINT.md` carries a local path not yet qualified for a public repository |
| `build/jarvis-v0`, `exp/*`, `work/*`, `fix/*` branches | GitHub | untouched; their status is the one recorded in `docs/RECONCILE_V1_REGISTER.md` |
| `main` | GitHub | untouched; nothing from this branch was merged into it |

## 7. Guarantees

- `main` is still at `64a39b84853959c4002ed93dd66af936cc04ba0d`.
- `reconcile/jarvis-iron-obsidia-v1` is still at `227e0a86724b1e05743c939ca17f4b00cafc7c79`, and tag `org-reconciled/jarvis-iron-obsidia-v1-20261013` (tag object `527b79317b1f8e4e012a26bea1f7b40a93b4184f`) still points to it.
- `backup/portable-20261013/main` is still at `a1abae1397e37a9cf2aace6b2a8d11f75994c04d`.
- No PR was opened, closed or merged. No force-push, reset, rebase or squash. No existing tag was moved.
