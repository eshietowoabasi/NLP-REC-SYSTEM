<#
.SYNOPSIS
    Starts SkillBridge on this laptop and makes it reachable online through an ngrok link.

.DESCRIPTION
    1. Runs start-demo.ps1 (Docker services, migrations, API, worker and frontend windows).
    2. Builds the frontend and serves it with `vite preview` on port 4173 (fast over the
       internet), which also carries /api to Flask.
    3. Opens an ngrok tunnel to port 4173, so the whole app, including sign-in and
       downloads, works through one https link.

    One-time setup (see docs/DEMO.md, "Sharing the demo online"):
      winget install --id Ngrok.Ngrok -e
      ngrok config add-authtoken <your token from dashboard.ngrok.com>
    and claim your free static domain at dashboard.ngrok.com > Domains.

.PARAMETER Domain
    Your ngrok static domain, e.g. skillbridge-owo.ngrok-free.app. Asked for once and then
    remembered in .ngrok-domain. Pass -Domain '' -Random to use a random link instead.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\start-online-demo.ps1
#>
param([string]$Domain, [switch]$Random)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$domainFile = Join-Path $root '.ngrok-domain'

if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    Write-Host "`nngrok is not installed. Run:  winget install --id Ngrok.Ngrok -e" -ForegroundColor Red
    Write-Host "then close and reopen PowerShell, and run this script again."
    Read-Host 'Press Enter to close'; exit 1
}

if (-not $Random) {
    if (-not $Domain -and (Test-Path $domainFile)) { $Domain = (Get-Content $domainFile -Raw).Trim() }
    if (-not $Domain) {
        $Domain = (Read-Host 'Your ngrok static domain (e.g. skillbridge-owo.ngrok-free.app)').Trim()
        $Domain = $Domain -replace '^https?://', '' -replace '/.*$', ''
        if ($Domain) { Set-Content -Path $domainFile -Value $Domain -NoNewline }
    }
}

# Start the app (returns once the frontend answers on http://localhost:5173)
& (Join-Path $root 'start-demo.ps1') -NoBrowser

# The Vite dev server sends hundreds of small files, which is very slow through a tunnel.
# For the online link, build the frontend once and serve the built files with `vite preview`
# on port 4173; it forwards /api to Flask exactly like the dev server does.
$frontend = Join-Path $root 'frontend'
Write-Host "`n==> Building the frontend for the online link (about a minute)" -ForegroundColor Cyan
Push-Location $frontend
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host 'Frontend build failed; see the messages above.' -ForegroundColor Red; Read-Host 'Press Enter to close'; exit 1 }
Pop-Location
$preview = "Set-Location '$frontend'; `$host.UI.RawUI.WindowTitle = 'NLP-RS online frontend (port 4173)'; npx vite preview --port 4173 --strictPort"
Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $preview | Out-Null
Start-Sleep -Seconds 4

Write-Host "`n==> Opening the online link" -ForegroundColor Cyan
# --host-header=rewrite makes the request look local, so no host settings are needed and the
# session cookie and CSRF token keep working as they do on localhost.
if ($Domain) {
    Write-Host "Your link: https://$Domain" -ForegroundColor Green
    Write-Host "Keep this window open. Close it (or press Ctrl+C) to take the link offline.`n"
    ngrok http 4173 --domain=$Domain --host-header=rewrite
} else {
    Write-Host "Using a random link; look for the 'Forwarding' https address below." -ForegroundColor Yellow
    Write-Host "Keep this window open. Close it (or press Ctrl+C) to take the link offline.`n"
    ngrok http 4173 --host-header=rewrite
}
