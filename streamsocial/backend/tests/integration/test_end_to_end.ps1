# StreamSocial integration / end-to-end API test suite (Windows PowerShell).
# Prerequisites: stack running (.\setup_python.ps1 from repo root).
#
# Usage:
#   .\test_end_to_end.ps1              # all suites
#   .\test_end_to_end.ps1 -Suite health
#   .\test_end_to_end.ps1 -Suite event
#   .\test_end_to_end.ps1 -Suite consumer
#   .\test_end_to_end.ps1 -Suite metrics
#   .\test_end_to_end.ps1 -Suite cluster
#   .\test_end_to_end.ps1 -Suite scale        # produce + lag observation (needs live Kafka)
#   .\test_end_to_end.ps1 -Help

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Args,
    [string]$Suite = "all",
    [switch]$Help
)

$ErrorActionPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Get-Item $ScriptDir).Parent.Parent.Parent.Parent.FullName
$BaseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost:8000" }

# Colors (ANSI escape codes)
$GREEN = "`e[0;32m"
$BLUE = "`e[0;34m"
$YELLOW = "`e[1;33m"
$CYAN = "`e[0;36m"
$RED = "`e[0;31m"
$NC = "`e[0m"

$TESTS_PASSED = 0
$TESTS_FAILED = 0
$TESTS_SKIPPED = 0

function Section {
    param([string]$Message)
    Write-Host ""
    Write-Host "$BLUE▶ $Message$NC"
}

function Info {
    param([string]$Message)
    Write-Host "$YELLOW[INFO]$NC $Message"
}

function Success {
    param([string]$Message)
    Write-Host "$GREEN[OK]$NC $Message"
    $script:TESTS_PASSED++
}

function Error-Log {
    param([string]$Message)
    Write-Host "$RED[ERROR]$NC $Message"
    $script:TESTS_FAILED++
}

function Skip-Test {
    param([string]$Message)
    Write-Host "$YELLOW[SKIP]$NC $Message"
    $script:TESTS_SKIPPED++
}

function Need-Jq {
    if (-not (Get-Command jq -ErrorAction SilentlyContinue)) {
        Error-Log "jq is required for integration tests (choco install jq / scoop install jq)"
        exit 1
    }
}

function Need-Curl {
    if (-not (Get-Command curl -ErrorAction SilentlyContinue)) {
        Error-Log "curl is required but not found"
        exit 1
    }
}

# HTTP helpers: set $RESPONSE, $HTTP_CODE
function Http-Get {
    param([string]$Url)
    
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -ErrorAction SilentlyContinue
        $script:HTTP_CODE = $response.StatusCode
        $script:RESPONSE = $response.Content
    }
    catch {
        if ($_.Exception.Response) {
            $script:HTTP_CODE = $_.Exception.Response.StatusCode.Value__
        } else {
            $script:HTTP_CODE = 0
        }
        $script:RESPONSE = ""
    }
}

function Http-Post-Json {
    param([string]$Url, [string]$Body)
    
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Post -Body $Body -ContentType "application/json" -ErrorAction SilentlyContinue
        $script:HTTP_CODE = $response.StatusCode
        $script:RESPONSE = $response.Content
    }
    catch {
        if ($_.Exception.Response) {
            $script:HTTP_CODE = $_.Exception.Response.StatusCode.Value__
        } else {
            $script:HTTP_CODE = 0
        }
        $script:RESPONSE = ""
    }
}

function Assert-Http-Ok {
    param([string]$Name)
    
    if ($HTTP_CODE -eq 200 -or $HTTP_CODE -eq 201 -or $HTTP_CODE -eq 202) {
        Success "$Name (HTTP $HTTP_CODE)"
        return $true
    }
    
    Error-Log "$Name (HTTP $HTTP_CODE)"
    if ($RESPONSE) {
        try {
            $RESPONSE | ConvertFrom-Json | ConvertTo-Json
        }
        catch {
            $RESPONSE
        }
    }
    return $false
}

