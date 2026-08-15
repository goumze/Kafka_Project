@echo off
REM StreamSocial Docker Compose Quick Start (cmd.exe version)
REM
REM Usage:
REM   manage-streamsocial.bat start
REM   manage-streamsocial.bat stop
REM   manage-streamsocial.bat logs
REM   manage-streamsocial.bat scale 3
REM   manage-streamsocial.bat demo
REM   manage-streamsocial.bat status

setlocal enabledelayedexpansion

REM Configuration
set COMPOSE_FILE=streamsocial/Dockerfile
set PROJECT_NAME=streamsocial

REM Check if action provided
if "%1"=="" (
    set ACTION=start
) else (
    set ACTION=%1
)

REM Set parameter for scale action
if "%2"=="" (
    set PARAM=
) else (
    set PARAM=%2
)

REM Verify Docker Compose is available
docker compose version >nul 2>&1
if errorlevel 1 (
    echo ✗ Error: Docker Compose not found
    echo Please ensure Docker Desktop is installed and running
    exit /b 1
)

REM Verify compose file exists
if not exist "%COMPOSE_FILE%" (
    echo ✗ Error: Docker Compose file not found: %COMPOSE_FILE%
    echo Please run from the project root directory
    exit /b 1
)

REM Display header
cls
echo.
echo ╔══════════════════════════════════════════════╗
echo ║  StreamSocial Docker Compose Manager        ║
echo ║  Kafka + Spring Boot Microservices          ║
echo ╚══════════════════════════════════════════════╝
echo.
echo Action: %ACTION%
echo.

REM Execute action
if "%ACTION%"=="start" goto :start
if "%ACTION%"=="build" goto :build
if "%ACTION%"=="stop" goto :stop
if "%ACTION%"=="down" goto :stop
if "%ACTION%"=="logs" goto :logs
if "%ACTION%"=="status" goto :status
if "%ACTION%"=="ps" goto :ps
if "%ACTION%"=="restart" goto :restart
if "%ACTION%"=="scale" goto :scale
if "%ACTION%"=="demo" goto :demo
echo ✗ Unknown action: %ACTION%
goto :help

:start
echo Starting StreamSocial Stack...
docker compose -f %COMPOSE_FILE% up -d --build
if errorlevel 1 (
    echo ✗ Failed to start stack
    exit /b 1
)
echo ✓ Stack started
echo.
echo Waiting for services to be healthy (30 seconds)...
timeout /t 30 /nobreak
echo.
echo Status:
docker compose -f %COMPOSE_FILE% ps
goto :end

:build
echo Building Docker images...
docker compose -f %COMPOSE_FILE% build
if errorlevel 1 (
    echo ✗ Build failed
    exit /b 1
)
echo ✓ Build completed
goto :end

:stop
echo Stopping StreamSocial Stack...
docker compose -f %COMPOSE_FILE% down
if errorlevel 1 (
    echo ✗ Failed to stop stack
    exit /b 1
)
echo ✓ Stack stopped
goto :end

:logs
echo Displaying logs (Ctrl+C to exit)...
docker compose -f %COMPOSE_FILE% logs -f
goto :end

:status
echo Current Stack Status:
echo.
docker compose -f %COMPOSE_FILE% ps
goto :end

:ps
echo All containers:
docker compose -f %COMPOSE_FILE% ps -a
goto :end

:restart
echo Restarting Stack...
docker compose -f %COMPOSE_FILE% restart
if errorlevel 1 (
    echo ✗ Failed to restart
    exit /b 1
)
echo ✓ Stack restarted
goto :end

:scale
if "%PARAM%"=="" (
    echo ✗ Scale count not specified
    echo Usage: manage-streamsocial.bat scale ^<count^>
    echo Example: manage-streamsocial.bat scale 3
    exit /b 1
)
echo Scaling kafka-consumer to %PARAM% replicas...
docker compose -f %COMPOSE_FILE% up -d --scale kafka-consumer=%PARAM%
if errorlevel 1 (
    echo ✗ Failed to scale
    exit /b 1
)
echo ✓ Scaled to %PARAM% replicas
timeout /t 3 /nobreak
echo.
docker compose -f %COMPOSE_FILE% ps
goto :end

:demo
echo Starting Demo Mode...
echo.
echo  1. Starting services (Kafka + API)...
docker compose -f %COMPOSE_FILE% up -d --build
echo  Waiting for services to be healthy (30 seconds)...
timeout /t 30 /nobreak
echo.
echo  2. Current Status:
docker compose -f %COMPOSE_FILE% ps
echo.
echo  3. Scaling consumer to 3 instances...
docker compose -f %COMPOSE_FILE% up -d --scale kafka-consumer=3
timeout /t 5 /nobreak
echo.
echo  ✓ Demo Stack Ready!
echo.
echo  Access Points:
echo    - Kafka UI:       http://localhost:8080
echo    - API Health:     http://localhost:8000/actuator/health
echo    - API Metrics:    http://localhost:8000/actuator/metrics
echo.
echo  Try this (from PowerShell):
echo    curl -X POST http://localhost:8000/api/events/bulk/generate?count=100
echo.
goto :end

:help
echo Available Actions:
echo   start    - Build and start all services (default)
echo   build    - Build Docker images only
echo   stop     - Stop and remove containers
echo   down     - Stop and remove containers
echo   logs     - Display live logs
echo   status   - Show container status
echo   ps       - List all containers
echo   restart  - Restart running containers
echo   scale N  - Scale kafka-consumer to N replicas
echo   demo     - Run interactive demo
echo.
echo Examples:
echo   manage-streamsocial.bat start
echo   manage-streamsocial.bat scale 3
echo   manage-streamsocial.bat logs
echo   manage-streamsocial.bat stop
goto :end

:end
echo.
pause
