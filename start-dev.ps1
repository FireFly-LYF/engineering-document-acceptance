# Start API (8787) + web (5173) + AGH (4177).
# Console shows only the Vite frontend. API/AGH logs go to .dev-logs\
# Usage: .\start-dev.ps1   or double-click start-dev.cmd
# Ctrl+C stops the frontend and cleans up background processes.
# Uses node.exe directly (not npm.cmd) to avoid Windows "Terminate batch job (Y/N)?" hangs.

$ErrorActionPreference = 'Stop'

$EdaRoot = $PSScriptRoot
$ServerDir = Join-Path $EdaRoot 'server'
$WebDir = Join-Path $EdaRoot 'web'
$AghRoot = Join-Path (Split-Path $EdaRoot -Parent) 'agnes-harness'
$AghCli = Join-Path $AghRoot 'packages\cli\dist\local\agnes.mjs'
$LogDir = Join-Path $EdaRoot '.dev-logs'
$TsxCli = Join-Path $ServerDir 'node_modules\tsx\dist\cli.mjs'
$ViteCli = Join-Path $WebDir 'node_modules\vite\bin\vite.js'

if (-not (Test-Path $ServerDir)) { throw "server not found: $ServerDir" }
if (-not (Test-Path $WebDir)) { throw "web not found: $WebDir" }
if (-not (Test-Path $TsxCli)) { throw "tsx not found: $TsxCli  (run npm install in server/)" }
if (-not (Test-Path $ViteCli)) { throw "vite not found: $ViteCli  (run npm install in web/)" }
if (-not (Test-Path $AghCli)) {
  throw @"
AGH CLI not found: $AghCli
Build it first in agnes-harness:
  pnpm install --frozen-lockfile
  pnpm --filter @agnes/cli build:local
"@
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Stop-Tree([System.Diagnostics.Process]$proc) {
  if (-not $proc) { return }
  try {
    if (-not $proc.HasExited) {
      & taskkill.exe /PID $proc.Id /T /F 2>$null | Out-Null
    }
  } catch {
    # ignore
  }
}

$apiProc = $null
$aghProc = $null
$code = 0

try {
  # API / AGH 共用 profile，否则 sessions list 与 -p 对不上，跳转永远拿不到 sessionId
  $env:AGNES_PROFILE = 'local-dev'

  Write-Host '[start-dev] background API  -> http://127.0.0.1:8787' -ForegroundColor DarkGray
  $apiProc = Start-Process -FilePath 'node.exe' `
    -ArgumentList @($TsxCli, 'watch', 'src/index.ts') `
    -WorkingDirectory $ServerDir `
    -PassThru `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDir 'api.out.log') `
    -RedirectStandardError (Join-Path $LogDir 'api.err.log')

  Write-Host '[start-dev] background AGH  -> http://127.0.0.1:4177' -ForegroundColor DarkGray
  $aghProc = Start-Process -FilePath 'node.exe' `
    -ArgumentList @($AghCli, 'serve') `
    -WorkingDirectory $AghRoot `
    -PassThru `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDir 'agh.out.log') `
    -RedirectStandardError (Join-Path $LogDir 'agh.err.log')

  $ready = $false
  for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 250
    try {
      $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8787/api/health' -UseBasicParsing -TimeoutSec 1
      if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {
      # keep waiting
    }
  }
  if ($ready) {
    Write-Host '[start-dev] API ready' -ForegroundColor DarkGray
  } else {
    Write-Host '[start-dev] API not ready yet; starting web anyway (see .dev-logs)' -ForegroundColor DarkYellow
  }

  Write-Host '[start-dev] foreground web (Vite output below)' -ForegroundColor Cyan
  Write-Host '----------------------------------------' -ForegroundColor DarkGray
  Set-Location $WebDir
  # Direct node (not npm.cmd) — avoids nested .cmd "Terminate batch job (Y/N)?" on Ctrl+C / restart.
  & node.exe $ViteCli
  $code = $LASTEXITCODE
} finally {
  Write-Host ''
  Write-Host '[start-dev] stopping background API / AGH ...' -ForegroundColor DarkGray
  Stop-Tree $apiProc
  Stop-Tree $aghProc
}

if ($null -eq $code) { exit 0 }
exit $code
