[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:47821"
)

$ErrorActionPreference = "Stop"

try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/api/health" -Method Get -TimeoutSec 5
    Write-Host "PERSONAL_JARVIS_HEALTH=PASS"
    $health | ConvertTo-Json -Depth 5
}
catch {
    Write-Host "PERSONAL_JARVIS_HEALTH=FAIL"
    throw
}
