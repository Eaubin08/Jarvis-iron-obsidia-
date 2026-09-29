# Jarvis Iron — Organ Selection Matrix V0

Date: 2026-09-29
Status: PROVISIONAL SELECTION — NO DONOR INTEGRATION
Previous: DEEP_DONOR_AUDIT_PASS1.md

Legend:
- TAKE: reuse behind Jarvis boundary when license/API fit is verified.
- ADAPT: use donor through an adapter or selectively adapt code.
- REIMPLEMENT: preserve mechanism/behavior, implement Jarvis-owned version.
- REFERENCE: learn from it only.
- REJECT: not selected for V0.

## Matrix

| Organ | Primary candidate | Secondary/fallback | Disposition | Jarvis ownership |
|---|---|---|---|---|
| Wake word | JARVIS-6/openWakeWord path | Personal Jarvis | ADAPT/REIMPLEMENT | VoiceInterface |
| STT | JARVIS-6/faster-whisper path | Personal Jarvis providers | ADAPT | SpeechToTextProvider |
| TTS | JARVIS-6/Kokoro path | Personal Jarvis providers | ADAPT | TextToSpeechProvider |
| Barge-in/follow-up | Samuel + JARVIS-6 behavior | Personal Jarvis | REIMPLEMENT | ConversationRuntime |
| Speaker verification | JARVIS-6 mechanism | none for V0 | REIMPLEMENT/ADAPT | IdentitySignalProvider |
| Fast commands | Jarvis-owned | JARVIS-6 routing ideas | REIMPLEMENT | FastIntentRouter |
| Perceptual capture | screenpipe | direct on-demand screenshot | EXTERNAL ADAPTER | PerceptualTimeline |
| UI history/search | screenpipe REST/MCP | none | EXTERNAL ADAPTER | PerceptualTimeline |
| Working context | Jarvis-owned | Leon concepts | REIMPLEMENT | ContextAssembler |
| Personal memory | Jarvis-owned layered model | Leon + Agent Zero concepts | REIMPLEMENT | PersonalMemory |
| Project memory | Jarvis-owned | Agent Zero project model | REIMPLEMENT | ProjectMemory |
| Windows structured action | UFO2 concepts/MCP surfaces | direct pywin32/UIA | ADAPT/REIMPLEMENT | NativeWindowsBackend |
| Browser action | Playwright/DOM-first | UI-TARS browser operator | TAKE/ADAPT | BrowserBackend |
| Visual GUI fallback | UI-TARS SDK/operator | OmniParser-style detection | ADAPTER | VisualOperatorBackend |
| Raw mouse/keyboard | Jarvis-owned thin backend | donor utilities | REIMPLEMENT | RawInputBackend |
| Long tasks/projects | Jarvis-owned runtime | Agent Zero adapter | REIMPLEMENT/ADAPT | TaskRuntime |
| Skills | Jarvis-owned skill format | Agent Zero + Leon concepts | REIMPLEMENT | SkillRegistry |
| HUD | Jarvis-owned event client | devyuv/JARVIS, JARVIS-6, MAL19, Jayavisaag | REIMPLEMENT/SELECTIVE TAKE | HUDClient |
| Camera | Jarvis-owned provider | Jayavisaag/davidakpele ideas | REIMPLEMENT | CameraProvider |
| Gestures | MediaPipe provider | devyuv behavior | ADAPT/REIMPLEMENT | GestureProvider |
| Mobile | Jarvis protocol/client | 01 concepts | REIMPLEMENT | MobileClient |
| Devices/home | Jarvis DeviceProvider | Jayavisaag + later HA audit | REIMPLEMENT | DeviceProvider |

## Selected action hierarchy

ActionRequest
  -> CapabilityRegistry
  -> PermissionPolicy
  -> ActionRouter
       1. Native/API backend
       2. Browser DOM/Playwright backend
       3. Windows accessibility/UIA/Win32/COM backend
       4. Visual VLM operator
       5. Raw input fallback
  -> ActionResult
  -> EventBus

