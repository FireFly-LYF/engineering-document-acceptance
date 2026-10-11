# Start API (8787) + web (5173) + AGH (4177).
# Console shows only the Vite frontend. API/AGH logs go to .dev-logs\
# Usage: .\start-dev.ps1   or double-click start-dev.cmd
#
# CRITICAL: AGH serve MUST use EDA root as workspace (--cwd), same as server -p.
# If serve runs under agnes-harness, web shows transport closed / empty session.

$ErrorActionPreference = 'Stop'

$EdaRoot = $PSScriptRoot
if (-not $EdaRoot) { $EdaRoot = Split-Path -Parent $MyInvocation.MyCommand.Path }
$EdaRoot = (Resolve-Path -LiteralPath $EdaRoot).Path

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

function Invoke-TaskKillSafe([int]$ProcId) {
  if (-not $ProcId -or $ProcId -eq 0) { return $false }
  $prev = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    $null = cmd.exe /c "taskkill /PID $ProcId /T /F >nul 2>&1"
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  } finally {
    $ErrorActionPreference = $prev
  }
}

function Stop-Tree([System.Diagnostics.Process]$proc) {
  if (-not $proc) { return }
  try {
    if (-not $proc.HasExited) { [void](Invoke-TaskKillSafe $proc.Id) }
  } catch { }
}

function Stop-PortListener([int]$Port) {
  $conns = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
  foreach ($c in $conns) {
    $procId = $c.OwningProcess
    if ($procId -and $procId -ne 0) {
      Write-Host "[start-dev] free port $Port (kill pid $procId)" -ForegroundColor DarkYellow
      if (-not (Invoke-TaskKillSafe $procId)) {
        Write-Host "[start-dev] could not kill pid $procId — will try another port if needed" -ForegroundColor DarkYellow
      }
    }
  }
}

function Test-PortFree([int]$Port) {
  -not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

$apiProc = $null
$aghProc = $null
$code = 0

try {
  $env:AGNES_PROFILE = 'local-dev'
  $env:EDA_ROOT = $EdaRoot

  Write-Host "[start-dev] EDA workspace = $EdaRoot" -ForegroundColor Cyan

  Write-Host '[start-dev] stopping previous AGH daemon (local-dev) ...' -ForegroundColor DarkGray
  try {
    & node.exe $AghCli daemon stop --profile local-dev 2>$null | Out-Null
  } catch { }

  $prevKill = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'daemon\.mjs|agnes\.mjs serve' } |
    ForEach-Object {
      Write-Host "[start-dev] kill leftover agnes pid $($_.ProcessId)" -ForegroundColor DarkYellow
      [void](Invoke-TaskKillSafe $_.ProcessId)
    }
  $ErrorActionPreference = $prevKill

  Stop-PortListener 4177
  Stop-PortListener 4178
  Stop-PortListener 8787
  Start-Sleep -Milliseconds 800

  $aghPort = 4177
  if (-not (Test-PortFree 4177)) {
    Write-Host '[start-dev] 4177 stuck — falling back to 4178' -ForegroundColor DarkYellow
    $aghPort = 4178
    Stop-PortListener 4178
  }
  $env:AGNES_WEB_ORIGIN = "http://127.0.0.1:$aghPort"
  # 落盘给 API 读取（Start-Process 在部分环境下不继承 $env）
  Set-Content -Path (Join-Path $LogDir 'agh-web-origin.txt') -Value $env:AGNES_WEB_ORIGIN -Encoding utf8

  Write-Host "[start-dev] AGH Web origin -> $($env:AGNES_WEB_ORIGIN)" -ForegroundColor Cyan

  Write-Host '[start-dev] background API  -> http://127.0.0.1:8787' -ForegroundColor DarkGray
  $apiProc = Start-Process -FilePath 'node.exe' `
    -ArgumentList @($TsxCli, 'watch', 'src/index.ts') `
    -WorkingDirectory $ServerDir `
    -PassThru `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDir 'api.out.log') `
    -RedirectStandardError (Join-Path $LogDir 'api.err.log')

  Write-Host "[start-dev] background AGH  -> http://127.0.0.1:$aghPort (serve --cwd EDA)" -ForegroundColor DarkGray
  $aghProc = Start-Process -FilePath 'node.exe' `
    -ArgumentList @($AghCli, 'serve', '--cwd', $EdaRoot, '--profile', 'local-dev', '--port', "$aghPort") `
    -WorkingDirectory $EdaRoot `
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
    } catch { }
  }
  if ($ready) {
    Write-Host '[start-dev] API ready' -ForegroundColor DarkGray
  } else {
    Write-Host '[start-dev] API not ready yet; starting web anyway (see .dev-logs)' -ForegroundColor DarkYellow
  }

  $aghReady = $false
  for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 250
    try {
      $r = Invoke-WebRequest -Uri "http://127.0.0.1:$aghPort/" -UseBasicParsing -TimeoutSec 1
      if ($r.StatusCode -eq 200) { $aghReady = $true; break }
    } catch { }
  }
  if ($aghReady) {
    Write-Host '[start-dev] AGH web ready' -ForegroundColor DarkGray
  } else {
    Write-Host '[start-dev] AGH web not ready (see .dev-logs/agh.err.log)' -ForegroundColor DarkYellow
    if (Test-Path (Join-Path $LogDir 'agh.err.log')) {
      Get-Content (Join-Path $LogDir 'agh.err.log') -Tail 8 | ForEach-Object {
        Write-Host "  $_" -ForegroundColor DarkYellow
      }
    }
  }

  Write-Host '[start-dev] foreground web (Vite output below)' -ForegroundColor Cyan
  Write-Host '----------------------------------------' -ForegroundColor DarkGray
  Set-Location $WebDir
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
