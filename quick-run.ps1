# StreamSocial Quick Start Script
# Fast execution of common docker-compose operations
#
# Examples:
#   .\quick-run.ps1              (start stack)
#   .\quick-run.ps1 -stop        (stop stack)
#   .\quick-run.ps1 -logs        (view logs)
#   .\quick-run.ps1 -scale 3     (scale consumer to 3)

param(
    [switch]$stop,
    [switch]$logs,
    [switch]$status,
    [switch]$restart,
    [int]$scale = 0,
    [switch]$demo
)

$ProjectRoot = Get-Location
$ComposeFile = "streamsocial/Dockerfile"

# Validate compose file exists
if (-not (Test-Path $ComposeFile)) {
    Write-Host "[ERROR] Docker Compose file not found at $ComposeFile" -ForegroundColor Red
    Write-Host "  Please run this script from the project root directory" -ForegroundColor Yellow
    exit 1
}

# Validate Docker is available
try {
    docker compose version | Out-Null
}
catch {
    Write-Host "[ERROR] Docker Compose not available" -ForegroundColor Red
    Write-Host "  Please ensure Docker Desktop is installed and running" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  StreamSocial Stack Management" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Execute action
if ($stop) {
    Write-Host "[STOP] Stopping stack..." -ForegroundColor Yellow
    docker compose -f $ComposeFile down
    Write-Host "[OK] Stack stopped" -ForegroundColor Green
}
elseif ($logs) {
    Write-Host "[LOGS] Displaying logs (Ctrl+C to exit)..." -ForegroundColor Cyan
    docker compose -f $ComposeFile logs -f
}
elseif ($status) {
    Write-Host "[STATUS] Stack Status:" -ForegroundColor Cyan
    docker compose -f $ComposeFile ps
}
elseif ($restart) {
    Write-Host "[RESTART] Restarting stack..." -ForegroundColor Yellow
    docker compose -f $ComposeFile restart
    Write-Host "[OK] Stack restarted" -ForegroundColor Green
}
elseif ($scale -gt 0) {
    Write-Host "[SCALE] Scaling kafka-consumer to $scale replicas..." -ForegroundColor Yellow
    docker compose -f $ComposeFile up -d --scale kafka-consumer=$scale
    Write-Host "[OK] Scaled to $scale replicas" -ForegroundColor Green
    Start-Sleep -Seconds 2
    docker compose -f $ComposeFile ps
}
elseif ($demo) {
    Write-Host "[DEMO] Starting Demo Mode..." -ForegroundColor Green
    Write-Host ""
    
    # Start stack
    Write-Host "  [1] Starting services (Kafka + API)..." -ForegroundColor Cyan
    docker compose -f $ComposeFile up -d --build
    Write-Host "     Waiting for services to be healthy..." -ForegroundColor Gray
    Start-Sleep -Seconds 30
    
    # Show status
    Write-Host "`n  [2] Current Status:" -ForegroundColor Cyan
    docker compose -f $ComposeFile ps
    
    # Scale consumer
    Write-Host "`n  [3] Scaling consumer to 3 instances..." -ForegroundColor Cyan
    docker compose -f $ComposeFile up -d --scale kafka-consumer=3
    Start-Sleep -Seconds 5
    
    # Final status
    Write-Host "`n  [OK] Demo Stack Ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  => Access Points:" -ForegroundColor Green
    Write-Host "     * Kafka UI:       http://localhost:8080" -ForegroundColor White
    Write-Host "     * API Health:     http://localhost:8000/actuator/health" -ForegroundColor White
    Write-Host "     * API Metrics:    http://localhost:8000/actuator/metrics" -ForegroundColor White
    Write-Host ""
    Write-Host "  * Try This:" -ForegroundColor Green
    Write-Host "     curl -X POST http://localhost:8000/api/events/bulk/generate?count=100" -ForegroundColor White
    Write-Host ""
}
else {
    Write-Host "[START] Starting stack with build..." -ForegroundColor Green
    docker compose -f $ComposeFile up -d --build
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n[OK] Stack started" -ForegroundColor Green
        Write-Host ""
        Write-Host "[STATUS] Current Status:" -ForegroundColor Cyan
        docker compose -f $ComposeFile ps
        Write-Host ""
        Write-Host "[TIP] Quick commands:" -ForegroundColor Yellow
        Write-Host "   View logs:      .\quick-run.ps1 -logs" -ForegroundColor Gray
        Write-Host "   Stop stack:     .\quick-run.ps1 -stop" -ForegroundColor Gray
        Write-Host "   Scale consumer: .\quick-run.ps1 -scale 3" -ForegroundColor Gray
        Write-Host "   Demo mode:      .\quick-run.ps1 -demo" -ForegroundColor Gray
        Write-Host ""
    }
    else {
        Write-Host "[ERROR] Failed to start stack" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
