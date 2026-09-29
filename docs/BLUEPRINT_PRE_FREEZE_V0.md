# Jarvis Iron — Blueprint Pre-Freeze V0

Date: 2026-09-29
Status: PRE-FREEZE — NOT YET IMPLEMENTATION AUTHORITY

## Core ownership

Jarvis Iron owns:
- event schemas
- session state
- provider contracts
- fast-intent routing
- context assembly
- memory separation
- task lifecycle
- capability registry
- action routing
- permission policy
- UI/HUD event protocol

No donor owns those contracts.

## Runtime graph

VOICE INPUT
  -> WakeWordProvider
  -> VAD / turn detector
  -> optional SpeakerSignalProvider
  -> SpeechToTextProvider
  -> ConversationRuntime
       -> FastIntentRouter
            -> exact CapabilityRequest
            -> CognitionProvider
       -> ContextAssembler
            -> WorkingMemory
            -> PersonalMemory
            -> ProjectMemory
            -> EpisodicMemory
            -> PerceptualTimeline
       -> TaskRuntime
       -> ActionRouter
            -> Native/API
            -> Browser DOM/Playwright
            -> Windows UIA/Win32/COM
            -> VisualOperator
            -> RawInput fallback
       -> EventBus
            -> TTS
            -> HUD
            -> Desktop UI
            -> notifications
            -> future mobile/device clients

## External V0 services

Screenpipe:
perceptual history only.

Optional cognition providers:
replaceable via CognitionProvider.

Optional visual operator:
UI-TARS-compatible adapter.

Optional long-task donor:
Agent Zero-compatible AgentProvider after V0 core.

## Windows-first execution

Priority:
1. deterministic capability/API
2. application-native interface
3. browser DOM
4. Windows accessibility/native automation
5. visual VLM
6. raw input

This avoids treating the desktop as pixels when the OS/application exposes
structured state.

## Voice-first execution

Priority:
- local wake/VAD/STT/TTS where practical;
- provider-neutral cognition;
- barge-in;
- short follow-up listening window;
- fast path for deterministic commands;
- explicit escalation to cognition only when required.

## HUD

HUD is a Jarvis event consumer.

It can display:
- listening/thinking/speaking state
- transcript
- current task
- action preview/result
- active app/context
- perceptual timeline query result
- agent/task progress
- system/device telemetry
- optional 3D/gesture layer

It cannot directly mutate core state outside typed commands.

## Pre-freeze blockers

A. exact SHA table for Tier-A donors
B. exact license verification for JARVIS-6 and remaining minor HUD donors
C. browser implementation choice
D. Windows voice benchmark on target machine
E. event/schema contract expansion
F. V0 integration-test matrix
G. dependency layout: external services vs packages vs reference-only

J1-D Personal Jarvis remains PAUSED until the architecture freeze.
