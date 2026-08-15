# StreamSocial Docker Compose - Execution Scripts

Complete set of scripts to easily manage the StreamSocial Docker Compose stack (Kafka + Spring Boot microservices).

## 📋 Available Scripts

| Script | Platform | Type | Use Case |
|--------|----------|------|----------|
| **manage-streamsocial.ps1** | Windows (PowerShell) | Advanced | Full control with detailed options |
| **quick-run.ps1** | Windows (PowerShell) | Simple | Fast execution of common commands |
| **manage-streamsocial.bat** | Windows (cmd.exe) | Simple | Legacy cmd.exe support |
| **manage-streamsocial.sh** | Linux/Mac/WSL | Advanced | Full control, cross-platform |

---

## ⚡ Quick Start (Choose Your Platform)

### Windows - PowerShell (Recommended)

```powershell
# Terminal
cd C:\path\to\Kafka_Project

# Start everything
.\quick-run.ps1

# Or use advanced script
.\manage-streamsocial.ps1 -Action start
```

### Windows - Command Prompt (Legacy)

```batch
REM Command Prompt
cd C:\path\to\Kafka_Project

REM Start everything
manage-streamsocial.bat start

REM Or scale consumers
manage-streamsocial.bat scale 3
```

### Linux / Mac / WSL

```bash
# Bash/Shell
cd /path/to/Kafka_Project

# Make script executable
chmod +x manage-streamsocial.sh

# Start everything
./manage-streamsocial.sh start

# Or run demo
./manage-streamsocial.sh demo
```

---

## 🎯 Platform-Specific Guides

### 🪟 Windows - PowerShell Execution Policy

**First time setup:**

```powershell
# Allow local scripts to run (requires one-time setup)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or run script with explicit bypass
powershell -ExecutionPolicy Bypass -File .\manage-streamsocial.ps1 -Action start
```

**Then use normally:**

```powershell
# Start
.\quick-run.ps1

# Stop
.\quick-run.ps1 -stop

# Scale
.\quick-run.ps1 -scale 3
```

### 🪟 Windows - Command Prompt

**No setup needed - just run:**

```batch
manage-streamsocial.bat start
manage-streamsocial.bat scale 3
manage-streamsocial.bat stop
```

### 🐧 Linux / Mac / WSL

**First time setup:**

```bash
# Make executable
chmod +x manage-streamsocial.sh

# Run
./manage-streamsocial.sh start
```

---

## 📖 Complete Command Reference

### PowerShell - `manage-streamsocial.ps1`

**Full-featured, parameter-based commands:**

```powershell
# Start (default)
.\manage-streamsocial.ps1
.\manage-streamsocial.ps1 -Action start

# Build only
.\manage-streamsocial.ps1 -Action build

# Stop
.\manage-streamsocial.ps1 -Action stop

# View logs (all)
.\manage-streamsocial.ps1 -Action logs

# View logs (specific service)
.\manage-streamsocial.ps1 -Action logs -Service kafka-consumer
.\manage-streamsocial.ps1 -Action logs -Service backend-api

# Check status
.\manage-streamsocial.ps1 -Action status

# List containers
.\manage-streamsocial.ps1 -Action ps

# Restart services
.\manage-streamsocial.ps1 -Action restart

# Scale consumer
.\manage-streamsocial.ps1 -Action scale -Service kafka-consumer -Replicas 3

# Run demo
.\manage-streamsocial.ps1 -Action demo
```

### PowerShell - `quick-run.ps1`

**Simplified, flag-based commands:**

```powershell
# Start (default)
.\quick-run.ps1

# Stop
.\quick-run.ps1 -stop

# View logs
.\quick-run.ps1 -logs

# Check status
.\quick-run.ps1 -status

# Restart
.\quick-run.ps1 -restart

# Scale
.\quick-run.ps1 -scale 3

# Demo mode
.\quick-run.ps1 -demo
```

### Command Prompt - `manage-streamsocial.bat`

```batch
REM Start (default)
manage-streamsocial.bat
manage-streamsocial.bat start

REM Build only
manage-streamsocial.bat build

REM Stop
manage-streamsocial.bat stop

REM View logs
manage-streamsocial.bat logs

REM Check status
manage-streamsocial.bat status

REM List containers
manage-streamsocial.bat ps

REM Restart
manage-streamsocial.bat restart

REM Scale
manage-streamsocial.bat scale 3

REM Demo
manage-streamsocial.bat demo
```

