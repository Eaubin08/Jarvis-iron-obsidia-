[CmdletBinding()]
param(
    [string]$InstallRoot = "$env:USERPROFILE\.jarvis-iron\donors\personal-jarvis",
    [switch]$InstallDependencies
)

$ErrorActionPreference = "Stop"
$Repo = "https://github.com/PersonalJarvis/PersonalJarvis.git"
$Pin = "53d8c4d16f7baf5cfbfb2e02896fae4b89c4628f"

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

Require-Command git
Require-Command python

$pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$parts = $pythonVersion.Split(".")
if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 11)) {
    throw "Python 3.11+ required; found $pythonVersion"
}

if (-not (Test-Path $InstallRoot)) {
    New-Item -ItemType Directory -Force -Path (Split-Path $InstallRoot) | Out-Null
    git clone $Repo $InstallRoot
}

Push-Location $InstallRoot
try {
    git fetch origin $Pin
    git checkout --detach $Pin

    $actual = (git rev-parse HEAD).Trim()
    if ($actual -ne $Pin) {
        throw "Donor pin mismatch. Expected $Pin, got $actual"
    }

    if (-not (Test-Path ".venv")) {
        python -m venv .venv
    }

    $venvPython = Join-Path $InstallRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        throw "Virtual environment was not created correctly."
    }

    if ($InstallDependencies) {
        & $venvPython -m pip install --upgrade pip
        & $venvPython -m pip install -e ".[full]"
    }

    Write-Host "PERSONAL_JARVIS_PIN_OK=$actual"
    Write-Host "INSTALL_ROOT=$InstallRoot"
    if (-not $InstallDependencies) {
        Write-Host "Dependencies not installed. Re-run with -InstallDependencies after reviewing the donor."
    }
}
finally {
    Pop-Location
}
