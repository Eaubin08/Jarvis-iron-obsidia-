# Jarvis Iron — Assembly Contracts V0

Status: PRE-FREEZE CONTRACT DRAFT

## Principle

Jarvis core speaks only Jarvis contracts.
Donor-specific objects never cross the adapter boundary.

## Voice

WakeWordProvider.detect(audio) -> WakeEvent
SpeechToTextProvider.transcribe(audio) -> Transcript
TextToSpeechProvider.speak(text, interrupt_token) -> SpeechHandle
SpeakerSignalProvider.compare(audio) -> IdentitySignal

Required behavior:
- cancellable output;
- barge-in;
- timestamps;
- provider identity;
- failure is explicit.

## Perception

ScreenProvider.snapshot() -> ScreenObservation
AudioContextProvider.recent(window) -> AudioObservation[]
CameraProvider.snapshot() -> CameraObservation
ActivityProvider.current() -> ActivityObservation
PerceptualTimeline.query(query, time_range, limit) -> Observation[]

Historical observations are immutable evidence, not live action handles.

## Context

ContextAssembler.build(session, task, request) -> ContextSnapshot

Snapshot records provenance for every included memory/observation and stays bounded.

## Memory

WorkingMemory: session-local, ephemeral.
PersonalMemory: durable admitted personal facts/preferences.
ProjectMemory: project-scoped knowledge/state.
EpisodicMemory: selected Jarvis interactions/events.
PerceptualTimeline: high-volume observational history.

Each store has independent admission, retention and query policy.

## Cognition

CognitionProvider.respond(input, context, tools) -> CognitionResult

No provider is mandatory.
Cognition cannot execute OS actions directly.

## Tasks

TaskRuntime.create(goal) -> Task
TaskRuntime.step(task_id) -> TaskStep
TaskRuntime.cancel(task_id)
TaskRuntime.resume(task_id)

Task state and artifacts are Jarvis-owned even when an external agent executes work.

## Actions

CapabilityRegistry.resolve(intent) -> Capability
PermissionPolicy.evaluate(request, context) -> PermissionDecision
ActionBackend.execute(ActionRequest) -> ActionResult

ActionRequest includes:
- capability
- arguments
- target
- source
- session/task id
- risk class
- idempotency key when applicable

ActionResult includes:
- success/failure
- backend
- started/finished timestamps
- structured result
- user-visible summary
- evidence/receipt references

## Action backend ladder

NativeWindowsBackend
BrowserBackend
AccessibilityBackend
VisualOperatorBackend
RawInputBackend

ActionRouter selects the highest-structure backend that can satisfy the request.

## Interfaces

HUDClient consumes JarvisEvent and emits typed UserCommand.
DesktopClient consumes JarvisEvent and emits typed UserCommand.
MobileClient uses the same logical protocol.

No UI calls donor internals directly.

## Events

Minimum event families:
- session.*
- voice.*
- perception.*
- context.*
- cognition.*
- task.*
- action.*
- memory.*
- permission.*
- ui.*
- system.*

Every event:
event_id
event_type
timestamp
source
session_id
task_id?
payload
correlation_id?
causation_id?

## Replacement test

A donor adapter is acceptable only if a fake provider can replace it without
changing JarvisCore.

This is the primary anti-lock-in test.
