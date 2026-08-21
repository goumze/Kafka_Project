#!/usr/bin/env pwsh
# PowerShell script to start the Kafka cluster using docker-compose
# Ensure Docker and docker-compose are installed and running.

# Navigate to the directory containing this script (project root)
Set-Location -Path $PSScriptRoot

# Bring up the services defined in docker-compose.yml in detached mode
docker-compose -f "docker-compose.yml" up -d

Write-Host "Kafka cluster started. Use 'docker-compose logs -f' to view logs or 'docker-compose down' to stop."
