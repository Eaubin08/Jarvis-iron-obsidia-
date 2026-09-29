# JARVIS IRON — ARCHITECTURE FREEZE V0

Date: 2026-09-29
Status: FROZEN FOR IMPLEMENTATION
Scope: standalone Jarvis Iron. No Obsidia/Sens/Cognition integration.

## 0. Purpose

Build a Windows-first personal Jarvis that is useful early:
voice-first, context-aware, able to perceive recent computer activity,
perform bounded computer/browser actions, sustain tasks, and expose an
Iron-Man-style HUD.

External projects are organ donors, never architectural owners.

## 1. Canonical ownership

Jarvis Iron owns:
SessionRuntime
EventBus
ConversationRuntime
FastIntentRouter
ContextAssembler
Memory interfaces
TaskRuntime
CapabilityRegistry
PermissionPolicy
ActionRouter
provider contracts
HUD/client protocol
canonical state and receipts

## 2. Canonical organ graph

VoiceInterface
  -> ConversationRuntime
      -> FastIntentRouter
      -> ContextAssembler
      -> CognitionProvider
      -> TaskRuntime
      -> ActionRouter
  -> EventBus
      -> TTS
      -> HUD/Desktop
      -> future Mobile/Devices

ContextAssembler reads independently:
WorkingMemory
PersonalMemory
ProjectMemory
EpisodicMemory
PerceptualTimeline

ActionRouter order:
1 Native/API
2 Browser DOM/Playwright
3 Windows UIA/Win32/COM
4 Visual operator
5 Raw input

## 3. Donor dispositions

Personal Jarvis:
external runtime/test fixture/selective donor; Apache-2.0 at audited 2.x.
Not root.

Screenpipe:
external localhost perceptual-timeline service.
Do not copy source into V0 core.

UFO2:
Windows action mechanism donor.
Adapt/reimplement UIA/Win32/COM/MCP concepts behind Jarvis contracts.

UI-TARS:
visual fallback adapter candidate.
Never default action path.

Samuel:
MIT behavioral donor.
Reimplement Windows equivalent of realtime voice, barge-in, ambient audio
recall, context relevance gating, and explicit control modes.

JARVIS-6:
REFERENCE ONLY until source license is established.
No LICENSE file found at audited SHA.
Reimplement useful voice/orchestration ideas without copying source.

Leon:
memory/context/skills concept donor; no hard runtime dependency.

Agent Zero:
task/project/subagent concept donor; optional later AgentProvider.

01:
AGPL/reference only for realtime/device protocol.

HUD donors:
devyuv/JARVIS, JARVIS-OS-V.2, Jayavisaag/JARVIS, davidakpele/jarvis.
HUD remains an event consumer.

## 4. Browser decision

V0 PRIMARY:
Playwright/DOM-first BrowserBackend with persistent user-approved browser
profile/session.

V0 FALLBACK:
VisualOperatorBackend (UI-TARS-compatible).

Rules:
- DOM/accessibility selectors before coordinates.
- refresh page state before consequential action.
- no CAPTCHA/MFA/access-control bypass.
- credential material is not emitted into model context unless explicitly
  required by a bounded provider contract.

## 5. Voice decision

V0 target:
local wake/VAD/STT/TTS where viable on target Windows machine.

Candidate mechanisms:
openWakeWord-style wake provider
faster-whisper-style STT provider
Kokoro-style TTS provider
realtime/cloud voice remains replaceable option

Required:
barge-in
follow-up window
cancellable speech
context-relevance gating
explicit listening/control modes

No bundled model asset is approved merely because its repository code is
permissively licensed.

## 6. Perception decision

Continuous cheap observation is separated from expensive interpretation.

Screenpipe may retain/search timeline.
Current live state is refreshed before action.
ContextAssembler selects bounded relevant observations.
Screen/camera/audio capture has visible enable/disable state.

## 7. Memory decision

Five categories remain distinct:
Working
Personal
Project
Episodic
PerceptualTimeline

No single donor store may collapse them.

## 8. Safety/desktop control

This is practical desktop safety, not Obsidia governance.

PermissionPolicy classifies actions.
Read-only/local low-impact actions may auto-run.
Sensitive/destructive/external-impact actions require explicit approval.
Cognition never receives unrestricted direct shell authority.

## 9. V0 implementation sequence

F0 — expand Jarvis contracts/events.
F1 — local text CLI + fake providers.
F2 — FastIntentRouter + CapabilityRegistry.
F3 — BrowserBackend / Playwright.
F4 — NativeWindows + UIA/Win32 path.
F5 — Voice pipeline on target Windows.
F6 — Screenpipe PerceptualTimeline adapter.
F7 — ContextAssembler + memory separation.
F8 — VisualOperator fallback.
F9 — TaskRuntime.
F10 — HUD event client.
F11 — camera/gesture.
F12 — mobile/device bridge.

Daily-use target begins at F5/F6, not F12.

## 10. Freeze invariants

- no Obsidia runtime dependency;
- no donor owns JarvisCore;
- no donor-specific object crosses core boundary;
- no mandatory LLM vendor;
- no visual-first action when structured action is available;
- historical perception is not a live action handle;
- UI/HUD cannot bypass ActionRouter;
- every external donor can be replaced by a fake adapter in contract tests;
- source/model/asset licenses are tracked separately.

Changes to these invariants require an explicit architecture revision.
