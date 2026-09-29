# Jarvis Iron — Deep Donor Audit Pass 1

Date: 2026-09-29
Status: RESEARCH ONLY
Rule: no donor is the base. Decisions below are per organ.

## 1. Voice presence

### JARVIS-6 — psycoks/Jarvis
Useful mechanisms:
- core/audio_in.py: microphone + clap detector
- core/wakeword.py: openWakeWord
- core/stt.py: faster-whisper
- core/tts.py: Kokoro
- core/speaker_id.py: owner voice verification
- core/orchestrator.py: bounded multi-hop + safety
- follow-up window and barge-in

Disposition: ADAPT / REIMPLEMENT
Why: Windows-first and close to the target interaction model. Keep provider-neutral
contracts; do not inherit Gemini as an architectural dependency.

### Samuel — sambuild04/screen-voice-agent
Useful mechanisms:
- sub-500ms voice interaction claim
- wake-word conversational presence
- screen + system-audio context
- recent-audio recall
- self-written/self-repaired tools

Disposition: REIMPLEMENT FOR WINDOWS
Why: interaction model is valuable, implementation is macOS-first.

### Personal Jarvis
Useful mechanisms:
- configurable self-hosted voice desktop shell
- wake word, STT/TTS, dictation, computer use
- public WebSocket/event boundary already audited
- MCP / coding-agent integrations

Disposition: ADAPT SELECTIVELY
Why: good donor/runtime fixture, not the product base.
License at current 2.x: Apache-2.0.

## 2. Fast path / cognition path

### The-AlphaWolf/JARVIS
Useful mechanism:
mic -> wake -> STT -> route
- deterministic/regex fast path for trivial commands
- local LLM slow path for open-ended/tool reasoning
- follow-up window

Disposition: REIMPLEMENT
Why: Jarvis should not invoke expensive cognition for deterministic local commands.

Proposed Jarvis-owned contract:
Utterance
 -> FastIntentRouter
      -> deterministic capability (when exact/confident)
      -> CognitionProvider otherwise

## 3. Perceptual timeline

### screenpipe
Useful mechanisms:
- continuous screen + audio capture
- accessibility tree first, OCR fallback
- local transcription
- app/window/activity history
- local REST API / SDK
- searchable temporal history

Disposition: EXTERNAL SERVICE ADAPTER initially; REIMPLEMENT selected concepts later
License: current source is Screenpipe Commercial License.
Important: personal/non-commercial source use is permitted; commercial source use
requires a paid commercial license.

Architectural decision:
PerceptualTimeline != PersonalMemory != WorkingContext.

## 4. Windows action substrate

### Microsoft UFO2
Useful mechanisms:
- Windows UI Automation
- Win32
- WinCOM
- hybrid GUI + native API execution
- visual control detection as complement

Disposition: ADAPT / REIMPLEMENT MECHANISMS
License: MIT.

Preferred action ladder:
1. explicit native/API capability
2. browser DOM/Playwright
3. Windows UIA/Win32/COM
4. visual GUI operator
5. raw mouse/keyboard only as last fallback

## 5. Visual computer use

### ByteDance UI-TARS Desktop
Useful mechanisms:
- screenshot/VLM grounding
- precise mouse/keyboard control
- local and remote computer operators
- browser operator
- cross-platform operator abstraction

Disposition: ADAPTER / SDK EVALUATION
License: Apache-2.0.

Role:
visual fallback, not first-choice Windows control.

## 6. Personal/context memory

### Leon 2.0
Useful mechanisms:
- explicit tool execution
- progressive grounding
- inspectable traces
- Skills -> Actions -> Tools -> Functions
- current architecture exposes context/memory as first-class runtime layers

Disposition: REIMPLEMENT CONCEPTS / SELECTIVE ADAPT
Caution: 2.0 is Developer Preview; repository is current source of truth.

### Agent Zero
Useful mechanisms:
- project-scoped files/instructions/secrets/memory/repos/model presets
- skills loaded on demand
- subordinate agents
- host-machine bridge
- inspectable prompts/tools/plugins
- memory plugin with scoped stores and consolidation

Disposition: REIMPLEMENT PROJECT/TASK MODEL; OPTIONAL EXTERNAL AGENT ADAPTER
License: MIT.

Important:
do not copy Agent Zero's single vector-memory idea as the whole Jarvis memory model.

## 7. Iron-Man embodiment / HUD

