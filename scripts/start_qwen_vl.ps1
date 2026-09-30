param(
    [int]$Port = 8081,
    [int]$CtxSize = 4096,
    [string]$Model = "ggml-org/Qwen2.5-VL-3B-Instruct-GGUF:Q4_K_M"
)

$ErrorActionPreference = "Stop"

$llama = Get-Command llama-server -ErrorAction SilentlyContinue
if (-not $llama) {
    $llama = Get-Command llama -ErrorAction SilentlyContinue
}
if (-not $llama) {
    Write-Host "JARJAR_VISION: llama.cpp not found."
    Write-Host "Install with: winget install llama.cpp"
    exit 2
}

Write-Host "JARJAR_VISION: starting Qwen2.5-VL-3B-Instruct Q4_K_M on port $Port"
Write-Host "JARJAR_VISION: first launch may download the model from Hugging Face"

if ($llama.Name -eq "llama-server.exe" -or $llama.Name -eq "llama-server") {
    & $llama.Source -hf $Model --host 127.0.0.1 --port $Port -c $CtxSize
} else {
    & $llama.Source serve -hf $Model --host 127.0.0.1 --port $Port -c $CtxSize
}
