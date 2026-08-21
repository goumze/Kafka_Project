# Start PostgreSQL and PgAdmin containers
# Usage: .\start-postgres.ps1

Write-Host "Starting PostgreSQL and PgAdmin..." -ForegroundColor Green

docker-compose -f postgres-compose.yml up -d

Write-Host "`nChecking container status..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

docker-compose -f postgres-compose.yml ps

Write-Host "`nPostgreSQL and PgAdmin services started!" -ForegroundColor Green
Write-Host "`nAccess information:" -ForegroundColor Cyan
Write-Host "PostgreSQL:" -ForegroundColor Yellow
Write-Host "  Host: localhost" 
Write-Host "  Port: 5432"
Write-Host "  Username: admin"
Write-Host "  Password: admin123"
Write-Host "  Database: myapp_db"
Write-Host ""
Write-Host "PgAdmin:" -ForegroundColor Yellow
Write-Host "  URL: http://localhost:5050"
Write-Host "  Email: admin@admin.com"
Write-Host "  Password: admin123"
