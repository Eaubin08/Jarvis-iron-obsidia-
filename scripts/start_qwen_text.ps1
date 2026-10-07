param(
    [int]$Port = 8080,
    [int]$CtxSize = 4096,
    [string]$Model = "Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M",
    [switch]$CpuOnly,
    [string]$LogFile = ""
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

$mode = if ($CpuOnly) { "CPU" } else { "AUTO" }
Write-Host "JARJAR_QWEN: starting Qwen2.5-3B-Instruct Q4_K_M on port $Port (mode=$mode)"

$args = @('-hf',$Model,'--host','127.0.0.1','--port',"$Port",'-c',"$CtxSize")
if ($CpuOnly) {
    $args += @('--gpu-layers','0')
}
if ($LogFile) {
    $args += @('--log-file',$LogFile,'--log-verbosity','5','--log-colors','off')
}

if ($llama.Name -eq "llama-server.exe" -or $llama.Name -eq "llama-server") {
    & $llama.Source @args
} else {
    & $llama.Source serve @args
}

$code = $LASTEXITCODE
if ($null -eq $code) { $code = 1 }
Write-Host "JARJAR_QWEN: llama.cpp exited with code $code (mode=$mode)"
exit $code
