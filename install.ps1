# Vynaris installer for Windows (PowerShell).
# Creates venv, installs deps, ensures Postgres, runs vynaris setup.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Say($msg)  { Write-Host "==> $msg" -ForegroundColor Cyan }
function OK($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  [!] $msg"  -ForegroundColor Yellow }
function Die($msg)  { Write-Host "  [X] $msg"  -ForegroundColor Red; exit 1 }

Say "Vynaris installer"

# --- Python ---
$py = $null
foreach ($c in @("python", "python3", "py")) {
    try {
        $v = & $c --version 2>$null
        if ($v) { $py = $c; break }
    } catch { }
}
if (-not $py) { Die "Python 3.11+ required. Install from https://www.python.org" }
$ver = & $py -c "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$parts = $ver.Split("."); $major = [int]$parts[0]; $minor = [int]$parts[1]
if ($major*100 + $minor -lt 311) { Die "Python 3.11+ required (found $ver)" }
OK "Python $ver"

# --- Node / Claude CLI ---
try { $nv = & node --version 2>$null; if ($nv) { OK "Node $nv" } } catch { Warn "Node.js not found — Claude CLI requires it" }
$claudeOk = $false
try { & claude --version 2>$null | Out-Null; $claudeOk = $LASTEXITCODE -eq 0 } catch { }
if (-not $claudeOk) {
    try {
        Say "installing Claude CLI via npm..."
        & npm install -g '@anthropic-ai/claude-code' 2>&1 | Out-Null
        $claudeOk = $?
    } catch { Warn "Claude CLI install failed — run manually: npm install -g @anthropic-ai/claude-code" }
}
if ($claudeOk) { OK "Claude CLI ready" }

# --- Postgres ---
Say "checking Postgres on localhost:5432..."
$pgReady = $false
try {
    $tcp = Test-NetConnection -ComputerName localhost -Port 5432 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($tcp) { $pgReady = $true }
} catch { }
if ($pgReady) {
    OK "Postgres already running on :5432"
} else {
    try {
        & docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Say "starting Postgres via docker compose..."
            & docker compose up -d postgres | Out-Null
            for ($i=0; $i -lt 30; $i++) {
                Start-Sleep -Seconds 1
                try {
                    & docker compose exec -T postgres pg_isready -U vynaris -d vynaris 2>&1 | Out-Null
                    if ($LASTEXITCODE -eq 0) { break }
                } catch { }
            }
            OK "Postgres running in Docker"
        } else {
            Die "No Postgres on :5432 and Docker not running. Start Docker Desktop or install Postgres, then rerun."
        }
    } catch {
        Die "No Postgres on :5432 and Docker not available. Start Docker Desktop or install Postgres, then rerun."
    }
}

# --- venv + deps ---
if (-not (Test-Path ".venv")) {
    Say "creating Python venv..."
    & $py -m venv .venv
}
$venvPy = Join-Path (Resolve-Path .venv).Path "Scripts\python.exe"
Say "installing Python dependencies..."
& $venvPy -m pip install -q --upgrade pip
& $venvPy -m pip install -q -e .
OK "dependencies installed"

# --- setup ---
Say "running vynaris setup..."
& $venvPy -m vynaris setup
OK "install complete"

Write-Host ""
Write-Host "  Start Vynaris:   .venv\Scripts\vynaris.exe start" -ForegroundColor Green
Write-Host "  Open in browser: .venv\Scripts\vynaris.exe open" -ForegroundColor Green
Write-Host ""
