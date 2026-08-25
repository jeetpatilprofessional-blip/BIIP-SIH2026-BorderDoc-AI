<#>
.SYNOPSIS
    BIIP-SIH2026 Development Environment Setup Script (PowerShell for Windows)
.DESCRIPTION
    Sets up the complete development environment for BIIP-SIH2026
#>

param(
    [switch]$SkipModelDownload,
    [switch]$SkipDocker
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "BIIP-SIH2026 Development Setup (Windows)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

function Check-Command {
    param($Name, $VersionCmd = "--version")
    try {
        $version = & $Name $VersionCmd 2>&1 | Select-Object -First 1
        Write-Host "✓ $Name found: $version" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "✗ $Name not found - please install it" -ForegroundColor Red
        return $false
    }
}

Write-Host ""
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

$allFound = $true
$allFound = Check-Command "docker" -and $allFound
$allFound = Check-Command "docker-compose" -and $allFound
$allFound = Check-Command "git" -and $allFound
$allFound = Check-Command "node" -and $allFound
$allFound = Check-Command "npm" -and $allFound
$allFound = Check-Command "python" -and $allFound

if (-not $allFound) {
    Write-Host "Missing dependencies. Please install them first." -ForegroundColor Red
    exit 1
}

# Check versions
$nodeVersion = [int](node --version 2>&1 | Select-Object -First 1).TrimStart('v').Split('.')[0]
if ($nodeVersion -lt 20) {
    Write-Host "⚠ Node.js version $nodeVersion < 20, may cause issues" -ForegroundColor Yellow
}

$pythonVersion = (python --version 2>&1).Split(' ')[1]
$pyMajor = [int]$pythonVersion.Split('.')[0]
$pyMinor = [int]$pythonVersion.Split('.')[1]
if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 11)) {
    Write-Host "⚠ Python version $pythonVersion < 3.11, may cause issues" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setting up Backend" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Set-Location backend

if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
& ".\\venv\\Scripts\\pip.exe" install --upgrade pip
& ".\\venv\\Scripts\\pip.exe" install -r requirements.txt

if (-not (Test-Path ".env")) {
    Write-Host "Creating backend .env from example..." -ForegroundColor Yellow
    Copy-Item "..\\.env.example" ".env"
    Write-Host "⚠ Please edit backend\.env with your settings" -ForegroundColor Yellow
}

New-Item -ItemType Directory -Force -Path "models\\insightface" | Out-Null

Write-Host "✓ Backend setup complete" -ForegroundColor Green

Set-Location ..

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setting up Frontend" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Set-Location frontend

Write-Host "Installing Node dependencies..." -ForegroundColor Yellow
npm install

if (-not (Test-Path ".env")) {
    Write-Host "Creating frontend .env..." -ForegroundColor Yellow
    @"
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
VITE_DEMO_MODE=true
"@ | Set-Content ".env"
}

Write-Host "✓ Frontend setup complete" -ForegroundColor Green

Set-Location ..

if (-not $SkipModelDownload) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Downloading AI Models" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan

    $modelDir = "backend\models\insightface"
    $modelFile = "$modelDir\buffalo_l.onnx"

    if (-not (Test-Path $modelFile)) {
        Write-Host "Downloading InsightFace buffalo_l model (~200MB)..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Force -Path $modelDir | Out-Null
        Set-Location $modelDir

        try {
            Invoke-WebRequest -Uri "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip" -OutFile "buffalo_l.zip" -ErrorAction Stop
            Expand-Archive -Path "buffalo_l.zip" -DestinationPath "." -Force
            Remove-Item "buffalo_l.zip"
            Write-Host "✓ Model downloaded" -ForegroundColor Green
        } catch {
            Write-Host "⚠ Could not download model - will download on first run" -ForegroundColor Yellow
        }

        Set-Location ..\..\..
    } else {
        Write-Host "✓ Model already present" -ForegroundColor Green
    }
}

if (-not $SkipDocker) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Starting Services with Docker Compose" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan

    Write-Host "Starting PostgreSQL..." -ForegroundColor Yellow
    docker-compose up -d postgres

    Write-Host "Waiting for PostgreSQL..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5

    Set-Location backend
    & ".\\venv\\Scripts\\python.exe" -m alembic upgrade head 2>$null
    Set-Location ..
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start development servers:" -ForegroundColor White
Write-Host ""
Write-Host "  Terminal 1 - Backend:" -ForegroundColor White
Write-Host "    cd backend; .\\venv\\Scripts\\Activate.ps1; uvicorn app.main:app --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "  Terminal 2 - Frontend:" -ForegroundColor White
Write-Host "    cd frontend; npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "Or use Docker Compose for everything:" -ForegroundColor White
Write-Host "  docker-compose up --build" -ForegroundColor Gray
Write-Host ""
Write-Host "Access points:" -ForegroundColor White
Write-Host "  Frontend:     http://localhost:3000 (docker) or http://localhost:5173 (dev)" -ForegroundColor Gray
Write-Host "  Backend API:  http://localhost:8000" -ForegroundColor Gray
Write-Host "  API Docs:     http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "  Database:     localhost:5432 (postgres/postgres)" -ForegroundColor Gray
Write-Host ""
Write-Host "Run demo scenarios:" -ForegroundColor White
Write-Host "  curl -X POST http://localhost:8000/api/demo/load-test-data" -ForegroundColor Gray
Write-Host "  curl -X POST http://localhost:8000/api/demo/scenarios/scenario_1/run" -ForegroundColor Gray
Write-Host ""
Write-Host "Run tests:" -ForegroundColor White
Write-Host "  cd backend; .\\venv\\Scripts\\pytest tests\ -v" -ForegroundColor Gray