# Stop PostgreSQL and PgAdmin containers
# Usage: .\stop-postgres.ps1

Write-Host "Stopping PostgreSQL and PgAdmin..." -ForegroundColor Yellow

docker-compose -f postgres-compose.yml down

Write-Host "`nContainer status:" -ForegroundColor Yellow
docker-compose -f postgres-compose.yml ps

Write-Host "`nPostgreSQL and PgAdmin services stopped!" -ForegroundColor Green
