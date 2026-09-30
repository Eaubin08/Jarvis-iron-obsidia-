# UI-TARS REAL PROVIDER GATE

Status: READY / ENDPOINT REQUIRED

## Provider

Jarvis now includes `OpenAICompatibleUITARSGrounder`.

It accepts:

- `base_url`
- `model`
- `api_key`

and sends the fresh screenshot plus semantic instruction to an
OpenAI-compatible `/chat/completions` endpoint.

This matches the deployment seam documented by UI-TARS for local vLLM and
OpenAI-compatible endpoints.

No UI-TARS agent loop, generated Python, or donor task state is adopted.

## Physical gate

The opt-in test creates only a disposable local Tk window containing one large
button labeled `CLICK TARGET`.

The proof requires:

1. Jarvis captures a fresh screenshot.
2. The real UI-TARS endpoint receives screenshot + semantic instruction.
3. The model returns a grounded click.
4. Jarvis parses and reprojects it.
5. Existing bounded PyAutoGUI execution clicks the local target.
6. The Tk callback confirms the actual target was hit.

Required environment variables:

```text
JARVIS_REAL_UITARS_TEST=1
JARVIS_UITARS_BASE_URL=http://127.0.0.1:8000/v1
JARVIS_UITARS_MODEL=ui-tars
JARVIS_UITARS_API_KEY=empty
```

Remote compatible endpoints may be used by changing those values.

## Non-claims

This gate does not prove:

- multi-monitor correctness;
- arbitrary-app reliability;
- unrestricted multi-action autonomy;
- browser superiority over Playwright;
- replacement of structured UIA/WinCOM paths.
