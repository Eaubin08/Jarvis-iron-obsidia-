param(
    [int]$Port = 8080,
    [int]$CtxSize = 4096,
    [string]$Model = "Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M"
)

$ErrorActionPreference = "Stop"

$llama = Get-Command llama-server -ErrorAction SilentlyContinue
if (-not $llama) {
    $llama = Get-Command llama -ErrorAction SilentlyContinue
}
if (-not $llama) {
    Write-Host "JARJAR_QWEN: llama.cpp not found."
    Write-Host "Install with: winget install llama.cpp"
    exit 2
}

Write-Host "JARJAR_QWEN: starting Qwen2.5-3B-Instruct Q4_K_M on port $Port"

if ($llama.Name -eq "llama-server.exe" -or $llama.Name -eq "llama-server") {
    & $llama.Source -hf $Model --host 127.0.0.1 --port $Port -c $CtxSize
} else {
    & $llama.Source serve -hf $Model --host 127.0.0.1 --port $Port -c $CtxSize
}
