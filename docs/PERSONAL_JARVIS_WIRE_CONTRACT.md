# Personal Jarvis wire contract — J1-B

Audit target:
`PersonalJarvis/PersonalJarvis@53d8c4d16f7baf5cfbfb2e02896fae4b89c4628f`

Source of truth used for J1:
upstream `scripts/smoke_boot.py`, which is explicitly its functional
end-to-end boot test.

## Chat transport

Default local runtime:
`ws://127.0.0.1:47821/ws`

Outbound text turn:

```json
{
  "type": "message",
  "kind": "text",
  "content": "hello",
  "metadata": {"thread_id": "jarvis-iron"}
}
```

Successful terminal event:

```json
{
  "type": "event",
  "event_name": "ResponseGenerated",
  "payload": {"text": "..."}
}
```

Brain-layer `ErrorOccurred` is terminal failure.

## Boundary

Only `src/jarvis/transports/personal_jarvis_ws.py` knows this donor protocol.

`JarvisCore` and `PersonalJarvisCognition` remain donor-protocol agnostic.

## J1-B verdict

**PASS STRUCTURAL**

The transport has an injectable connection factory and contract tests.
A real-machine E2E remains J1-D and requires the donor runtime to be installed,
configured with a model provider, and running.
