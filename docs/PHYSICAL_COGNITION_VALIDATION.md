# Physical cognition validation — Qwen text + Qwen-VL screen

After camera vision PASS, two V0 physical gates remain:

1. Qwen-VL on the full Windows virtual desktop.
2. Qwen text on the local OpenAI-compatible endpoint.

## Dual-screen vision

Keep the Qwen-VL server on port 8081 running, then:

```powershell
python -m scripts.smoke_qwen_vl_screen
```

Success:

`VISION_SCREEN_PHYSICAL: PASS`

## Qwen text

Start a separate local text server:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_qwen_text.ps1
```

Default model:

`Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M`

Then, in another terminal:

```powershell
python -m scripts.smoke_qwen_text
```

Success:

`QWEN_TEXT_PHYSICAL: PASS`

Both providers return text only and have no action authority.