Rationale:
visual mouse/keyboard control is not the default when a structured, native,
browser or accessibility surface exists.

## Selected perception hierarchy

Live cheap signals:
- foreground app/window
- accessibility tree / structured UI
- event-driven screenshots
- microphone/system-audio transcript
- optional camera signal

PerceptualTimeline:
- external screenpipe adapter initially
- historical/searchable evidence only
- never treated as live action handles

ContextAssembler:
- pulls only relevant bounded slices from timeline
- combines current state + working memory + personal/project memory
- expensive cognition receives selected context, not the full timeline

## Selected conversational path

Audio
 -> WakeWord
 -> SpeakerSignal (optional/bounded)
 -> STT
 -> FastIntentRouter
      -> exact local capability when confident
      -> CognitionProvider otherwise
 -> Task/Action path
 -> TTS
 -> HUD/Event stream

Barge-in interrupts output without destroying the active session.
A short follow-up window avoids requiring the wake word on every turn.

## Memory separation — frozen candidate rule

WorkingMemory:
ephemeral current session/task state.

PersonalMemory:
durable user preferences/facts/relationships explicitly admitted by policy.

ProjectMemory:
project-scoped instructions, files, decisions and task history.

EpisodicMemory:
selected Jarvis interactions/events.

PerceptualTimeline:
high-volume screen/audio/activity evidence, primarily externalized to Screenpipe.

No donor database is allowed to silently collapse these five categories.

## Donor decisions tightened

### JARVIS-6
Disposition: ADAPT/REIMPLEMENT.
Selected for study of Windows-local voice pipeline and bounded orchestration.
Do not inherit Gemini as mandatory cognition.

### Samuel
Disposition: REIMPLEMENT interaction behavior.
Selected for ambient/realtime conversational behavior, not macOS implementation.

### Personal Jarvis
Disposition: ADAPT SELECTIVELY / TEST FIXTURE.
Installed donor remains useful for protocol and feature comparison.
It is not the base.

### Screenpipe
Disposition: EXTERNAL SERVICE ADAPTER.
Use localhost REST/MCP. Do not make its historical UI element IDs live action
handles. Current source-license constraints make service isolation preferable.

### UFO2
Disposition: ADAPT/REIMPLEMENT Windows action mechanisms.
Study UIA/Win32/WinCOM, MCP command discovery, UI tree/screenshot collection,
and application-specific native executors.

### UI-TARS Desktop/SDK
Disposition: VISUAL FALLBACK ADAPTER.
Apache-2.0. Keep behind VisualOperatorBackend so models/operators are replaceable.

### Leon
Disposition: REIMPLEMENT memory/context/skill concepts.
Developer Preview means no hard runtime dependency for V0.

### Agent Zero
Disposition: REIMPLEMENT project/task concepts; optional agent adapter later.
MIT. Useful project isolation, skills and subagent patterns.

### Open Interpreter 01
Disposition: REFERENCE for device/realtime voice protocol.
AGPL and experimental safeguards make it unattractive as a V0 embedded dependency.

### HUD-focused Jarvis projects
Disposition: UI/interaction donor pool.
No HUD donor owns core/session/action state.

## Explicit rejects for architecture ownership

REJECT:
- making Personal Jarvis the root application;
- making Screenpipe the single memory system;
- making UI-TARS the default action engine;
- making Agent Zero the Jarvis core;
- making any HUD repository own cognition;
- mandatory Gemini/OpenAI/Anthropic provider coupling;
- importing unrelated donor histories into the master Git history.

## Remaining blockers before architecture freeze

1. Exact SHA/license table for all Tier-A donors.
2. Deep module audit for HUD donor pool.
3. Browser donor comparison: Playwright implementations vs visual browser operator.
4. Voice latency/runtime comparison on Windows.
5. Define Jarvis-owned event/schema contracts for every selected organ.
6. Decide which donors are submodules, external installed services, packages, or reference-only.
7. Define V0 integration test matrix.

Until those are closed: J1-D remains paused.
