# Jarvis Iron — Integration Disposition V0

Date: 2026-09-29
Status: AUDIT / PROVISIONAL

## Rule

A donor can contribute one organ without becoming a runtime dependency.
Licensing is evaluated for source AND bundled models/assets.

## Dispositions

### PersonalJarvis/PersonalJarvis
- Current 2.x source license: Apache-2.0.
- <=1.6.0 remains MIT.
- Current audited release family: 2.3.x.
- Role: general voice/computer-use donor and protocol test fixture.
- Mode: EXTERNAL RUNTIME ADAPTER / SELECTIVE SOURCE STUDY.
- Do not make it Jarvis Iron's root application.

### screenpipe/screenpipe
- Current source license: Screenpipe Commercial License.
- Free personal/non-commercial use; commercial terms apply to commercial use.
- Role: perceptual timeline: screen/audio/activity/search.
- Mode: EXTERNAL LOCAL SERVICE ADAPTER.
- No source copy into Jarvis core during V0.

### microsoft/UFO
- Source license: MIT.
- Role: Windows structured action reference: UIA/Win32/COM/MCP.
- Mode: SELECTIVE ADAPT / REIMPLEMENT behind NativeWindowsBackend.
- Do not inherit its agent hierarchy as Jarvis core.

### bytedance/UI-TARS-desktop
- Source license: Apache-2.0.
- Latest public release observed during audit: v0.3.0.
- Role: visual computer-use fallback / browser operator.
- Mode: SDK/OPERATOR ADAPTER.
- Caveat: upstream quick-start warns of single-monitor limitations for some tasks.

### leon-ai/leon
- Source license: MIT.
- Current 2.0 work is Developer Preview on develop.
- Role: context/memory/skills architecture donor.
- Mode: REIMPLEMENT CONCEPTS / SELECTIVE ADAPT.
- No hard V0 runtime dependency.

### agent0ai/agent-zero
- Source license: MIT.
- Role: project/task/subagent/skills donor.
- Mode: REIMPLEMENT TASK MODEL; optional external AgentProvider later.

### sambuild04/screen-voice-agent (Samuel)
- Source license: MIT.
- Current implementation: macOS 14+.
- Role: realtime conversational behavior, ambient screen/audio coupling,
  interruption and recent-audio recall.
- Mode: REIMPLEMENT BEHAVIOR FOR WINDOWS.

### psycoks/Jarvis (JARVIS-6)
- Role: Windows-local voice pipeline, wake/follow-up/speaker verification,
  Playwright/browser and HUD ideas.
- Mode: SELECTIVE ADAPT / REIMPLEMENT.
- IMPORTANT: verify repository license at exact pin before any source reuse.
- IMPORTANT: bundled wake-word/model licenses are independent of source license.

### openinterpreter/01
- Source license: AGPL-3.0.
- Role: voice/device/mobile/ESP32 protocol reference.
- Mode: REFERENCE / PROTOCOL INSPIRATION.
- Avoid embedding into V0.

### MAL19INDUSTRIES/JARVIS-OS-V.2
- Source license: MIT.
- Role: PyQt6 workspace, detachable panels, desktop UX surfaces.
- Mode: SELECTIVE UI REFERENCE / ADAPT.

### devyuv/JARVIS
- Source license: MIT.
- Role: Three.js HUD, WebSocket event display, MediaPipe gestures, simple
  auto-discovered skills.
- Mode: SELECTIVE TAKE/ADAPT after exact-pin audit.

## Model/asset license boundary

Never infer that a permissive repository license makes bundled models/assets
commercially reusable.

Known example to guard:
- common openWakeWord hey_jarvis model distributions can carry
  CC BY-NC-SA terms.
- commercial Jarvis Iron must replace/retrain any non-commercial wake-word
  asset before distribution.

Every pinned donor gets:
SOURCE_LICENSE
MODEL_LICENSES
ASSET_LICENSES
NOTICE_REQUIREMENTS
COMMERCIAL_OK
INTEGRATION_MODE
