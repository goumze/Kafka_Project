# StreamSocial Docker Compose Orchestration Script
# Manages the full Kafka + Spring Boot microservices stack
# 
# Usage:
#   .\manage-streamsocial.ps1 -Action build
#   .\manage-streamsocial.ps1 -Action start
#   .\manage-streamsocial.ps1 -Action stop
#   .\manage-streamsocial.ps1 -Action logs -Service kafka-consumer
#   .\manage-streamsocial.ps1 -Action scale -Service kafka-consumer -Replicas 3

param(
    [Parameter(Mandatory = $false)]
    [ValidateSet('build', 'start', 'stop', 'restart', 'logs', 'status', 'scale', 'down', 'ps', 'demo')]
    [string]$Action = 'start',
    
    [Parameter(Mandatory = $false)]
    [string]$Service = '',
    
    [Parameter(Mandatory = $false)]
    [int]$Replicas = 1,
    
    [Parameter(Mandatory = $false)]
    [string]$ProjectRoot = ''
)

# ========================================
# Configuration
# ========================================

if ([string]::IsNullOrEmpty($ProjectRoot)) {
    # Try to find the project root automatically
    $ProjectRoot = Get-Location
    if (-not (Test-Path "streamsocial/Dockerfile")) {
        # If Dockerfile not found, try to navigate up
        if (Test-Path "../streamsocial/Dockerfile") {
            $ProjectRoot = Resolve-Path ".."
        }
    }
}

$ComposeFile = Join-Path $ProjectRoot "streamsocial/Dockerfile"
$StackName = "streamsocial"

# Color outputs
$successColor = 'Green'
$errorColor = 'Red'
$infoColor = 'Cyan'
$warningColor = 'Yellow'

# ========================================
# Helper Functions
# ========================================

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $successColor
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $errorColor
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor $infoColor
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor $warningColor
}

function Test-Docker {
    try {
        docker --version | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Test-DockerCompose {
    try {
        docker compose version | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Test-ComposeFile {
    if (-not (Test-Path $ComposeFile)) {
        Write-Error-Custom "Docker Compose file not found: $ComposeFile"
        return $false
    }
    return $true
}

function Show-Header {
    Write-Host "`n╔════════════════════════════════════════════╗" -ForegroundColor $infoColor
    Write-Host "║  StreamSocial Docker Compose Manager     ║" -ForegroundColor $infoColor
    Write-Host "║  Kafka + Spring Boot Microservices       ║" -ForegroundColor $infoColor
    Write-Host "╚════════════════════════════════════════════╝`n" -ForegroundColor $infoColor
}

# ========================================
# Main Actions
# ========================================

function Start-Stack {
    Write-Info "Starting StreamSocial Stack..."
    Write-Info "Building and starting all services (Kafka cluster + Spring Boot apps)..."
    
    docker compose -f $ComposeFile up -d --build
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Stack started successfully"
        Write-Info "Waiting for services to be healthy..."
        Start-Sleep -Seconds 10
        Show-Status
    }
    else {
        Write-Error-Custom "Failed to start stack"
        exit 1
    }
}

function Build-Stack {
    Write-Info "Building services..."
    docker compose -f $ComposeFile build
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Build completed successfully"
    }
    else {
        Write-Error-Custom "Build failed"
        exit 1
    }
}

function Stop-Stack {
    Write-Info "Stopping StreamSocial Stack..."
    docker compose -f $ComposeFile down
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Stack stopped"
    }
    else {
        Write-Error-Custom "Failed to stop stack"
        exit 1
    }
}

function Restart-Stack {
    Write-Info "Restarting StreamSocial Stack..."
    docker compose -f $ComposeFile restart
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Stack restarted"
    }
    else {
        Write-Error-Custom "Failed to restart stack"
        exit 1
    }
}

function Show-Logs {
    if ([string]::IsNullOrEmpty($Service)) {
        Write-Info "Showing logs for all services..."
        docker compose -f $ComposeFile logs -f
    }
    else {
        Write-Info "Showing logs for service: $Service"
        docker compose -f $ComposeFile logs -f $Service
    }
}

function Show-Status {
    Write-Info "Current Stack Status:"
    Write-Host ""
    docker compose -f $ComposeFile ps
    Write-Host ""
}

function Show-Processes {
    Write-Info "Listing all containers:"
    docker compose -f $ComposeFile ps -a
}

function Scale-Service {
    if ([string]::IsNullOrEmpty($Service)) {
        Write-Error-Custom "Service name required for scale action"
        Write-Info "Example: .\manage-streamsocial.ps1 -Action scale -Service kafka-consumer -Replicas 3"
        exit 1
    }
    
    Write-Info "Scaling $Service to $Replicas replicas..."
    docker compose -f $ComposeFile up -d --scale $Service=$Replicas
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Service scaled to $Replicas replicas"
        Start-Sleep -Seconds 3
        Show-Status
    }
    else {
        Write-Error-Custom "Failed to scale service"
        exit 1
    }
}