function Assert-Jq {
    param([string]$Name, [string]$Expr)
    
    if (-not $RESPONSE) {
        Error-Log "$Name (empty response)"
        return $false
    }
    
    try {
        $json = $RESPONSE | ConvertFrom-Json
        
        # Simple PowerShell native JSON assertions (no jq needed)
        # Handle common patterns like: has("field"), .field == "value", .field != null
        
        # Check for .field == "value" or .field == "value" or pattern
        if ($Expr -match '\.([a-zA-Z_]\w*)\s*==\s*true\s+or\s+\.([a-zA-Z_]\w*)\s*==\s*"([^"]*)"\s+or\s+\.([a-zA-Z_]\w*)\s*!=\s*null') {
            $field1 = $matches[1]
            $field2 = $matches[2]
            $value2 = $matches[3]
            $field3 = $matches[4]
            if ($json.$field1 -eq $true -or $json.$field2 -eq $value2 -or $null -ne $json.$field3) {
                Success $Name
                return $true
            }
        }
        # Check for .field == "value" pattern
        elseif ($Expr -match '\.([a-zA-Z_]\w*)\s*==\s*"([^"]*)"') {
            $field = $matches[1]
            $expectedValue = $matches[2]
            $actualValue = $json.$field
            if ($actualValue -eq $expectedValue) {
                Success $Name
                return $true
            }
        }
        # Check for .field == true pattern
        elseif ($Expr -match '\.([a-zA-Z_]\w*)\s*==\s*true') {
            $field = $matches[1]
            if ($json.$field -eq $true) {
                Success $Name
                return $true
            }
        }
        # Check for 'has' pattern: has("fieldname")
        elseif ($Expr -match 'has\("([^"]+)"\)') {
            $field = $matches[1]
            if ($json | Get-Member -Name $field -ErrorAction SilentlyContinue) {
                Success $Name
                return $true
            }
        }
        # Check for null comparison: .field != null, .field == null
        elseif ($Expr -match '\.([a-zA-Z_]\w*)\s*(!=|==)\s*null') {
            $field = $matches[1]
            $operator = $matches[2]
            $value = $json.$field
            
            if ($operator -eq "!=") {
                if ($null -ne $value) {
                    Success $Name
                    return $true
                }
            }
            elseif ($operator -eq "==") {
                if ($null -eq $value) {
                    Success $Name
                    return $true
                }
            }
        }
        # Check for 'or' patterns with has()
        elseif ($Expr -match 'has\("([^"]+)"\)\s+or\s+has\("([^"]+)"\)\s+or\s+has\("([^"]+)"\)') {
            $field1 = $matches[1]
            $field2 = $matches[2]
            $field3 = $matches[3]
            if (($json | Get-Member -Name $field1 -ErrorAction SilentlyContinue) -or
                ($json | Get-Member -Name $field2 -ErrorAction SilentlyContinue) -or
                ($json | Get-Member -Name $field3 -ErrorAction SilentlyContinue)) {
                Success $Name
                return $true
            }
        }
        # Check for 'or' patterns with has()
        elseif ($Expr -match 'has\("([^"]+)"\)\s+or\s+has\("([^"]+)"\)') {
            $field1 = $matches[1]
            $field2 = $matches[2]
            if (($json | Get-Member -Name $field1 -ErrorAction SilentlyContinue) -or
                ($json | Get-Member -Name $field2 -ErrorAction SilentlyContinue)) {
                Success $Name
                return $true
            }
        }
        # Default: try jq if available
        else {
            if (Get-Command jq -ErrorAction SilentlyContinue) {
                $result = $json | ConvertTo-Json | jq -e $Expr 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Success $Name
                    return $true
                }
            }
        }
    }
    catch {
        # Continue to error
    }
    
    Error-Log "$Name (expr: $Expr)"
    try {
        $RESPONSE | ConvertFrom-Json | ConvertTo-Json
    }
    catch {
        $RESPONSE
    }
    return $false
}

