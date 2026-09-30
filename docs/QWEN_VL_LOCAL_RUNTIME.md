# Qwen2.5-VL local runtime — target machine

Chosen physical V0 model:

`ggml-org/Qwen2.5-VL-3B-Instruct-GGUF:Q4_K_M`

Rationale:

- multimodal Qwen-VL model;
- GGUF is available from ggml-org;
- Q4_K_M is materially lighter than F16/Q8 for the target CPU/16 GB machine;
- llama.cpp exposes an OpenAI-compatible local server;
- Jarjar already targets that API contract on port 8081.

## Install llama.cpp on Windows

```powershell
winget install llama.cpp
```

Close/reopen PowerShell if the executable is not immediately visible.

## Launch vision server

```powershell
cd C:\Users\User\Desktop\Jarvis-iron-obsidia-
powershell -ExecutionPolicy Bypass -File .\scripts\start_qwen_vl.ps1
```

Default endpoint:

`http://127.0.0.1:8081/v1/chat/completions`

The first launch may download the GGUF model.

## Physical validation

Keep the vision server running in terminal 1. In terminal 2:

```powershell
cd C:\Users\User\Desktop\Jarvis-iron-obsidia-
& 'C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m scripts.smoke_qwen_vl
```

Success ends with:

`VISION_PHYSICAL: PASS`

## Boundary

This provider returns descriptive text only. It cannot click, type, launch
applications, or bypass ActionRouter/PermissionPolicy.


## Diagnostic note

The first physical smoke uses one fresh image only. This keeps the validation
focused on API/model correctness before attempting multi-image inference on
the CPU target.

The vision adapter now preserves HTTP status and the beginning of the server
error body so failures are diagnosable instead of collapsing to a generic
"provider unavailable" error.


## CPU timeout calibration

On the target CPU machine, the first multimodal request was still processing
normally when the previous 45-second client timeout cancelled it. The server
had processed 1594 tokens and reported no model failure.

Defaults are therefore now:

- `JARJAR_VISION_TIMEOUT=180`
- `JARJAR_VISION_MAX_TOKENS=96`
- smoke output limited to 48 tokens

These remain configurable. The longer timeout reflects CPU inference latency;
it is not evidence of a provider failure.


## CPU screen preprocessing

The original virtual-desktop screenshot remains full-resolution evidence for
coordinate mapping and action receipts.

For local CPU Qwen-VL inference only, `live-screen` evidence is copied and
downscaled to a maximum dimension of 1280 pixels before being sent to the
vision model. This avoids mutating the canonical screenshot while reducing
multimodal prompt cost and latency.

Override with:

`JARJAR_VISION_SCREEN_MAX_DIMENSION`