### Bash/Shell - `manage-streamsocial.sh`

```bash
# Start (default)
./manage-streamsocial.sh
./manage-streamsocial.sh start

# Build only
./manage-streamsocial.sh build

# Stop
./manage-streamsocial.sh stop

# View logs (all)
./manage-streamsocial.sh logs

# View logs (specific service)
./manage-streamsocial.sh logs kafka-consumer
./manage-streamsocial.sh logs backend-api

# Check status
./manage-streamsocial.sh status

# List containers
./manage-streamsocial.sh ps

# Restart
./manage-streamsocial.sh restart

# Scale
./manage-streamsocial.sh scale 3

# Demo
./manage-streamsocial.sh demo

# Help
./manage-streamsocial.sh help
```

---

## 🚀 Common Workflows

### Workflow 1: Full Demo (All Platforms)

**PowerShell:**
```powershell
.\quick-run.ps1 -demo
# or
.\manage-streamsocial.ps1 -Action demo
```

**Command Prompt:**
```batch
manage-streamsocial.bat demo
```

**Bash:**
```bash
./manage-streamsocial.sh demo
```

### Workflow 2: Development Testing

**Terminal 1 - Start with logs:**
```powershell
# PowerShell
.\quick-run.ps1
.\quick-run.ps1 -logs

# or Cmd
manage-streamsocial.bat start
REM then in another terminal:
manage-streamsocial.bat logs

# or Bash
./manage-streamsocial.sh start
./manage-streamsocial.sh logs
```

**Terminal 2 - Generate events and test:**
```powershell
# Generate events
curl -X POST http://localhost:8000/api/events/bulk/generate?count=100

# Or from CMD
powershell -Command "Invoke-WebRequest -Uri 'http://localhost:8000/api/events/bulk/generate?count=100' -Method Post"

# Or from Bash
curl -X POST http://localhost:8000/api/events/bulk/generate?count=100
```

### Workflow 3: Load Test with Scaling

**PowerShell:**
```powershell
# Terminal 1: Start
.\quick-run.ps1

# Terminal 2: Generate load
for ($i = 0; $i -lt 10; $i++) {
    curl -X POST http://localhost:8000/api/events/bulk/generate?count=1000
    Start-Sleep -Seconds 5
}

# Terminal 1: Monitor in logs
# (already running in Terminal 1)

# Terminal 3: Scale when needed
.\quick-run.ps1 -scale 3
.\quick-run.ps1 -scale 5
```

**Bash:**
```bash
# Terminal 1: Start
./manage-streamsocial.sh start

# Terminal 2: Monitor logs
./manage-streamsocial.sh logs

# Terminal 3: Generate load
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/events/bulk/generate?count=1000
  sleep 5
done

# Terminal 4: Scale
./manage-streamsocial.sh scale 3
./manage-streamsocial.sh scale 5
```

### Workflow 4: Cleanup

**PowerShell:**
```powershell
.\quick-run.ps1 -stop
# or
.\manage-streamsocial.ps1 -Action stop
```

**Command Prompt:**
```batch
manage-streamsocial.bat stop
```

**Bash:**
```bash
./manage-streamsocial.sh stop
```

---

## 🌐 Service Access Points

Once running, access these endpoints:

| Service | URL | Purpose |
|---------|-----|---------|
| **Kafka UI** | http://localhost:8080 | Monitor Kafka cluster, topics, consumer lag |
| **API Health** | http://localhost:8000/actuator/health | Check API service status |
| **API Metrics** | http://localhost:8000/actuator/metrics | View metrics and performance data |
| **API Prometheus** | http://localhost:8000/actuator/prometheus | Prometheus-format metrics |
| **Generate Events** | POST http://localhost:8000/api/events/bulk/generate | Send test events to Kafka |

### Example Requests

**PowerShell:**
```powershell
# Generate 100 events
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/events/bulk/generate?count=100" -Method Post
$response.StatusCode

# Check health
Invoke-WebRequest -Uri "http://localhost:8000/actuator/health" -Method Get | ConvertFrom-Json
```