# ── Health ──────────────────────────────────────────────────────────
function Test-Health-Check {
    Section "GET /health"
    Http-Get "$BaseUrl/health"
    if (-not (Assert-Http-Ok "health reachable")) { return }
    Assert-Jq "status healthy" '.status == "healthy"' | Out-Null
    try {
        $RESPONSE | ConvertFrom-Json | Select-Object status, service, timestamp | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Root-Endpoint {
    Section "GET /"
    Http-Get "$BaseUrl/"
    if (-not (Assert-Http-Ok "root reachable")) { return }
    Assert-Jq "service present" '.service != null' | Out-Null
    try {
        $RESPONSE | ConvertFrom-Json | Select-Object service, version, consumer_mode, consumer_group_id, demo | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Health-Controller {
    Write-Host "$CYAN══ HEALTH ══$NC"
    Test-Health-Check
    Test-Root-Endpoint
}

# ── Events ──────────────────────────────────────────────────────────
function Test-Register-User {
    Section "POST /events/user/register"
    $users = @("alice", "bob", "charlie")
    $emails = @("alice@example.com", "bob@example.com", "charlie@example.com")
    
    for ($i = 0; $i -lt $users.Count; $i++) {
        $body = @{
            username = $users[$i]
            email = $emails[$i]
            source = "e2e"
        } | ConvertTo-Json
        
        Http-Post-Json "$BaseUrl/events/user/register" $body
        
        if (Assert-Http-Ok "register $($users[$i])") {
            try {
                $json = $RESPONSE | ConvertFrom-Json
                if ($json.success -eq $true) {
                    Success "publish ok user=$($users[$i])"
                }
                else {
                    Error-Log "register body not success for $($users[$i])"
                    $json | ConvertTo-Json | Write-Host
                }
            }
            catch {
                $RESPONSE | Write-Host
            }
        }
        Start-Sleep -Milliseconds 200
    }
}

function Test-Get-Recent-Events {
    Section "GET /events/recent"
    Http-Get "$BaseUrl/events/recent"
    if (-not (Assert-Http-Ok "recent events")) { return }
    Assert-Jq "payload has success or events" 'has("success") or has("events") or has("count")' | Out-Null
    try {
        $json = $RESPONSE | ConvertFrom-Json
        @{
            success = $json.success
            count = $json.count
            message = $json.message
            events_in_memory = $json.events_in_memory
        } | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Bulk-Generate-Short {
    Section "POST /events/bulk/generate (short background load)"
    $body = @{
        events_per_second = 200
        duration_seconds = 5
        background = $true
    } | ConvertTo-Json
    
    Http-Post-Json "$BaseUrl/events/bulk/generate" $body
    if (-not (Assert-Http-Ok "bulk generate accepted")) { return }
    Assert-Jq "bulk started or configured" '.success == true or .status == "started" or .config != null' | Out-Null
    try {
        $json = $RESPONSE | ConvertFrom-Json
        @{
            success = $json.success
            message = $json.message
            config = $json.config
            observe_lag = $json.observe_lag
        } | ConvertTo-Json | Write-Host
    }
    catch { }
    
    Section "GET /events/bulk/status"
    Http-Get "$BaseUrl/events/bulk/status"
    if (-not (Assert-Http-Ok "bulk status")) { return }
    try {
        $RESPONSE | ConvertFrom-Json | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Event-Controller {
    Write-Host "$CYAN══ EVENT ══$NC"
    Test-Register-User
    Test-Get-Recent-Events
    Test-Bulk-Generate-Short
}

# ── Consumer ────────────────────────────────────────────────────────
function Test-Consumer-Stats {
    Section "GET /consumer/stats"
    Http-Get "$BaseUrl/consumer/stats"
    if (-not (Assert-Http-Ok "consumer stats")) { return }
    Assert-Jq "has status" 'has("status")' | Out-Null
    try {
        $json = $RESPONSE | ConvertFrom-Json
        @{
            status = $json.status
            mode = $json.mode
            group_id = $json.group_id
            total_lag = $json.total_lag
            scale_hint = $json.scale_hint
        } | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Consumer-Lag {
    Section "GET /consumer/lag"
    Http-Get "$BaseUrl/consumer/lag"
    if (-not (Assert-Http-Ok "consumer lag HTTP")) { return }
    Assert-Jq "has group_id or total_lag" 'has("group_id") or has("total_lag")' | Out-Null
    
    try {
        $json = $RESPONSE | ConvertFrom-Json
        if ($json.error -and $json.error -ne "") {
            Error-Log "consumer lag reported error: $($json.error)"
            @{
                group_id = $json.group_id
                total_lag = $json.total_lag
                error = $json.error
                source = $json.source
            } | ConvertTo-Json | Write-Host
        }
        else {
            Success "consumer lag payload has no error"
            @{
                group_id = $json.group_id
                total_lag = $json.total_lag
                partition_count = $json.partition_count
                lag_by_topic = $json.lag_by_topic
                source = $json.source
            } | ConvertTo-Json | Write-Host
        }
    }
    catch { }
}

function Test-Consumer-Instances {
    Section "GET /consumer/instances"
    Http-Get "$BaseUrl/consumer/instances"
    if (-not (Assert-Http-Ok "consumer instances")) { return }
    try {
        $json = $RESPONSE | ConvertFrom-Json
        @{
            total_in_process_instances = $json.total_in_process_instances
            group_id = $json.group_id
            note = $json.note
        } | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Consumer-Health {
    Section "GET /consumer/health"
    Http-Get "$BaseUrl/consumer/health"
    if (-not (Assert-Http-Ok "consumer health")) { return }
    try {
        $RESPONSE | ConvertFrom-Json | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Consumer-Start-Disabled {
    Section "POST /consumer/start (compose mode: expect disabled)"
    $body = "{}" 
    Http-Post-Json "$BaseUrl/consumer/start" $body
    if (-not (Assert-Http-Ok "start endpoint responds")) { return }
    
    try {
        $json = $RESPONSE | ConvertFrom-Json
        if ($json.status -eq "disabled" -or $json.status -eq "started" -or $json.status -eq "already_running") {
            Success "start status acceptable: $($json.status)"
        }
        else {
            Error-Log "unexpected start status"
            $json | ConvertTo-Json | Write-Host
        }
        @{
            status = $json.status
            message = $json.message
            group_id = $json.group_id
        } | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Consumer-Stop {
    Section "POST /consumer/stop"
    $body = "{}"
    Http-Post-Json "$BaseUrl/consumer/stop" $body
    if (-not (Assert-Http-Ok "stop endpoint responds")) { return }
    try {
        $json = $RESPONSE | ConvertFrom-Json
        @{
            status = $json.status
            message = $json.message
        } | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Consumer-Controller {
    Write-Host "$CYAN══ CONSUMER ══$NC"
    Test-Consumer-Stats
    Test-Consumer-Lag
    Test-Consumer-Instances
    Test-Consumer-Health
    Test-Consumer-Start-Disabled
    Test-Consumer-Stop
}

# ── Metrics ─────────────────────────────────────────────────────────
function Test-Metrics {
    Section "GET /metrics"
    Http-Get "$BaseUrl/metrics"
    if (-not (Assert-Http-Ok "metrics")) { return }
    Assert-Jq "has total_lag or group_id" 'has("total_lag") or has("group_id") or has("consumer_group_id")' | Out-Null
    
    try {
        $json = $RESPONSE | ConvertFrom-Json
        if ($json.error -and $json.error -ne "") {
            Error-Log "metrics lag error: $($json.error)"
        }
        else {
            Success "metrics payload has no error"
        }
        @{
            group_id = $json.group_id
            consumer_group_id = $json.consumer_group_id
            total_lag = $json.total_lag
            error = $json.error
            demo = $json.demo
        } | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Metrics-Lag {
    Section "GET /metrics/lag"
    Http-Get "$BaseUrl/metrics/lag"
    if (-not (Assert-Http-Ok "metrics/lag")) { return }
    try {
        $json = $RESPONSE | ConvertFrom-Json
        @{
            group_id = $json.group_id
            total_lag = $json.total_lag
            error = $json.error
        } | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Metrics-Suite {
    Write-Host "$CYAN══ METRICS ══$NC"
    Test-Metrics
    Test-Metrics-Lag
}

# ── Cluster ─────────────────────────────────────────────────────────
function Test-Cluster-Health {
    Section "GET /cluster/health"
    Http-Get "$BaseUrl/cluster/health"
    if (-not (Assert-Http-Ok "cluster health")) { return }
    Assert-Jq "has status" 'has("status")' | Out-Null
    try {
        $json = $RESPONSE | ConvertFrom-Json
        @{
            status = $json.status
            healthy_count = $json.healthy_count
            total_brokers = $json.total_brokers
            ops_enabled = $json.ops_enabled
        } | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Cluster-Metadata {
    Section "GET /cluster/metadata"
    Http-Get "$BaseUrl/cluster/metadata"
    if (-not (Assert-Http-Ok "cluster metadata")) { return }
    try {
        $json = $RESPONSE | ConvertFrom-Json
        @{
            topic = $json.topic
            brokers = ($json.brokers.Count)
            bootstrap_servers = $json.bootstrap_servers
            replication_factor = $json.replication_factor
            error = $json.error
        } | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Cluster-Partitions {
    Section "GET /cluster/partitions"
    Http-Get "$BaseUrl/cluster/partitions"
    if (-not (Assert-Http-Ok "cluster partitions")) { return }
    try {
        $json = $RESPONSE | ConvertFrom-Json
        @{
            topic = $json.topic
            partition_details_count = ($json.partition_details.Count)
            error = $json.error
        } | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Cluster-Consumer-Lag {
    Section "GET /cluster/consumer-lag"
    Http-Get "$BaseUrl/cluster/consumer-lag"
    if (-not (Assert-Http-Ok "cluster consumer-lag")) { return }
    try {
        $json = $RESPONSE | ConvertFrom-Json
        @{
            consumer_group = $json.consumer_group
            group_id = $json.group_id
            total_lag = $json.total_lag
            error = $json.error
        } | ConvertTo-Json | Write-Host
    }
    catch { }
}

function Test-Cluster-Failure-Ops {
    Section "POST /cluster/simulate-failure + recover (optional)"
    
    $body = @{
        broker_name = "kafka-broker-2"
    } | ConvertTo-Json
    
    Http-Post-Json "$BaseUrl/cluster/simulate-failure" $body
    if ($HTTP_CODE -ne 200) {
        Skip-Test "simulate-failure not available (HTTP $HTTP_CODE) -- enable CLUSTER_OPS_ENABLED if needed"
        return
    }
    
    try {
        $json = $RESPONSE | ConvertFrom-Json
        if ($json.status -eq "disabled" -or $json.enabled -eq $false -or $json.ops_enabled -eq $false) {
            Skip-Test "cluster ops disabled: $($json.message)"
            return
        }
        
        if ($json.status) {
            Success "simulate-failure responded"
            @{
                status = $json.status
                broker = $json.broker
                action = $json.action
                message = $json.message
            } | ConvertTo-Json | Write-Host
        }
        else {
            Error-Log "simulate-failure unexpected body"
            $json | ConvertTo-Json | Write-Host
            return
        }
    }
    catch { }
    
    Start-Sleep -Seconds 2
    
    $body = @{
        broker_name = "kafka-broker-2"
    } | ConvertTo-Json
    
    Http-Post-Json "$BaseUrl/cluster/recover-failure" $body
    if (Assert-Http-Ok "recover-failure") {
        try {
            $json = $RESPONSE | ConvertFrom-Json
            @{
                status = $json.status
                broker = $json.broker
                action = $json.action
            } | ConvertTo-Json | Write-Host
        }
        catch { }
    }
}

function Test-Cluster-Controller {
    Write-Host "$CYAN══ CLUSTER ══$NC"
    Test-Cluster-Health
    Test-Cluster-Metadata
    Test-Cluster-Partitions
    Test-Cluster-Consumer-Lag
    Test-Cluster-Failure-Ops
}

# ── Scale / lag narrative ───────────────────────────────────────────
function Test-Scale-Narrative {
    Write-Host "$CYAN══ SCALE / LAG NARRATIVE ══$NC"
    
    Section "Baseline lag"
    Http-Get "$BaseUrl/consumer/lag"
    if (-not (Assert-Http-Ok "baseline lag")) { return }
    
    try {
        $json = $RESPONSE | ConvertFrom-Json
        $lagBefore = $json.total_lag -as [int]
        if ($null -eq $lagBefore) { $lagBefore = 0 }
        Info "total_lag before load: $lagBefore"
        
        if ($json.error -and $json.error -ne "") {
            Error-Log "lag API error blocks scale narrative: $($json.error)"
            Info "Worker logs may still show lag_report; fix lag probe config and rebuild API."
        }
    }
    catch { }
    
    Section "Produce background load"
    $body = @{
        events_per_second = 1500
        duration_seconds = 15
        background = $true
    } | ConvertTo-Json
    
    Http-Post-Json "$BaseUrl/events/bulk/generate" $body
    if (-not (Assert-Http-Ok "loadgen started")) { return }
    Success "load generation requested"
    try {
        $json = $RESPONSE | ConvertFrom-Json
        @{
            success = $json.success
            message = $json.message
            config = $json.config
        } | ConvertTo-Json | Write-Host
    }
    catch { }
    
    Info "Waiting 12s for produce/consume..."
    Start-Sleep -Seconds 12
    
    Section "Lag after load"
    Http-Get "$BaseUrl/metrics"
    if (-not (Assert-Http-Ok "metrics after load")) { return }
    try {
        $json = $RESPONSE | ConvertFrom-Json
        $lagAfter = $json.total_lag -as [int]
        if ($null -eq $lagAfter) { $lagAfter = 0 }
        Info "total_lag after load (API): $lagAfter"
        @{
            total_lag = $json.total_lag
            error = $json.error
            consumer_group_id = $json.consumer_group_id
            demo = $json.demo
        } | ConvertTo-Json | Write-Host
    }
    catch { }
    
    Section "Compose consumer scale hint"
    Info "Scale command: docker compose -f $RepoRoot/docker-compose.yml up -d --scale kafka-consumer=3"
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $consumers = docker ps --filter "name=kafka-consumer" --format "{{.Names}}" 2>$null | Measure-Object -Line
        $n = $consumers.Lines
        Info "running kafka-consumer containers: $n"
        if ($n -ge 1) {
            Success "at least one kafka-consumer container is running"
        }
        else {
            Error-Log "no kafka-consumer containers found -- start stack with .\setup_python.ps1"
        }
    }
    else {
        Skip-Test "docker not available to count consumers"
    }
}

function Test-All {
    Write-Host "$CYAN"
    Write-Host "==============================================================="
    Write-Host "  StreamSocial Integration Test Suite (PowerShell)              "
    Write-Host "  Base URL: $BaseUrl"
    Write-Host "==============================================================="
    Write-Host "$NC"
    Test-Health-Controller
    Test-Event-Controller
    Test-Consumer-Controller
    Test-Metrics-Suite
    Test-Cluster-Controller
    Test-Scale-Narrative
}

function Show-Help {
    Write-Host "$CYANStreamSocial integration tests (PowerShell)$NC"
    Write-Host ""
    Write-Host "Prerequisites:"
    Write-Host "  From repo root: .\setup_python.ps1"
    Write-Host "  API must answer $BaseUrl/health"
    Write-Host ""
    Write-Host "Usage: .\test_end_to_end.ps1 [-Suite SUITE]"
    Write-Host "  -Suite all|health|event|consumer|metrics|cluster|scale"
    Write-Host "  -Help                Show this message"
    Write-Host ""
    Write-Host "Suites:"
    Write-Host "  all       Full suite"
    Write-Host "  health    Health + root"
    Write-Host "  event     Register, recent, bulk generate"
    Write-Host "  consumer  Stats, lag, instances, start/stop"
    Write-Host "  metrics   /metrics and /metrics/lag"
    Write-Host "  cluster   Cluster endpoints (+ optional failure ops)"
    Write-Host "  scale     Produce + lag observation narrative"
    Write-Host ""
    Write-Host "Env: BASE_URL (default http://localhost:8000)"
}

function Verify-Backend {
    Section "Verifying backend at $BaseUrl"
    Need-Curl
    
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/health" -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Success "Backend is running"
        }
        else {
            throw "Status code $($response.StatusCode)"
        }
    }
    catch {
        Error-Log "Backend is NOT reachable at $BaseUrl"
        Write-Host ""
        Write-Host "$YELLOWStart the app first:$NC"
        Write-Host "  cd $RepoRoot"
        Write-Host "  .\setup_python.ps1"
        Write-Host "  # or: .\setup_python.ps1 -StartOnly"
        Write-Host ""
        exit 1
    }
}

function Print-Summary {
    Write-Host ""
    Write-Host "$CYAN===============================================================$NC"
    Write-Host "$CYAN  TEST RESULTS SUMMARY$NC"
    Write-Host "$CYAN===============================================================$NC"
    Write-Host "$GREEN[PASSED]:  $TESTS_PASSED$NC"
    Write-Host "$RED[FAILED]:  $TESTS_FAILED$NC"
    Write-Host "$YELLOW[SKIPPED]: $TESTS_SKIPPED$NC"
    Write-Host ""
    
    if ($TESTS_FAILED -gt 0) {
        exit 1
    }
    exit 0
}

# Parse suite argument
if ($Help) {
    Show-Help
    exit 0
}

# Handle positional arguments if passed
if ($Args.Count -gt 0) {
    $Suite = $Args[0]
}

# Main execution
switch ($Suite.ToLower()) {
    "health" {
        Verify-Backend
        Test-Health-Controller
        Print-Summary
    }
    "event" {
        Verify-Backend
        Test-Event-Controller
        Print-Summary
    }
    "consumer" {
        Verify-Backend
        Test-Consumer-Controller
        Print-Summary
    }
    "metrics" {
        Verify-Backend
        Test-Metrics-Suite
        Print-Summary
    }
    "cluster" {
        Verify-Backend
        Test-Cluster-Controller
        Print-Summary
    }
    "scale" {
        Verify-Backend
        Test-Scale-Narrative
        Print-Summary
    }
    "all" {
        Verify-Backend
        Test-All
        Print-Summary
    }
    "list" {
        Show-Help
        exit 0
    }
    default {
        Write-Host "$RED[ERROR] Unknown suite: $Suite$NC"
        Show-Help
        exit 1
    }
}
