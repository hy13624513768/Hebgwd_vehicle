[CmdletBinding()]
param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$runDir = Join-Path $projectRoot ".local-run"
$localDatabaseUrl = "sqlite:///./data/local-dev.db"
$frontendUrl = "http://127.0.0.1:8080"
$backendReadyUrl = "http://127.0.0.1:8000/ready"

New-Item -ItemType Directory -Force -Path $runDir | Out-Null

function Test-HttpEndpoint {
    param([Parameter(Mandatory)][string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

function Wait-HttpEndpoint {
    param(
        [Parameter(Mandatory)][string]$Url,
        [int]$TimeoutSeconds = 60
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if (Test-HttpEndpoint -Url $Url) { return $true }
        Start-Sleep -Milliseconds 750
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Get-PythonExecutable {
    $venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) { return $venvPython }

    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) { return $pythonCommand.Source }

    throw "Python was not found. Install Python 3 and run this script again."
}

$python = Get-PythonExecutable
$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    throw "npm was not found. Install Node.js and run this script again."
}

Push-Location $backendDir
try {
    & $python -c "import fastapi, uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing backend dependencies..."
        & $python -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed." }
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "Installing frontend dependencies..."
    Push-Location $frontendDir
    try {
        & $npmCommand.Source install
        if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." }
    }
    finally {
        Pop-Location
    }
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"

if (Test-HttpEndpoint -Url $backendReadyUrl) {
    Write-Host "Backend is already running: $backendReadyUrl"
}
else {
    $backendOut = Join-Path $runDir "backend-$stamp.stdout.log"
    $backendErr = Join-Path $runDir "backend-$stamp.stderr.log"

    $previousDatabaseUrl = [Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")
    $previousEnvironment = [Environment]::GetEnvironmentVariable("ENVIRONMENT", "Process")
    $previousDemoSeeding = [Environment]::GetEnvironmentVariable("DEMO_SEEDING_ENABLED", "Process")
    try {
        $env:DATABASE_URL = $localDatabaseUrl
        $env:ENVIRONMENT = "development"
        $env:DEMO_SEEDING_ENABLED = "true"
        $backendProcess = Start-Process `
            -FilePath $python `
            -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload") `
            -WorkingDirectory $backendDir `
            -RedirectStandardOutput $backendOut `
            -RedirectStandardError $backendErr `
            -WindowStyle Hidden `
            -PassThru
    }
    finally {
        [Environment]::SetEnvironmentVariable("DATABASE_URL", $previousDatabaseUrl, "Process")
        [Environment]::SetEnvironmentVariable("ENVIRONMENT", $previousEnvironment, "Process")
        [Environment]::SetEnvironmentVariable("DEMO_SEEDING_ENABLED", $previousDemoSeeding, "Process")
    }

    Set-Content -Path (Join-Path $runDir "backend.pid") -Value $backendProcess.Id
    Set-Content -Path (Join-Path $runDir "backend.log.path") -Value $backendErr

    if (-not (Wait-HttpEndpoint -Url $backendReadyUrl -TimeoutSeconds 60)) {
        Write-Host "Backend failed to become ready. Recent error log:" -ForegroundColor Red
        if (Test-Path $backendErr) { Get-Content $backendErr -Tail 30 }
        throw "Backend startup failed."
    }
    Write-Host "Backend started: $backendReadyUrl"
}

if (Test-HttpEndpoint -Url $frontendUrl) {
    Write-Host "Frontend is already running: $frontendUrl"
}
else {
    $frontendOut = Join-Path $runDir "frontend-$stamp.stdout.log"
    $frontendErr = Join-Path $runDir "frontend-$stamp.stderr.log"
    $frontendProcess = Start-Process `
        -FilePath $npmCommand.Source `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "8080") `
        -WorkingDirectory $frontendDir `
        -RedirectStandardOutput $frontendOut `
        -RedirectStandardError $frontendErr `
        -WindowStyle Hidden `
        -PassThru

    Set-Content -Path (Join-Path $runDir "frontend.pid") -Value $frontendProcess.Id
    Set-Content -Path (Join-Path $runDir "frontend.log.path") -Value $frontendErr

    if (-not (Wait-HttpEndpoint -Url $frontendUrl -TimeoutSeconds 60)) {
        Write-Host "Frontend failed to become ready. Recent error log:" -ForegroundColor Red
        if (Test-Path $frontendErr) { Get-Content $frontendErr -Tail 30 }
        throw "Frontend startup failed."
    }
    Write-Host "Frontend started: $frontendUrl"
}

Write-Host ""
Write-Host "Local development service is ready." -ForegroundColor Green
Write-Host "Page:    $frontendUrl"
Write-Host "API:     http://127.0.0.1:8000/docs"
Write-Host "Database: backend\data\local-dev.db"
Write-Host "Logs:    .local-run"

if (-not $NoBrowser) {
    Start-Process $frontendUrl
}
