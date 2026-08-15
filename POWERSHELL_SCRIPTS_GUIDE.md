# StreamSocial Docker Compose - PowerShell Scripts Guide

## 📋 Overview

Two PowerShell scripts are provided to manage the StreamSocial Docker Compose stack:

1. **`manage-streamsocial.ps1`** - Full-featured orchestration script with detailed controls
2. **`quick-run.ps1`** - Simplified script for common operations

Both scripts manage:
- 3-broker Kafka cluster (KRaft mode)
- Kafka UI (monitoring dashboard)
- Spring Boot API service (port 8000)
- Scalable consumer workers

---

## ⚡ Quick Start

### Fastest Way to Start

```powershell
# Run from project root
.\quick-run.ps1
```

This will:
1. Build the Docker images
2. Start all services
3. Wait for Kafka brokers to be healthy
4. Show status
5. Display quick command hints

### Start with Full Demo

```powershell
.\quick-run.ps1 -demo
```

This will:
1. Start the stack
2. Generate 100 test events
3. Scale consumer to 3 instances
4. Show access points

---

## 🛠️ Available Scripts & Commands

### Script 1: `manage-streamsocial.ps1` (Advanced)

**Syntax:**
```powershell
.\manage-streamsocial.ps1 -Action <action> [-Service <name>] [-Replicas <count>]
```

**Actions:**

| Action | Description | Example |
|--------|-------------|---------|
| `start` (default) | Build and start all services | `.\manage-streamsocial.ps1 -Action start` |
| `build` | Build Docker images only | `.\manage-streamsocial.ps1 -Action build` |
| `stop` | Stop and remove containers | `.\manage-streamsocial.ps1 -Action stop` |
| `restart` | Restart running containers | `.\manage-streamsocial.ps1 -Action restart` |
| `logs` | View logs (all or specific service) | `.\manage-streamsocial.ps1 -Action logs -Service kafka-consumer` |
| `status` | Show running containers status | `.\manage-streamsocial.ps1 -Action status` |
| `ps` | List all containers | `.\manage-streamsocial.ps1 -Action ps` |
| `scale` | Scale service to N replicas | `.\manage-streamsocial.ps1 -Action scale -Service kafka-consumer -Replicas 5` |
| `down` | Stop and remove everything | `.\manage-streamsocial.ps1 -Action down` |
| `demo` | Run full interactive demo | `.\manage-streamsocial.ps1 -Action demo` |

**Examples:**

```powershell
# Start with automatic build
.\manage-streamsocial.ps1 -Action start

# Build only (useful before pushing to registry)
.\manage-streamsocial.ps1 -Action build

# View producer logs
.\manage-streamsocial.ps1 -Action logs -Service backend-api

# View consumer logs
.\manage-streamsocial.ps1 -Action logs -Service kafka-consumer

# Scale consumer to 5 instances
.\manage-streamsocial.ps1 -Action scale -Service kafka-consumer -Replicas 5

# View all containers
.\manage-streamsocial.ps1 -Action ps

# Run interactive demo
.\manage-streamsocial.ps1 -Action demo

# Stop everything
.\manage-streamsocial.ps1 -Action stop
```

---

### Script 2: `quick-run.ps1` (Simple)

**Syntax:**
```powershell
.\quick-run.ps1 [-stop] [-logs] [-status] [-restart] [-scale <n>] [-demo]
```

**Flags:**

| Flag | Description |
|------|-------------|
| (none) | Start stack with build |
| `-stop` | Stop the stack |
| `-logs` | View live logs |
| `-status` | Show stack status |
| `-restart` | Restart services |
| `-scale 3` | Scale consumer to 3 instances |
| `-demo` | Run full demo mode |

**Examples:**

```powershell
# Start (default)
.\quick-run.ps1

# Stop
.\quick-run.ps1 -stop

# View logs
.\quick-run.ps1 -logs

# Check status
.\quick-run.ps1 -status

# Scale to 3 consumers
.\quick-run.ps1 -scale 3

# Run demo
.\quick-run.ps1 -demo
```

---

## 🚀 Common Workflows

### Workflow 1: First-Time Setup & Demo

```powershell
# Terminal 1: Start everything
.\quick-run.ps1 -demo

# Wait for services to start (30 seconds)
# Then open browser: http://localhost:8080 (Kafka UI)
```

### Workflow 2: Development Testing

```powershell
# Terminal 1: Start with logs
.\quick-run.ps1
.\quick-run.ps1 -logs

# Terminal 2: In another PowerShell window, generate events
curl -X POST http://localhost:8000/api/events/bulk/generate?count=100

# Terminal 1: Watch consumer processing in logs
# (Consumer logs will show in the logs output)
```

### Workflow 3: Load Testing with Scaling

