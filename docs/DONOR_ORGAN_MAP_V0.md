# Jarvis Iron — Donor Organ Map V0

Status: AUDIT / NO INTEGRATION DECISION YET

The goal is not to select one upstream Jarvis. We select or reimplement the
best mechanisms organ-by-organ, then assemble them behind Jarvis-owned
contracts.

## Voice / conversational presence

Candidates:
- PersonalJarvis/PersonalJarvis
- sambuild04/screen-voice-agent (Samuel)
- psycoks/Jarvis (JARVIS-6)
- openinterpreter/01
- Jayavisaag/JARVIS

Audit focus:
wake word, interruption/barge-in, STT/TTS locality, latency, continuous
listening, speaker verification, realtime transport.

Current strongest mechanisms to study:
- Samuel: realtime voice presence + interruption + ambient context coupling.
- JARVIS-6: Windows-local wake/STT/TTS path.
- Personal Jarvis: mature configurable desktop voice/provider shell.
- 01: device-independent speech-to-speech transport.

## Ambient perception / timeline

Candidates:
- screenpipe/screenpipe
- Samuel
- JARVIS-6
- Jayavisaag/JARVIS

Current strongest mechanisms to study:
- screenpipe: continuous screen/audio/activity capture, accessibility tree,
  OCR fallback, transcription, searchable local history.
- Samuel: rolling recent-audio recall tied to live conversation.
- JARVIS-6: on-demand screen vision.
- Jayavisaag: screen + webcam grounding.

Likely architecture:
continuous low-cost perception != expensive semantic reasoning.
Jarvis should retain a local perceptual timeline and escalate selected moments
to cognition.

## Windows computer use

Candidates:
- microsoft/UFO (UFO2)
- bytedance/UI-TARS-desktop
- JARVIS-6
- Personal Jarvis
- Jayavisaag/JARVIS

Current strongest mechanisms to study:
- UFO2: Windows-native UIA/Win32/COM + GUI/API hybrid execution.
- UI-TARS: VLM visual grounding and mouse/keyboard operator.
- JARVIS-6: Playwright browser + Windows desktop tools.
- Personal Jarvis: approval-aware general computer-use surface.

Likely architecture:
1. native/API action when available;
2. browser DOM/Playwright for web;
3. accessibility/UIA for desktop;
4. visual VLM operator as fallback.

## Browser

Candidates:
- JARVIS-6 / Playwright
- Samuel / Playwright
- UI-TARS Browser Operator
- Agent TARS
- Personal Jarvis

Audit focus:
persistent session, DOM-first vs visual fallback, credential handling,
confirmation boundaries, observability.

## Personal memory / context

Candidates:
- Leon 2.0
- screenpipe
- Personal Jarvis
- Agent Zero

Current strongest mechanisms to study:
- Leon: layered memory + environment context + profile isolation.
- screenpipe: perceptual/event memory rather than semantic personal memory.
- Agent Zero: project-scoped files/instructions/secrets/memories.

Important distinction:
personal semantic memory, working context and perceptual timeline are separate
organs and must not be collapsed into one database.

## Agents / long-running work

Candidates:
- Agent Zero
- Leon
- Personal Jarvis
- Agent TARS

Audit focus:
task lifecycle, delegation, resumability, artifacts, tool creation, recovery,
human steering.

## HUD / embodiment

Candidates:
- devyuv/JARVIS
- psycoks/Jarvis
- MAL19INDUSTRIES/JARVIS-OS-V.2
- Jayavisaag/JARVIS
- davidakpele/jarvis

Current mechanisms to study:
- devyuv: Three.js HUD + gesture control + WebSocket-driven state.
- JARVIS-6: local WebGL HUD.
- JARVIS-OS-V.2: PyQt6 desktop workspace/panels.
- Jayavisaag: neural-core command center + device/system telemetry.
- davidakpele: Stark-style UI + camera view.

Rule:
HUD consumes Jarvis events. HUD never owns cognition or actions.

## Camera / gesture

Candidates:
- devyuv/JARVIS: MediaPipe hand gestures.
- Jayavisaag/JARVIS: webcam vision grounding.
- davidakpele/jarvis: live camera + AI vision.

## Mobile / physical devices

Candidates:
- openinterpreter/01: mobile + ESP32 architecture.
- Jayavisaag/JARVIS: phone + smart-home control.
- Home Assistant Assist: later specialized smart-home audit.

## Self-extension / skills

Candidates:
- Samuel: self-written / repairable plugins.
- Leon: Skills -> Actions -> Tools -> Functions.
- Agent Zero: skills/plugins/tool creation.
- Personal Jarvis: agents + Plugins/Skills/MCP.

This organ is high-value but must be bounded: generated tools are not silently
promoted into trusted permanent capabilities.

## Provisional assembly hypothesis — NOT FROZEN

Human
  -> realtime voice
  -> Jarvis session/event core
       -> context assembler
            -> personal memory
            -> perceptual timeline
            -> current screen/audio/camera
       -> cognition provider
       -> task/agent runtime
       -> action router
            -> native Windows/API
            -> browser/DOM
            -> accessibility/UIA
            -> visual computer-use fallback
       -> event stream
            -> voice output
            -> HUD
            -> notifications
            -> mobile/device clients

No upstream project owns this graph.