### devyuv/JARVIS
Useful mechanisms:
- React + Three.js HUD
- ArcReactor 3D core
- live waveform
- HUD panels
- transcript
- WebSocket event updates
- MediaPipe hand gesture tracker
- gesture deltas decoupled from voice/LLM tasks

Disposition: ADAPT UI IDEAS / POSSIBLY TAKE ISOLATED MIT-COMPATIBLE CODE AFTER LICENSE CHECK
Need exact license verification before code reuse.

### JARVIS-6
Useful:
- local WebGL HUD
- live pipeline trace
Disposition: REIMPLEMENT UI MECHANISMS.

### MAL19INDUSTRIES/JARVIS-OS-V.2
Useful:
- PyQt6 desktop workspace
- detachable panels
- local desktop + hosted client separation
- screen/camera/files/browser/research surfaces

Disposition: REFERENCE / SELECTIVE ADAPT
License: MIT.

### Jayavisaag/JARVIS
Useful:
- Windows neural HUD / telemetry
- screen + webcam grounding
- multi-monitor coordinate transform
- interruptible SAPI voice
- scheduler
- Android ADB bridge
- smart-home/device panels

Disposition: REIMPLEMENT SELECTED MECHANISMS
Caution: personal portfolio build with hardware-specific assumptions.

## 8. Physical/mobile interface

### Open Interpreter 01
Useful mechanisms:
- voice interface decoupled from device
- desktop/mobile/ESP32 clients
- Light Server / LiveKit server split
- realtime multimodal voice transport

Disposition: REFERENCE / PROTOCOL INSPIRATION ONLY
License: AGPL-3.0.
Upstream explicitly warns that the project is experimental and lacks basic safeguards.

### Jayavisaag/JARVIS
Useful:
- Android ADB control
- smart-light/fan integration
Disposition: REIMPLEMENT generic DeviceProvider contracts, not hardware-specific code.

## 9. Agent/work runtime

### Agent Zero
Useful:
- long-running project workspaces
- subagent delegation
- tools/plugins/MCP/A2A
- local host bridge
- project-scoped secrets/memory
Disposition: ADAPT THROUGH A JARVIS AGENT PROVIDER OR REIMPLEMENT TASK MODEL.

### Agent TARS
Useful:
- multimodal general-agent stack
- terminal/computer/browser/product surfaces
- MCP ecosystem
Disposition: AUDIT NEXT.

## 10. Provisional V0 organ choices

These are hypotheses to test, not frozen dependencies.

VOICE PRESENCE:
  JARVIS-6 mechanisms + Samuel interaction model + Personal Jarvis reference

FAST COMMANDS:
  Jarvis-owned deterministic fast router

PERCEPTUAL TIMELINE:
  screenpipe external adapter

PERSONAL MEMORY:
  Jarvis-owned layered memory; study Leon + Agent Zero

WINDOWS CONTROL:
  UFO2 concepts/native APIs

BROWSER:
  Playwright/DOM-first; visual operator fallback

VISUAL FALLBACK:
  UI-TARS operator/SDK candidate

AGENT WORK:
  Jarvis-owned TaskRuntime; Agent Zero adapter/reference

HUD:
  Jarvis-owned event-driven HUD; study devyuv + JARVIS-6 + MAL19 + Jayavisaag

CAMERA/GESTURE:
  MediaPipe-style gesture provider + explicit camera perception provider

MOBILE/DEVICES:
  Jarvis-owned DeviceProvider; study 01 + Jayavisaag

## 11. New core boundaries suggested by this audit

JarvisCore
- SessionRuntime
- EventBus
- FastIntentRouter
- CognitionProvider
- ContextAssembler
- TaskRuntime
- CapabilityRegistry
- ActionRouter
- PermissionPolicy

Perception
- ScreenProvider
- AudioContextProvider
- CameraProvider
- ActivityProvider
- PerceptualTimeline

Memory
- WorkingMemory
- PersonalMemory
- EpisodicMemory
- ProjectMemory

Action backends
- NativeWindowsBackend
- BrowserBackend
- AccessibilityBackend
- VisualOperatorBackend
- RawInputBackend

Interfaces
- VoiceInterface
- HUDClient
- DesktopClient
- MobileClient
- DeviceBridge

## 12. Hard rule

No integration begins until:
- Tier-A audit is complete enough to compare mechanisms;
- licenses are recorded;
- V0 organ ownership is frozen;
- donor interfaces are behind Jarvis-owned contracts.

Personal Jarvis remains installed but J1-D stays paused.
