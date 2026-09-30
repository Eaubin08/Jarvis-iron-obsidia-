# Jarjar → Obsidia Governed Cognition Bridge V0

## Boundary

Jarjar owns the desktop shell: HUD, microphone, wake word, STT/TTS, perception
and bounded action adapters. It does **not** own the Obsidia cognition stack.

The cognition path is:

```text
Jarjar text / Whisper transcript
→ local presence reflex (only trivial acknowledgements)
→ POST /api/brody/chat
→ Obsidia/Brody stack
→ internal routing/provider selection (including local Qwen when the stack decides)
→ final_answer
→ Kokoro / HUD
```

Jarjar never calls Qwen directly and contains no Qwen routing rule.

## Canonical API contract

Default endpoint:

`http://127.0.0.1:8000/api/brody/chat`

Request fields used:

- `message`
- `language="fr"`
- stable Jarjar `session_id`
- `allow_provider=true` by default
- `allow_memory_candidate=false`
- `allow_manual_apply=false`
- debug flags false

Response preference:

1. `final_answer`
2. `response`

The API key, when configured, is sent only as `X-API-Key` and is never logged.

## Authority

This bridge is cognition-only. It does not provide an action execution path.
Provider escalation is a decision of the Obsidia stack. Jarjar action execution
remains behind Jarjar ActionRouter/PermissionPolicy boundaries, and Obsidia
authority remains KX108_ONLY.

## Environment

- `JARJAR_OBSIDIA_CHAT_URL`
- `JARJAR_OBSIDIA_TIMEOUT`
- `JARJAR_OBSIDIA_ALLOW_PROVIDER`
- `OBSIDIA_API_KEY`

If the stack is unavailable, Jarjar degrades to its local V0 presence provider
instead of crashing the voice/HUD runtime.


## Deferred HOLD — cognition/session voice

Status after physical bridge validation:

- Jarjar -> `POST /api/brody/chat` -> HTTP 200: PASS.
- Wake/STT/TTS/HUD V0: PASS.
- Natural conversational continuity: HOLD.
- Short/vague follow-ups may be interpreted poorly by the current Brody/session path.
- Voice remains half-duplex: speech started while Kokoro is speaking may be lost.
- Session timing/loop ergonomics need a later dedicated pass.
- Do not solve these issues by duplicating Brody/router/Qwen logic inside Jarjar.

## Provider causality

`allow_provider=true` only permits the Obsidia stack to consider its provider
path. It is **not evidence that a provider was called**.

Jarjar therefore logs routing metadata returned by Brody when available:

`provider_status`, `provider_called`, `selected_provider`, `source`,
`voice_runtime`, and `fastpath`.

If those fields are absent, provider causality remains UNKNOWN from the Jarjar
side and must not be inferred from answer style alone.
