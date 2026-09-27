<#
.SYNOPSIS
    Start NLP-RS for a demo in lightweight mode and open it in the browser.

.DESCRIPTION
    1. Starts PostgreSQL and Redis in Docker (docker-compose.services.yml).
    2. Applies database migrations.
    3. Opens three windows: the Flask API, the RQ worker and the Vite frontend.
    4. Waits until the app answers, then opens http://localhost:5173.

    Close the three windows (or press Ctrl+C in each) to stop the app; Postgres and Redis keep
    running in Docker (stop them with: docker compose -f docker-compose.services.yml stop).

.PARAMETER NoBrowser
    Do not open the browser at the end.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\start-demo.ps1
#>
param([switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$appUrl = 'http://localhost:5173'
$apiHealth = 'http://localhost:5000/api/health'

function Step($message) { Write-Host "`n==> $message" -ForegroundColor Cyan }
function Fail($message) {
    Write-Host "`n$message" -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
}

# --- Prerequisites ---------------------------------------------------------------------
Step 'Checking prerequisites'
if (-not (Test-Path (Join-Path $root '.env'))) {
    Fail 'No .env file. Copy .env.example to .env and fill it in (see docs/SETUP.md).'
}
if (-not (Test-Path (Join-Path $backend '.venv\Scripts\python.exe'))) {
    Fail 'Backend virtualenv missing. In backend\: python -m venv .venv; .venv\Scripts\pip install -r requirements-dev.txt'
}
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Fail 'Frontend packages missing. In frontend\: npm ci'
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $dockerBin = Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin'
    if (Test-Path $dockerBin) { $env:Path = "$dockerBin;$env:Path" }
    else { Fail 'Docker is not installed or not on PATH. Start Docker Desktop and try again.' }
}
docker info *> $null
if ($LASTEXITCODE -ne 0) { Fail 'Docker Desktop is not running. Start it, wait until it is ready, then run this script again.' }

# --- Services --------------------------------------------------------------------------
Step 'Starting PostgreSQL and Redis (Docker)'
Push-Location $root
docker compose -f docker-compose.services.yml up -d --wait
$composeExit = $LASTEXITCODE
Pop-Location
if ($composeExit -ne 0) { Fail 'PostgreSQL/Redis did not start. Check: docker compose -f docker-compose.services.yml logs' }

Step 'Applying database migrations'
Push-Location $backend
& .\.venv\Scripts\flask.exe --app wsgi db upgrade
$migrateExit = $LASTEXITCODE
Pop-Location
if ($migrateExit -ne 0) { Fail 'Database migrations failed (see the messages above).' }

# --- App processes (one window each) ---------------------------------------------------
function Start-AppWindow($title, $folder, $command) {
    $script = "`$Host.UI.RawUI.WindowTitle = 'NLP-RS $title'; Set-Location '$folder'; $command"
    Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $script | Out-Null
}

Step 'Starting the API, the worker and the frontend (three new windows)'
Start-AppWindow 'API (Flask, port 5000)' $backend '.\.venv\Scripts\flask.exe --app wsgi run --port 5000'
Start-AppWindow 'worker (RQ)' $backend '.\.venv\Scripts\python.exe -m app.worker'
Start-AppWindow 'frontend (Vite, port 5173)' $frontend 'npm run dev'

# --- Wait until the app answers ----------------------------------------------------------
Step 'Waiting for the app to answer'
$deadline = (Get-Date).AddMinutes(3)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        $api = Invoke-WebRequest $apiHealth -UseBasicParsing -TimeoutSec 3
        $web = Invoke-WebRequest $appUrl -UseBasicParsing -TimeoutSec 3
        if ($api.StatusCode -eq 200 -and $web.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 2
}
if (-not $ready) { Fail "The app did not answer within 3 minutes. Check the three NLP-RS windows for errors." }

Write-Host "`nNLP-RS is running at $appUrl" -ForegroundColor Green
Write-Host 'Sign in with ADMIN_USERNAME / ADMIN_PASSWORD from .env (or any account created in Users).'
Write-Host 'Tip: run one analysis session before presenting; the first run in a new worker is slower.'
if (-not $NoBrowser) { Start-Process $appUrl }