function Run-Demo {
    Show-Header
    Write-Info "Starting StreamSocial Demo..."
    Write-Host ""
    
    # Start stack
    Write-Host "Step 1: Starting the stack..." -ForegroundColor $infoColor
    docker compose -f $ComposeFile up -d --build
    Write-Success "Stack starting (waiting for Kafka brokers to be healthy)..."
    Start-Sleep -Seconds 30
    
    # Show status
    Write-Host "`nStep 2: Stack Status:" -ForegroundColor $infoColor
    docker compose -f $ComposeFile ps
    
    # Generate events
    Write-Host "`nStep 3: Generating test events..." -ForegroundColor $infoColor
    Write-Info "Sending 100 test events to Kafka..."
    $ApiUrl = "http://localhost:8000/api/events/bulk/generate?count=100"
    
    try {
        $response = Invoke-WebRequest -Uri $ApiUrl -Method Post -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Success "Events generated successfully"
        }
        else {
            Write-Warning-Custom "API responded with status: $($response.StatusCode)"
        }
    }
    catch {
        Write-Warning-Custom "Could not reach API at $ApiUrl (API might still be starting)"
        Write-Info "Try again in a few seconds when the API is fully ready"
    }
    
    # Show Kafka UI
    Write-Host "`nStep 4: Access Services:" -ForegroundColor $infoColor
    Write-Info "Kafka UI:      http://localhost:8080"
    Write-Info "API Health:    http://localhost:8000/actuator/health"
    Write-Info "API Metrics:   http://localhost:8000/actuator/metrics"
    
    # Scale consumer
    Write-Host "`nStep 5: Scaling consumer workers..." -ForegroundColor $infoColor
    docker compose -f $ComposeFile up -d --scale kafka-consumer=3
    Write-Success "Scaled kafka-consumer to 3 replicas"
    
    # Show final status
    Write-Host "`nFinal Stack Status:" -ForegroundColor $infoColor
    docker compose -f $ComposeFile ps
    
    Write-Host "`n╔════════════════════════════════════════════╗" -ForegroundColor $successColor
    Write-Host "║  Demo Started Successfully!              ║" -ForegroundColor $successColor
    Write-Host "║                                          ║" -ForegroundColor $successColor
    Write-Host "║  Open Kafka UI to monitor:               ║" -ForegroundColor $successColor
    Write-Host "║  → http://localhost:8080                 ║" -ForegroundColor $successColor
    Write-Host "║                                          ║" -ForegroundColor $successColor
    Write-Host "║  API Endpoints:                          ║" -ForegroundColor $successColor
    Write-Host "║  → POST /api/events/bulk/generate        ║" -ForegroundColor $successColor
    Write-Host "║  → GET  /actuator/health                 ║" -ForegroundColor $successColor
    Write-Host "║  → GET  /actuator/metrics                ║" -ForegroundColor $successColor
    Write-Host "║                                          ║" -ForegroundColor $successColor
    Write-Host "║  View logs:                              ║" -ForegroundColor $successColor
    Write-Host "║  → .\manage-streamsocial.ps1 -Action logs║" -ForegroundColor $successColor
    Write-Host "║                                          ║" -ForegroundColor $successColor
    Write-Host "║  Stop stack:                             ║" -ForegroundColor $successColor
    Write-Host "║  → .\manage-streamsocial.ps1 -Action down║" -ForegroundColor $successColor
    Write-Host "╚════════════════════════════════════════════╝`n" -ForegroundColor $successColor
}

# ========================================
# Main Execution
# ========================================

# Show header
Show-Header

# Validate prerequisites
Write-Info "Validating prerequisites..."

if (-not (Test-Docker)) {
    Write-Error-Custom "Docker is not installed or not in PATH"
    Write-Info "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
}
Write-Success "Docker is installed"

if (-not (Test-DockerCompose)) {
    Write-Error-Custom "Docker Compose is not available"
    Write-Info "Please ensure Docker Desktop is updated (compose is included)"
    exit 1
}
Write-Success "Docker Compose is available"

if (-not (Test-ComposeFile)) {
    exit 1
}
Write-Success "Compose file found"

Write-Info "Project Root: $ProjectRoot"
Write-Info "Compose File: $ComposeFile"
Write-Host ""

# Execute requested action
switch ($Action) {
    'build' {
        Build-Stack
    }
    'start' {
        Start-Stack
    }
    'stop' {
        Stop-Stack
    }
    'restart' {
        Restart-Stack
    }
    'logs' {
        Show-Logs
    }
    'status' {
        Show-Status
    }
    'scale' {
        Scale-Service
    }
    'ps' {
        Show-Processes
    }
    'down' {
        Stop-Stack
    }
    'demo' {
        Run-Demo
    }
    default {
        Write-Error-Custom "Unknown action: $Action"
        exit 1
    }
}

Write-Host ""
Write-Success "Operation completed"
