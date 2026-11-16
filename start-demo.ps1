<#
.SYNOPSIS
    Start SkillBridge / NLP-RS in lightweight mode without Docker.

.DESCRIPTION
    1. Checks the local Python environment, frontend packages and .env.
    2. Verifies the configured PostgreSQL (Neon) and Redis (Upstash) connections.
    3. Applies database migrations.
    4. Opens three windows: the Flask API, the RQ worker and the Vite frontend.
    5. Waits until the app answers, then opens http://localhost:5173.

    Close the three windows (or press Ctrl+C in each) to stop the local app.

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

# --- Cloud services --------------------------------------------------------------------
Step 'Checking PostgreSQL and Redis connections'

$python = Join-Path $backend '.venv\Scripts\python.exe'

Push-Location $backend
try {
    & $python -c "from app import create_app; from app.extensions import db; from sqlalchemy import text; app=create_app(); ctx=app.app_context(); ctx.push(); db.session.execute(text('SELECT 1')).scalar(); ctx.pop(); print('PostgreSQL OK')"
    if ($LASTEXITCODE -ne 0) {
        Fail 'PostgreSQL connection failed. Check DATABASE_URL in .env.'
    }

    & $python -c "from app import create_app; import redis; app=create_app(); r=redis.from_url(app.config['REDIS_URL'], socket_timeout=10); assert r.ping(); print('Redis OK')"
    if ($LASTEXITCODE -ne 0) {
        Fail 'Redis connection failed. Check REDIS_URL in .env.'
    }
}
finally {
    Pop-Location
}

# --- Database --------------------------------------------------------------------------
Step 'Applying database migrations'

Push-Location $backend
& .\.venv\Scripts\flask.exe --app wsgi db upgrade
$migrateExit = $LASTEXITCODE
Pop-Location

if ($migrateExit -ne 0) {
    Fail 'Database migrations failed (see the messages above).'
}

# --- App processes (one window each) ---------------------------------------------------
function Start-AppWindow($title, $folder, $command) {
    $script = "`$Host.UI.RawUI.WindowTitle = 'SkillBridge $title'; Set-Location '$folder'; $command"
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

        if ($api.StatusCode -eq 200 -and $web.StatusCode -eq 200) {
            $ready = $true
            break
        }
    }
    catch { }

    Start-Sleep -Seconds 2
}

if (-not $ready) {
    Fail 'The app did not answer within 3 minutes. Check the three SkillBridge windows for errors.'
}

Write-Host "`nSkillBridge is running at $appUrl" -ForegroundColor Green
Write-Host 'Sign in with your administrator account.'
Write-Host 'Tip: the first NLP job in a fresh worker can be slower while models are loaded.'

if (-not $NoBrowser) {
    Start-Process $appUrl
}
