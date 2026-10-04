$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$runDir = Join-Path $projectRoot ".local-run"

$stopped = 0
foreach ($name in @("backend", "frontend")) {
    $pidFile = Join-Path $runDir "$name.pid"
    if (-not (Test-Path $pidFile)) { continue }

    $processId = Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($processId -and (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
        Stop-Process -Id $processId -Force
        Write-Host "Stopped $name (PID $processId)."
        $stopped++
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

if ($stopped -eq 0) {
    Write-Host "No launcher-managed local process was found."
}
else {
    Write-Host "Local development service stopped." -ForegroundColor Green
}