**Bash/cURL:**
```bash
# Generate 100 events
curl -X POST http://localhost:8000/api/events/bulk/generate?count=100

# Check health
curl http://localhost:8000/actuator/health | jq

# View metrics
curl http://localhost:8000/actuator/metrics | jq
```

---

## 🔧 Troubleshooting

### Script Not Found / Permission Denied

**PowerShell - Windows:**
```powershell
# Check execution policy
Get-ExecutionPolicy

# Allow script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run with explicit bypass
powershell -ExecutionPolicy Bypass -File .\quick-run.ps1
```

**Bash - Linux/Mac/WSL:**
```bash
# Check permissions
ls -la manage-streamsocial.sh

# Make executable
chmod +x manage-streamsocial.sh

# Run with explicit bash
bash manage-streamsocial.sh start
```

### Docker Compose Not Found

**All Platforms:**
```bash
# Verify Docker Compose is installed
docker compose version

# If not installed, update Docker Desktop to latest version
```

### Ports Already in Use

```powershell
# PowerShell - Find process using port 8000
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
tasklist /FI "PID eq <PID>"

# Kill the process
taskkill /PID <PID> /F
```

```bash
# Bash - Find process using ports
netstat -tlnp | grep :8000
netstat -tlnp | grep :8080

# Kill the process
kill -9 <PID>
```

### Services Stuck Restarting

```powershell
# PowerShell
.\quick-run.ps1 -stop
Start-Sleep -Seconds 5
.\quick-run.ps1

# Bash
./manage-streamsocial.sh stop
sleep 5
./manage-streamsocial.sh start
```

---

## 📊 Script Feature Comparison

| Feature | manage-streamsocial.ps1 | quick-run.ps1 | manage-streamsocial.bat | manage-streamsocial.sh |
|---------|-------------------------|---------------|------------------------|----------------------|
| **Syntax** | Parameter-based | Flag-based | Action-based | Action-based |
| **Start** | ✓ | ✓ | ✓ | ✓ |
| **Build** | ✓ | ✗ | ✓ | ✓ |
| **Stop** | ✓ | ✓ | ✓ | ✓ |
| **Logs** | ✓ (with service filter) | ✓ | ✓ | ✓ (with service filter) |
| **Scale** | ✓ (advanced) | ✓ | ✓ | ✓ |
| **Demo** | ✓ | ✓ | ✓ | ✓ |
| **Status** | ✓ | ✓ | ✓ | ✓ |
| **Restart** | ✓ | ✓ | ✓ | ✓ |
| **Color Output** | ✓ | ✓ | ✓ | ✓ |
| **Error Handling** | Comprehensive | Basic | Basic | Comprehensive |
| **Help** | Built-in validation | Hints | Help action | Help action |

---

## 🎯 Choose Your Script

### Use `quick-run.ps1` if:
- ✓ You're on Windows with PowerShell
- ✓ You want simplicity
- ✓ You prefer flags over parameters
- ✓ You use common commands frequently

### Use `manage-streamsocial.ps1` if:
- ✓ You're on Windows with PowerShell
- ✓ You want full control
- ✓ You prefer structured parameters
- ✓ You need detailed error messages

### Use `manage-streamsocial.bat` if:
- ✓ You're on Windows with Command Prompt
- ✓ You can't use PowerShell
- ✓ You prefer legacy cmd.exe

### Use `manage-streamsocial.sh` if:
- ✓ You're on Linux, Mac, or WSL
- ✓ You want cross-platform compatibility
- ✓ You need full-featured control

---

## 📝 Next Steps

1. **Choose your platform** from the options above
2. **Run your first command**: `start` or `quick-run.ps1`
3. **Wait 30 seconds** for services to be healthy
4. **Access Kafka UI**: http://localhost:8080
5. **Generate events**: Use the API endpoint
6. **Monitor**: Watch consumer processing in logs
7. **Scale**: Increase consumer replicas to test horizontal scaling
8. **Cleanup**: Stop the stack when done

---

## 📞 Need Help?

Each script includes:
- ✓ Automatic validation of prerequisites
- ✓ Color-coded output (success/error/info)
- ✓ Helpful error messages
- ✓ Status indicators
- ✓ Built-in help/documentation

See [POWERSHELL_SCRIPTS_GUIDE.md](POWERSHELL_SCRIPTS_GUIDE.md) for detailed documentation of PowerShell scripts.
