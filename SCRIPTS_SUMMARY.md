# StreamSocial Docker Compose - Scripts Summary

## ✅ Created Scripts Overview

You now have **4 complete management scripts** for orchestrating your Kafka + Spring Boot microservices stack:

---

## 📍 Script Locations

All scripts are located in the **project root directory**:
```
C:\Users\lipsa\OneDrive\Documents\Gags_tech\Kafka\Kafka_Project\
├── manage-streamsocial.ps1        ← PowerShell (Advanced)
├── quick-run.ps1                  ← PowerShell (Simple)
├── manage-streamsocial.bat        ← Command Prompt
└── manage-streamsocial.sh         ← Bash (Linux/Mac/WSL)
```

---

## 🎯 Which Script Should I Use?

### 👤 I'm on Windows with PowerShell

**Best choice: `quick-run.ps1`** (simplest)
```powershell
cd C:\...\Kafka_Project
.\quick-run.ps1
```

**Alternative: `manage-streamsocial.ps1`** (more control)
```powershell
.\manage-streamsocial.ps1 -Action start
```

### 👤 I'm on Windows with Command Prompt

**Use: `manage-streamsocial.bat`**
```batch
cd C:\...\Kafka_Project
manage-streamsocial.bat start
```

### 👤 I'm on Linux / Mac / WSL

**Use: `manage-streamsocial.sh`**
```bash
cd /path/to/Kafka_Project
chmod +x manage-streamsocial.sh
./manage-streamsocial.sh start
```

---

## 🚀 Quick Commands by Platform

### PowerShell (Fastest)
```powershell
.\quick-run.ps1              # Start everything
.\quick-run.ps1 -demo        # Run demo with scaling
.\quick-run.ps1 -scale 3     # Scale consumers
.\quick-run.ps1 -logs        # View logs
.\quick-run.ps1 -stop        # Stop everything
```

### Command Prompt
```batch
manage-streamsocial.bat start      # Start
manage-streamsocial.bat demo       # Demo
manage-streamsocial.bat scale 3    # Scale
manage-streamsocial.bat logs       # Logs
manage-streamsocial.bat stop       # Stop
```

### Bash/Shell
```bash
./manage-streamsocial.sh start      # Start
./manage-streamsocial.sh demo       # Demo
./manage-streamsocial.sh scale 3    # Scale
./manage-streamsocial.sh logs       # Logs
./manage-streamsocial.sh stop       # Stop
```

---

## 📋 What Each Script Does

### 1️⃣ `manage-streamsocial.ps1` (PowerShell - Advanced)
- **Type**: Parameter-based, full-featured
- **Platform**: Windows with PowerShell
- **Best for**: Detailed control, scripting, CI/CD
- **Features**: 
  - Build independently
  - View service-specific logs
  - Advanced scaling options
  - Comprehensive error handling
- **Example**: `.\manage-streamsocial.ps1 -Action scale -Service kafka-consumer -Replicas 5`

### 2️⃣ `quick-run.ps1` (PowerShell - Simple)
- **Type**: Flag-based, simplified
- **Platform**: Windows with PowerShell
- **Best for**: Quick development, simple operations
- **Features**:
  - Start (default)
  - Stop, restart, demo
  - View logs
  - Scale consumers
  - Interactive prompts
- **Example**: `.\quick-run.ps1 -scale 3`

### 3️⃣ `manage-streamsocial.bat` (Command Prompt)
- **Type**: Action-based
- **Platform**: Windows with cmd.exe
- **Best for**: Legacy cmd.exe users, batch automation
- **Features**:
  - All common operations
  - Pause after execution (for interactive use)
  - Windows-native batch commands
- **Example**: `manage-streamsocial.bat scale 3`

### 4️⃣ `manage-streamsocial.sh` (Bash/Shell)
- **Type**: Action-based
- **Platform**: Linux, Mac, WSL
- **Best for**: Cross-platform development, Unix users
- **Features**:
  - All operations of bat/ps scripts
  - POSIX shell compatible
  - Color-coded output
  - Comprehensive help
- **Example**: `./manage-streamsocial.sh scale 3`

---

## 🎬 First-Time Setup

### Step 1: Navigate to Project
```powershell
cd C:\Users\lipsa\OneDrive\Documents\Gags_tech\Kafka\Kafka_Project
# OR
cd /path/to/Kafka_Project  # On Linux/Mac
```

### Step 2: (PowerShell Only) Allow Script Execution
```powershell
# One-time setup
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then you can run scripts normally
.\quick-run.ps1
```

### Step 3: (Bash Only) Make Script Executable
```bash
# One-time setup
chmod +x manage-streamsocial.sh

# Then you can run it
./manage-streamsocial.sh start
```

### Step 4: Run Your First Command
```powershell
# PowerShell
.\quick-run.ps1

# OR Cmd
manage-streamsocial.bat start

# OR Bash
./manage-streamsocial.sh start
```

### Step 5: Wait and Access Services
- **Wait**: 30 seconds for services to become healthy
- **Kafka UI**: http://localhost:8080
- **API Health**: http://localhost:8000/actuator/health

---

## 📊 Feature Comparison Matrix

