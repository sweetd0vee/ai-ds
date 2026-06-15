# Docker stack launcher (Windows PowerShell)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Test-DockerReady {
    Write-Host "Checking Docker..." -ForegroundColor Cyan
    $proc = Start-Process -FilePath "docker" -ArgumentList "version" -NoNewWindow -PassThru
    if (-not $proc.WaitForExit(20000)) {
        try { $proc.Kill() } catch {}
        return $false
    }
    return $proc.ExitCode -eq 0
}

if (-not (Test-DockerReady)) {
    Write-Host ""
    Write-Host "Docker is not responding (timeout 20s)." -ForegroundColor Red
    Write-Host ""
    Write-Host "Do this:" -ForegroundColor Yellow
    Write-Host "  1. Start Docker Desktop from Start menu"
    Write-Host "  2. Wait until the whale icon shows Running (not Starting)"
    Write-Host "  3. Open a NEW PowerShell window"
    Write-Host "  4. Run: cd $PSScriptRoot"
    Write-Host "  5. Run: .\up.ps1"
    Write-Host ""
    Write-Host "If Docker Desktop is already open, restart it (Quit -> open again)." -ForegroundColor Yellow
    exit 1
}

Write-Host "Docker OK" -ForegroundColor Green

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example" -ForegroundColor Green
}

$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"

Write-Host ""
Write-Host "Building images (first run may take 10-20 minutes)..." -ForegroundColor Cyan
docker compose build --progress=plain
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Starting containers..." -ForegroundColor Cyan
docker compose up -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
docker compose ps
Write-Host ""
Write-Host "UI:  http://localhost:8080" -ForegroundColor Green
Write-Host "API: http://localhost:8020/api/health" -ForegroundColor Green
