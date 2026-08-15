# StreamSocial — application setup & start only (Windows PowerShell).
# Does NOT run tests (use .\test_end_to_end_master.ps1).
#
# Usage (from repo root):
#   .\setup_python.ps1              # deps (if needed) + start full stack
#   .\setup_python.ps1 -StartOnly   # skip venv/pip; just compose up + wait healthy
#   .\setup_python.ps1 -DepsOnly    # install Python deps only
#   .\setup_python.ps1 -Help

param(
    [Switch]$StartOnly,
    [Switch]$DepsOnly,
    [Switch]$Help
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$ReqFile = Join-Path $ScriptDir "streamsocial\backend\requirements.txt"
$ComposeFile = Join-Path $ScriptDir "docker-compose.yml"
$VenvDir = Join-Path $ScriptDir "venv"
$BaseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost:8000" }
$HealthUrl = "$BaseUrl/health"
$MaxWaitSec = if ($env:MAX_WAIT_SEC) { [int]$env:MAX_WAIT_SEC } else { 180 }

if ($Help) {
    Write-Host @"
StreamSocial — application setup & start only (Windows PowerShell).
Does NOT run tests (use .\test_end_to_end_master.ps1).

Usage (from repo root):
  .\setup_python.ps1              # deps (if needed) + start full stack
  .\setup_python.ps1 -StartOnly   # skip venv/pip; just compose up + wait healthy
  .\setup_python.ps1 -DepsOnly    # install Python deps only
  .\setup_python.ps1 -Help
"@
    exit 0
}

$Mode = "full"
if ($StartOnly) { $Mode = "start-only" }
if ($DepsOnly) { $Mode = "deps-only" }

function Write-Log {
    param([string]$Message)
    Write-Host "[setup] $Message" -ForegroundColor Cyan
}

function Write-Error-Log {
    param([string]$Message)
    Write-Host "[setup] ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Test-RequiredFile {
    param([string]$FilePath)
    if (-not (Test-Path $FilePath)) {
        Write-Error-Log "missing required file: $FilePath"
    }
}

function Install-Dependencies {
    Write-Log "Installing dependencies..."
    Test-RequiredFile $ReqFile

    # Check if Python 3 is installed
    $PythonCmd = $null
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $PythonCmd = "python"
    }
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        $PythonCmd = "python3"
    }

    if (-not $PythonCmd) {
        Write-Error-Log "Python 3 is required but not found. Please install Python 3 from https://www.python.org/"
    }

    # Create virtual environment if it doesn't exist
    if (-not (Test-Path $VenvDir)) {
        Write-Log "Creating virtualenv at $VenvDir"
        & $PythonCmd -m venv $VenvDir
    }
    else {
        Write-Log "Reusing virtualenv at $VenvDir"
    }

    # Activate virtual environment
    $ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
    if (-not (Test-Path $ActivateScript)) {
        Write-Error-Log "Failed to create virtual environment at $VenvDir"
    }
    & $ActivateScript

    Write-Log "Upgrading pip..."
    python -m pip install --upgrade pip | Out-Null

    Write-Log "Installing application dependencies from $ReqFile"
    pip install -r $ReqFile

    $PythonVersion = python --version 2>&1
    Write-Log "Python ready: $PythonVersion"
}

function Start-Application {
    Write-Log "Starting application..."
    Test-RequiredFile $ComposeFile

    # Check if Docker is installed
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error-Log "docker is required but not found. Please install Docker Desktop."
    }

    # Check if docker compose is available
    try {
        docker compose version | Out-Null
    }
    catch {
        Write-Error-Log "docker compose plugin is required but not found."
    }

    Write-Log "Starting StreamSocial stack (Kafka + API + consumers)..."
    docker compose -f $ComposeFile up -d --build

    Write-Log "Waiting for API health at $HealthUrl (timeout $MaxWaitSec seconds)..."
    $elapsed = 0
    $healthy = $false

    while ($elapsed -lt $MaxWaitSec) {
        try {
            $response = Invoke-WebRequest -Uri $HealthUrl -Method Get -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $healthy = $true
                break
            }
        }
        catch {
            # Still waiting
        }

        Start-Sleep -Seconds 5
        $elapsed += 5

        if ($elapsed % 15 -eq 0) {
            Write-Log "still waiting... $($elapsed)s"
        }
    }

    if (-not $healthy) {
        Write-Log "Last compose ps:"
        docker compose -f $ComposeFile ps 2>&1 | Out-Null
        Write-Error-Log "API did not become healthy within ${MaxWaitSec}s"
    }

    Write-Log "API is healthy."
    try {
        Invoke-WebRequest -Uri $HealthUrl -Method Get | ConvertTo-Json
    }
    catch {
        # Silently continue
    }

    Write-Host ""
    Write-Log "Services:"
    docker compose -f $ComposeFile ps

    Write-Host ""
    Write-Log "App URLs:"
    Write-Log "  API:      ${BaseUrl}"
    Write-Log "  Health:   ${HealthUrl}"
    Write-Log "  Docs:     ${BaseUrl}/docs"
    Write-Log "  Kafka UI: http://localhost:8080"
    Write-Log "Scale consumers: docker compose up -d --scale kafka-consumer=N"
    Write-Log "Integration tests: .\test_end_to_end_master.ps1"
    Write-Log "Setup complete (app started; tests not run)."
}

# Main execution
switch ($Mode) {
    "deps-only" {
        Install-Dependencies
    }
    "start-only" {
        Start-Application
    }
    "full" {
        Install-Dependencies
        Start-Application
    }
}
