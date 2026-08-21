# Manage both Kafka and PostgreSQL stacks
# Usage: .\manage-all.ps1 -Action start|stop|status|restart

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "status", "restart")]
    [string]$Action
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Managing Kafka & PostgreSQL Stack" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

switch ($Action) {
    "start" {
        Write-Host "Starting Kafka cluster..." -ForegroundColor Green
        docker-compose -f docker-compose.yml up -d
        Start-Sleep -Seconds 2
        
        Write-Host "`nStarting PostgreSQL and PgAdmin..." -ForegroundColor Green
        docker-compose -f postgres-compose.yml up -d
        Start-Sleep -Seconds 2
        
        Write-Host "`n" -ForegroundColor Green
        Write-Host "All services started!" -ForegroundColor Green
    }
    
    "stop" {
        Write-Host "Stopping Kafka cluster..." -ForegroundColor Yellow
        docker-compose -f docker-compose.yml down
        Start-Sleep -Seconds 1
        
        Write-Host "`nStopping PostgreSQL and PgAdmin..." -ForegroundColor Yellow
        docker-compose -f postgres-compose.yml down
        
        Write-Host "`nAll services stopped!" -ForegroundColor Green
    }
    
    "status" {
        Write-Host "Kafka Status:" -ForegroundColor Yellow
        docker-compose -f docker-compose.yml ps
        
        Write-Host "`nPostgreSQL Status:" -ForegroundColor Yellow
        docker-compose -f postgres-compose.yml ps
    }
    
    "restart" {
        Write-Host "Restarting all services..." -ForegroundColor Yellow
        
        Write-Host "`nStopping services..." -ForegroundColor Yellow
        docker-compose -f docker-compose.yml down
        docker-compose -f postgres-compose.yml down
        Start-Sleep -Seconds 2
        
        Write-Host "`nStarting services..." -ForegroundColor Green
        docker-compose -f docker-compose.yml up -d
        docker-compose -f postgres-compose.yml up -d
        Start-Sleep -Seconds 2
        
        Write-Host "`nAll services restarted!" -ForegroundColor Green
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Access Points:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Kafka UI: http://localhost:8080" -ForegroundColor White
Write-Host "PostgreSQL Host: localhost:5432 (admin/admin123)" -ForegroundColor White
Write-Host "PgAdmin: http://localhost:5050 (admin@admin.com/admin123)" -ForegroundColor White
