## Stop Kafka Docker‑Compose cluster
# This script stops and removes the containers defined in docker‑compose.yml
# Usage: .\stop-kafka.ps1

# Ensure we are in the script directory
Set-Location -Path $PSScriptRoot

# Stop and remove containers
docker-compose -f "docker-compose.yml" down

Write-Host "Kafka Docker‑Compose cluster stopped and removed." -ForegroundColor Green