```powershell
# Terminal 1: Start stack
.\quick-run.ps1

# Terminal 2: Monitor Kafka UI
# Open: http://localhost:8080

# Terminal 3: Generate events and scale
# Generate initial load
curl -X POST http://localhost:8000/api/events/bulk/generate?count=1000

# Monitor lag in Kafka UI...
# Then scale consumer
.\quick-run.ps1 -scale 3

# Watch lag decrease as more consumers join
# Continue generating events
curl -X POST http://localhost:8000/api/events/bulk/generate?count=5000

# Keep monitoring until lag drains
```

### Workflow 4: Cleanup

```powershell
# Stop everything
.\quick-run.ps1 -stop

# Or use
.\manage-streamsocial.ps1 -Action down

# Verify nothing is running
docker compose -f streamsocial/Dockerfile ps
```

---

## 📊 Service Endpoints & Monitoring

### API Service (Producer)
- **Base URL**: `http://localhost:8000/api`
- **Generate Events**: `POST /events/bulk/generate?count=100`
- **Health Check**: `GET /actuator/health`
- **Metrics**: `GET /actuator/metrics`
- **Prometheus**: `GET /actuator/prometheus`

### Kafka UI (Monitoring)
- **URL**: `http://localhost:8080`
- **Features**: Cluster overview, topic inspection, consumer groups, lag monitoring

### Kafka Brokers (Internal)
- **Internal**: `kafka-1:29092, kafka-2:29092, kafka-3:29092`
- **External**: `localhost:9092, localhost:9093, localhost:9094`

---

## 🐛 Troubleshooting

### Issue: "Docker Compose not found"
**Solution**: Ensure Docker Desktop is installed and running
```powershell
# Verify installation
docker compose version
```

### Issue: "Compose file not found"
**Solution**: Run scripts from project root directory
```powershell
cd c:\Users\YourUser\...\Kafka_Project
.\quick-run.ps1
```

### Issue: Ports already in use
**Solution**: Check what's using the ports and stop it
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Find process using port 8080
netstat -ano | findstr :8080

# Find process using Kafka ports
netstat -ano | findstr :9092
```

### Issue: Services stuck in restarting state
**Solution**: Clean up and restart
```powershell
.\quick-run.ps1 -stop
Start-Sleep -Seconds 5
.\quick-run.ps1
```

### Issue: Out of memory or resource issues
**Solution**: Reduce consumer replicas or stop other Docker containers
```powershell
.\quick-run.ps1 -scale 1
```

---

## 🔧 Advanced: Custom Configuration

### Using Environment File

Create `.env` file in project root:
```env
SPRING_KAFKA_CONSUMER_MAX_POLL_RECORDS=100
CONSUMER_PROCESSING_DELAY_MS=10
LOGGING_LEVEL_COM_STREAMSOCIAL=TRACE
```

### Overriding Settings

```powershell
# Set environment variables before running
$env:CONSUMER_PROCESSING_DELAY_MS = "50"
$env:SPRING_KAFKA_LISTENER_CONCURRENCY = "5"

# Then run
.\quick-run.ps1
```

### Building Specific Service

```powershell
# Build only producer
docker compose -f streamsocial/Dockerfile build backend-api

# Build only consumer
docker compose -f streamsocial/Dockerfile build kafka-consumer
```

---

## 📈 Performance & Scaling

### Scaling Horizontally

```powershell
# Start with 1 consumer
.\quick-run.ps1

# Scale to 3 consumers (one per Kafka partition group)
.\quick-run.ps1 -scale 3

# Scale to 5 consumers (more than partitions - some will idle)
.\quick-run.ps1 -scale 5

# Check status
.\quick-run.ps1 -status
```

### Monitoring Scaling Impact

1. **Open Kafka UI**: http://localhost:8080
2. **Monitor**: Consumer Groups → streamsocial_event_consumers
3. **Watch**: Member count, lag per partition
4. **Scale**: `.\quick-run.ps1 -scale 3`
5. **Observe**: Rebalancing, lag reduction

---

## 📝 Script Features

### Automatic Validation
- ✓ Checks Docker installation
- ✓ Verifies Docker Compose availability
- ✓ Validates compose file exists
- ✓ Health checks services

### Color-Coded Output
- 🟢 Green: Success messages
- 🔴 Red: Errors
- 🔵 Cyan: Information
- 🟡 Yellow: Warnings

### Error Handling
- Exits on missing prerequisites
- Validates action parameters
- Shows helpful error messages
- Provides troubleshooting hints

---

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| **Start stack** | `.\quick-run.ps1` |
| **Start with demo** | `.\quick-run.ps1 -demo` |
| **Stop everything** | `.\quick-run.ps1 -stop` |
| **View logs** | `.\quick-run.ps1 -logs` |
| **Check status** | `.\quick-run.ps1 -status` |
| **Scale consumers** | `.\quick-run.ps1 -scale 3` |
| **Full control** | `.\manage-streamsocial.ps1 -Action <action>` |

---

## 📞 Support

For issues or questions:
1. Check troubleshooting section above
2. Review Docker Compose logs: `.\quick-run.ps1 -logs`
3. Verify Kafka connectivity: Open Kafka UI at http://localhost:8080
4. Check API health: `curl http://localhost:8000/actuator/health`
