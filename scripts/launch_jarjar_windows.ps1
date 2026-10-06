[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$RepoCandidates = @(
    $env:OBSIDIA_JARJAR_ROOT,
    'C:\Users\User\Desktop\Jarvis-iron-obsidia-',
    (Join-Path $env:USERPROFILE 'Desktop\Jarvis-iron-obsidia-')
) | Where-Object { $_ } | Select-Object -Unique

$Repo = $RepoCandidates | Where-Object { Test-Path -LiteralPath (Join-Path $_ 'scripts\run_jarjar_live.py') } | Select-Object -First 1
if (-not $Repo) {
    throw "Jarjar repo introuvable. Candidats: $($RepoCandidates -join ' | ')"
}

$PythonCandidates = @(
    $env:OBSIDIA_JARJAR_PYTHON,
    'C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'),
    (Join-Path $Repo '.venv\Scripts\python.exe')
) | Where-Object { $_ } | Select-Object -Unique

$Python = $PythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $Python) {
    throw "Python Jarjar introuvable. Candidats: $($PythonCandidates -join ' | ')"
}

$env:JARJAR_BOUNDED_STRUCTURED_ROUTING_V0 = '1'
$env:JARJAR_LOCAL_BRODY = '1'
$env:PYTHONUTF8 = '1'
$env:PYTHONUNBUFFERED = '1'
$env:PYTHONIOENCODING = 'utf-8'

Set-Location -LiteralPath $Repo

Write-Host "JARJAR_REPO=$Repo"
Write-Host "JARJAR_PYTHON=$Python"
Write-Host "JARJAR_MODULE=scripts.run_jarjar_live"
Write-Host "JARJAR_STARTING..."

& $Python -m scripts.run_jarjar_live
$code = $LASTEXITCODE
Write-Host "JARJAR_EXIT_CODE=$code"
if ($code -ne 0) {
    throw "Jarjar a quitte avec le code $code"
}