| Feature | `manage-streamsocial.ps1` | `quick-run.ps1` | `manage-streamsocial.bat` | `manage-streamsocial.sh` |
|---------|:------------------------:|:---------------:|:----------------------:|:----------------------:|
| **Start services** | ✓ | ✓ | ✓ | ✓ |
| **Build images** | ✓ | ✗ | ✓ | ✓ |
| **Stop services** | ✓ | ✓ | ✓ | ✓ |
| **View logs** | ✓ | ✓ | ✓ | ✓ |
| **Service-specific logs** | ✓ | ✗ | ✗ | ✓ |
| **Check status** | ✓ | ✓ | ✓ | ✓ |
| **List containers** | ✓ | ✓ | ✓ | ✓ |
| **Restart services** | ✓ | ✓ | ✓ | ✓ |
| **Scale consumers** | ✓ | ✓ | ✓ | ✓ |
| **Demo mode** | ✓ | ✓ | ✓ | ✓ |
| **Easy to use** | Medium | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Powerful** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Windows** | ✓ | ✓ | ✓ | ⚠️ (WSL only) |
| **Linux/Mac** | ✗ | ✗ | ✗ | ✓ |

---

## 🎯 Common Tasks

| Task | Command |
|------|---------|
| **Start Stack** | `.\quick-run.ps1` |
| **Full Demo** | `.\quick-run.ps1 -demo` |
| **Scale to 5** | `.\quick-run.ps1 -scale 5` |
| **View Logs** | `.\quick-run.ps1 -logs` |
| **Check Status** | `.\quick-run.ps1 -status` |
| **Stop Everything** | `.\quick-run.ps1 -stop` |
| **Advanced: View Producer Logs** | `.\manage-streamsocial.ps1 -Action logs -Service backend-api` |
| **Advanced: Restart** | `.\manage-streamsocial.ps1 -Action restart` |

---

## 📚 Documentation

### Quick References
- **[DOCKER_COMPOSE_SCRIPTS.md](DOCKER_COMPOSE_SCRIPTS.md)** - Complete script guide for all platforms
- **[POWERSHELL_SCRIPTS_GUIDE.md](POWERSHELL_SCRIPTS_GUIDE.md)** - Detailed PowerShell documentation

### Architecture
- **[MICROSERVICES_REFACTORING_COMPLETE.md](MICROSERVICES_REFACTORING_COMPLETE.md)** - Microservices structure
- **[BEFORE_AFTER_COMPARISON.md](BEFORE_AFTER_COMPARISON.md)** - Architecture comparison
- **[SPRING_BOOT_SETUP.md](SPRING_BOOT_SETUP.md)** - Spring Boot implementation guide

---

## 🔍 Inside Each Script

All scripts include:

✅ **Automatic Validation**
- Docker installation check
- Docker Compose availability
- Compose file existence verification

✅ **Error Handling**
- Clear error messages
- Helpful troubleshooting hints
- Exit codes for automation

✅ **User Feedback**
- Color-coded output (Green/Red/Yellow/Cyan)
- Progress indicators
- Status displays

✅ **Smart Defaults**
- Default to "start" action
- Auto-detect project root
- Sensible timeouts

---

## 🚀 Execute Now!

### For PowerShell Users (Recommended):
```powershell
cd C:\Users\lipsa\OneDrive\Documents\Gags_tech\Kafka\Kafka_Project
.\quick-run.ps1
# Wait 30 seconds, then open http://localhost:8080
```

### For Command Prompt Users:
```batch
cd C:\Users\lipsa\OneDrive\Documents\Gags_tech\Kafka\Kafka_Project
manage-streamsocial.bat start
REM Wait 30 seconds, then open http://localhost:8080
```

### For Bash/Linux/Mac/WSL Users:
```bash
cd /path/to/Kafka_Project
chmod +x manage-streamsocial.sh
./manage-streamsocial.sh start
# Wait 30 seconds, then open http://localhost:8080
```

---

## 💡 Pro Tips

1. **Use demo mode first** to see everything working:
   ```powershell
   .\quick-run.ps1 -demo
   ```

2. **Open Kafka UI** while services are running:
   - Visit: http://localhost:8080
   - Watch partitions, lag, and consumer groups in real-time

3. **Generate events** while watching Kafka UI:
   ```powershell
   curl -X POST http://localhost:8000/api/events/bulk/generate?count=1000
   ```

4. **Scale dynamically** to test consumer group rebalancing:
   ```powershell
   .\quick-run.ps1 -scale 3  # 1 → 3 consumers
   .\quick-run.ps1 -scale 1  # 3 → 1 consumer
   ```

5. **Monitor logs** in one terminal:
   ```powershell
   .\quick-run.ps1 -logs
   # Ctrl+C to stop
   ```

---

## ✨ Summary

You have **complete, production-ready management scripts** for:

- ✅ Starting/stopping the entire stack
- ✅ Building Docker images
- ✅ Monitoring services and logs
- ✅ Scaling consumer workers
- ✅ Running demo scenarios
- ✅ Cross-platform compatibility
- ✅ Comprehensive error handling
- ✅ User-friendly interfaces

**Choose your platform, run your script, and start developing!** 🎉

