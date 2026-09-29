# Personal Jarvis donor audit — Gate 0

Upstream: `PersonalJarvis/PersonalJarvis`
Role candidate: primary V0 voice/orchestration/computer-use donor.
License observed: Apache-2.0 for current 2.x; <=1.6.0 remains MIT.
Current decision: **ADAPT_CANDIDATE**.

Why:
- voice-first personal assistant;
- wake word / STT / TTS;
- computer operation and dictation;
- MCP connectivity;
- agent/coding CLI orchestration;
- Windows support;
- can run self-hosted.

Rules:
- do not make Jarvis Core depend on Personal Jarvis internals;
- integrate only behind Jarvis provider contracts;
- pin an exact upstream commit before code reuse;
- preserve required Apache NOTICE/attribution for copied/modified code.

Next gate: map upstream modules to VoiceProvider, CognitionProvider and ActionProvider.
