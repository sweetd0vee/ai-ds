$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

& "$PSScriptRoot\wait-docker.ps1"
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "Building backend..." -ForegroundColor Cyan
docker build -f ..\backend\docker\Dockerfile -t ai-ds-backend:latest ..\backend
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Building frontend..." -ForegroundColor Cyan
docker build -f ..\frontend\docker\Dockerfile -t ai-ds-frontend:latest ..\frontend
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Images ready:" -ForegroundColor Green
docker images ai-ds-backend ai-ds-frontend

Write-Host ""
Write-Host "Starting stack..." -ForegroundColor Cyan
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
docker compose up -d
docker compose ps
