# Qwen runtime freeze — FIXE — 2026-10-08

## Scope

Freeze candidate for the repaired local Jarjar cognition runtime on the FIXE machine (`C:\Users\Aubin`).

This freeze records the exact working launch commands, ports, runtime build, local model path, camera mapping, and validation gates for:

- Qwen text
- Qwen-VL camera
- Qwen-VL screen
- Jarjar real routing
- Python regression

Do not replace the Qwen text local model launch with `-hf` on this machine unless intentionally revalidating the runtime.

## Canonical ports

| Component | Port |
|---|---:|
| Kernel X108 | 3001 |
| Brody / API / Native Memory | 8000 |
| Qwen text | 8080 |
| Qwen-VL | 8081 |

## llama.cpp runtime

```text
version: 0.5.0-dev
build: 11193
commit: 4e7481175
compiler: Clang 20.1.8 for Windows x86_64
```

Canonical local runtime folder:

```text
C:\Users\Aubin\Desktop\llama-b11193
```

## Qwen text — frozen working configuration

Model:

```text
C:\Users\Aubin\Desktop\MODELS\QWEN\qwen2.5-3b-instruct-q4_k_m.gguf
```

Launch:

```powershell
& "C:\Users\Aubin\Desktop\llama-b11193\llama-server.exe" `
  -m "C:\Users\Aubin\Desktop\MODELS\QWEN\qwen2.5-3b-instruct-q4_k_m.gguf" `
  --host 127.0.0.1 `
  --port 8080 `
  -c 4096
```

Observed validation:

```text
QWEN_TEXT_PHYSICAL: PASS
PARIS exact API smoke: PASS
```

Important: the working freeze uses the local GGUF path above. Earlier `-hf` launches triggered Hugging Face downloads and are not part of this freeze.

## Qwen-VL — frozen working configuration

Launch:

```powershell
$env:PATH = "C:\Users\Aubin\Desktop\llama-b11193;$env:PATH"
Set-Location "C:\Users\Aubin\Desktop\Jarvis-iron-obsidia-github"
powershell -ExecutionPolicy Bypass -File .\scripts\start_qwen_vl.ps1
```

Camera mapping:

```text
JARJAR_CAMERA_INDICES=0
```

Observed validation:

```text
VISION_PHYSICAL: PASS
VISION_SCREEN_PHYSICAL: PASS
```

## Full runtime launch order

Open four PowerShell terminals.

### Terminal 1 — Kernel :3001

```powershell
Set-Location "C:\Users\Aubin\Desktop\OBSIDIA_WORLDS\sources\obsidia-x108-proofs"
powershell -ExecutionPolicy Bypass -File .\scripts\runtime\start_kernel.ps1
```

### Terminal 2 — Brody / API / Native Memory :8000

```powershell
Set-Location "C:\Users\Aubin\Desktop\OBSIDIA_WORLDS\sources\obsidia-x108-proofs"
powershell -ExecutionPolicy Bypass -File .\scripts\runtime\start_api.ps1
```

### Terminal 3 — Qwen text :8080

```powershell
& "C:\Users\Aubin\Desktop\llama-b11193\llama-server.exe" `
  -m "C:\Users\Aubin\Desktop\MODELS\QWEN\qwen2.5-3b-instruct-q4_k_m.gguf" `
  --host 127.0.0.1 `
  --port 8080 `
  -c 4096
```

### Terminal 4 — Qwen-VL :8081

```powershell
$env:PATH = "C:\Users\Aubin\Desktop\llama-b11193;$env:PATH"
Set-Location "C:\Users\Aubin\Desktop\Jarvis-iron-obsidia-github"
powershell -ExecutionPolicy Bypass -File .\scripts\start_qwen_vl.ps1
```

## Port readiness check

```powershell
3001,8000,8080,8081 | ForEach-Object {
    $p = $_
    $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($c) {
        Write-Host "$p READY PID=$($c.OwningProcess)"
    } else {
        Write-Host "$p DOWN"
    }
}
```

Expected:

```text
3001 READY
8000 READY
8080 READY
8081 READY
```

## Validation commands

```powershell
Set-Location "C:\Users\Aubin\Desktop\Jarvis-iron-obsidia-github"

$PY = "C:\Users\Aubin\Desktop\Jarvis-iron-obsidia-\.venv\Scripts\python.exe"
$env:PYTHONPATH = "$PWD\src"
$env:JARJAR_CAMERA_INDICES = "0"
$env:JARJAR_VISION_TIMEOUT = "180"

& $PY -m scripts.smoke_qwen_text
& $PY -m scripts.smoke_qwen_vl
& $PY -m scripts.smoke_qwen_vl_screen
& $PY -m scripts.smoke_jarjar_route_e2e
```

Observed physical results:

```text
QWEN_TEXT_PHYSICAL: PASS
VISION_PHYSICAL: PASS
VISION_SCREEN_PHYSICAL: PASS

JARJAR_OBSIDIA: discovered http://127.0.0.1:8000/api/brody/chat
ROUTE_GENERAL: qwen
ROUTE_VISUAL: vision
JARJAR_LOCAL_BRODY: PASS
ROUTE_OBSIDIA: brody
ROUTE_ACTION: action_router
JARJAR_ROUTE_E2E: PASS
```

## Regression

Targeted Windows newline portability test:

```text
6 passed
```

Full Python regression:

```text
514 passed, 9 skipped, 0 failed
```

The only code change required for this regression was to make the G3 unified-patch test newline-agnostic on Windows.

## Freeze verdict

```text
QWEN_TEXT_8080 = FROZEN_CANDIDATE
QWEN_VL_8081 = FROZEN_CANDIDATE
JARJAR_REAL_ROUTING = PASS
PYTHON_REGRESSION = PASS
```

This document is the reproducibility record to use before creating the Git tag.
