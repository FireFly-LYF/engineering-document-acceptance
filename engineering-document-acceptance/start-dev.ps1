# Start API (8787) + web (5173) + AGH (4177).
# Console shows only the Vite frontend. API/AGH logs go to .dev-logs\
# Usage: .\start-dev.ps1   or from repo root: .\start.ps1
#
# CRITICAL: AGH serve MUST use EDA root as workspace (--cwd), same as server -p.
# Paths are relative to this script directory (engineering-document-acceptance).
#
# Ctrl+C / close window = stop Vite and background API/AGH.

$ErrorActionPreference = 'Stop'

$EdaRoot = $PSScriptRoot
if (-not $EdaRoot) { $EdaRoot = Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location -LiteralPath $EdaRoot

# Relative to EDA root (this script dir)
$ServerDirRel = 'server'
$WebDirRel = 'web'
$AghCliRel = Join-Path '..' 'agnes-harness\packages\cli\dist\local\agnes.mjs'
$LogDirRel = '.dev-logs'
$TsxCliRel = Join-Path $ServerDirRel 'node_modules\tsx\dist\cli.mjs'
$ViteCliRel = Join-Path $WebDirRel 'node_modules\vite\bin\vite.js'

if (-not (Test-Path -LiteralPath $ServerDirRel)) { throw "server not found: .\$ServerDirRel" }
if (-not (Test-Path -LiteralPath $WebDirRel)) { throw "web not found: .\$WebDirRel" }
if (-not (Test-Path -LiteralPath $TsxCliRel)) { throw "tsx not found: .\$TsxCliRel  (run ..\setup.ps1)" }
if (-not (Test-Path -LiteralPath $ViteCliRel)) { throw "vite not found: .\$ViteCliRel  (run ..\setup.ps1)" }
if (-not (Test-Path -LiteralPath $AghCliRel)) {
  throw @"
AGH CLI not found: $AghCliRel
From repo root run: .\setup.ps1
"@
}

New-Item -ItemType Directory -Force -Path $LogDirRel | Out-Null

# Absolute only where child processes / env require a stable cwd (not printed)
$EdaRootAbs = (Get-Location).Path
$ServerDirAbs = Join-Path $EdaRootAbs $ServerDirRel
$WebDirAbs = Join-Path $EdaRootAbs $WebDirRel
$AghCliAbs = (Resolve-Path -LiteralPath $AghCliRel).Path
$TsxCliAbs = (Resolve-Path -LiteralPath $TsxCliRel).Path
$ViteCliAbs = (Resolve-Path -LiteralPath $ViteCliRel).Path
$LogDirAbs = Join-Path $EdaRootAbs $LogDirRel

function Invoke-TaskKillSafe([int]$ProcId) {
  if (-not $ProcId -or $ProcId -eq 0) { return $false }
  $prev = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    $null = cmd.exe /c "taskkill /PID $ProcId /T /F >nul 2>&1"
    if ($LASTEXITCODE -eq 0) { return $true }
    Start-Sleep -Milliseconds 200
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

function Get-ListeningPids([int]$Port) {
  $pids = New-Object System.Collections.Generic.HashSet[int]
  $listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
  $hit = $false
  foreach ($ep in $listeners) {
    if ($ep.Port -eq $Port) { $hit = $true; break }
  }
  if (-not $hit) { return @() }

  # netstat is much faster than Get-NetTCPConnection on Windows
  $rows = netstat -ano -p tcp
  foreach ($line in $rows) {
    if ($line -notmatch 'LISTENING') { continue }
    if ($line -notmatch ":$Port\s+") { continue }
    if ($line -match '(\d+)\s*$') {
      [void]$pids.Add([int]$Matches[1])
    }
  }
  return @($pids)
}

function Test-PortFree([int]$Port) {
  $listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
  -not ($listeners | Where-Object { $_.Port -eq $Port })
}

function Stop-PortListener([int]$Port) {
  for ($attempt = 0; $attempt -lt 3; $attempt++) {
    $procIds = @(Get-ListeningPids $Port)
    if ($procIds.Count -eq 0) { return $true }
    foreach ($procId in $procIds) {
      if ($procId -and $procId -ne 0) {
        Write-Host "[start-dev] free port $Port (kill pid $procId)" -ForegroundColor DarkYellow
        if (-not (Invoke-TaskKillSafe $procId)) {
          Write-Host "[start-dev] could not kill pid $procId (Access Denied?); retry..." -ForegroundColor DarkYellow
        }
      }
    }
    Start-Sleep -Milliseconds 200
  }
  return (Test-PortFree $Port)
}

function Stop-MatchingNode([string[]]$Patterns) {
  $prev = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    $nodes = @(Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue)
    foreach ($proc in $nodes) {
      $cmd = $proc.CommandLine
      if (-not $cmd) { continue }
      foreach ($pattern in $Patterns) {
        if ($cmd -match $pattern) {
          Write-Host "[start-dev] kill leftover node pid $($proc.ProcessId)" -ForegroundColor DarkYellow
          [void](Invoke-TaskKillSafe $proc.ProcessId)
          break
        }
      }
    }
  } finally {
    $ErrorActionPreference = $prev
  }
}

function Invoke-DaemonStopTimed([int]$TimeoutMs = 5000) {
  $outLog = Join-Path $LogDirAbs 'daemon-stop.out.log'
  $errLog = Join-Path $LogDirAbs 'daemon-stop.err.log'
  $p = Start-Process -FilePath 'node.exe' `
    -ArgumentList @($AghCliAbs, 'daemon', 'stop', '--profile', 'local-dev') `
    -WorkingDirectory $EdaRootAbs `
    -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog
  if (-not $p.WaitForExit($TimeoutMs)) {
    Write-Host "[start-dev] daemon stop timed out (${TimeoutMs}ms) - skipping" -ForegroundColor DarkYellow
    [void](Invoke-TaskKillSafe $p.Id)
    return
  }
}

$apiProc = $null
$aghProc = $null
$code = 0
$prevLocation = Get-Location

try {
  $env:AGNES_PROFILE = 'local-dev'
  $env:EDA_ROOT = $EdaRootAbs

  Write-Host '[start-dev] EDA workspace = .' -ForegroundColor Cyan

  Write-Host '[start-dev] stopping previous AGH daemon (local-dev, max 5s) ...' -ForegroundColor DarkGray
  try { Invoke-DaemonStopTimed 5000 } catch { }

  Write-Host '[start-dev] cleaning leftover node / ports ...' -ForegroundColor DarkGray
  Stop-MatchingNode @(
    'daemon\.mjs|agnes\.mjs serve|agnes\.mjs -p',
    'tsx\\dist\\cli\.mjs|tsx/dist/cli\.mjs',
    'vite\\bin\\vite\.js|vite/bin/vite\.js'
  )

  [void](Stop-PortListener 4177)
  [void](Stop-PortListener 4178)
  [void](Stop-PortListener 8787)
  [void](Stop-PortListener 5173)
  Start-Sleep -Milliseconds 300

  $aghPort = 4177
  if (-not (Test-PortFree 4177)) {
    Write-Host '[start-dev] 4177 still busy - falling back to 4178' -ForegroundColor DarkYellow
    $aghPort = 4178
    [void](Stop-PortListener 4178)
  }

  if (-not (Test-PortFree 8787)) {
    $reuseApi = $false
    try {
      $h = Invoke-WebRequest -Uri 'http://127.0.0.1:8787/api/health' -UseBasicParsing -TimeoutSec 1
      if ($h.StatusCode -eq 200) { $reuseApi = $true }
    } catch { }
    if ($reuseApi) {
      Write-Host '[start-dev] port 8787 busy but healthy - reusing existing API' -ForegroundColor DarkYellow
    } else {
      throw 'port 8787 is stuck and not a healthy EDA API. Close the owning process in Task Manager, then retry.'
    }
  }

  $env:AGNES_WEB_ORIGIN = "http://127.0.0.1:$aghPort"
  Set-Content -Path (Join-Path $LogDirRel 'agh-web-origin.txt') -Value $env:AGNES_WEB_ORIGIN -Encoding utf8

  Write-Host "[start-dev] AGH Web origin -> $($env:AGNES_WEB_ORIGIN)" -ForegroundColor Cyan

  if (Test-PortFree 8787) {
    Write-Host '[start-dev] background API  -> http://127.0.0.1:8787' -ForegroundColor DarkGray
    $apiProc = Start-Process -FilePath 'node.exe' `
      -ArgumentList @($TsxCliAbs, 'watch', 'src/index.ts') `
      -WorkingDirectory $ServerDirAbs `
      -PassThru `
      -WindowStyle Hidden `
      -RedirectStandardOutput (Join-Path $LogDirAbs 'api.out.log') `
      -RedirectStandardError (Join-Path $LogDirAbs 'api.err.log')
  }

  Write-Host "[start-dev] background AGH  -> http://127.0.0.1:$aghPort (serve --cwd .)" -ForegroundColor DarkGray
  $aghProc = Start-Process -FilePath 'node.exe' `
    -ArgumentList @($AghCliAbs, 'serve', '--cwd', $EdaRootAbs, '--profile', 'local-dev', '--port', "$aghPort") `
    -WorkingDirectory $EdaRootAbs `
    -PassThru `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDirAbs 'agh.out.log') `
    -RedirectStandardError (Join-Path $LogDirAbs 'agh.err.log')

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
    Write-Host '[start-dev] AGH web not ready (see .dev-logs\agh.err.log)' -ForegroundColor DarkYellow
    if (Test-Path (Join-Path $LogDirRel 'agh.err.log')) {
      Get-Content (Join-Path $LogDirRel 'agh.err.log') -Tail 8 | ForEach-Object {
        Write-Host "  $_" -ForegroundColor DarkYellow
      }
    }
  }

  Write-Host '[start-dev] foreground web (Vite). Keep this window open.' -ForegroundColor Cyan
  Write-Host '[start-dev] Ctrl+C stops Vite and also stops background API/AGH.' -ForegroundColor DarkGray
  Write-Host '----------------------------------------' -ForegroundColor DarkGray
  Set-Location -LiteralPath $WebDirAbs
  $viteStarted = Get-Date
  & node.exe $ViteCliAbs --host 127.0.0.1 --port 5173
  $code = $LASTEXITCODE
  $elapsed = ((Get-Date) - $viteStarted).TotalSeconds
  if ($elapsed -lt 3) {
    Write-Host "[start-dev] Vite exited in $([int]$elapsed)s (abnormal). Check port 5173 or .dev-logs." -ForegroundColor Red
    if ($null -eq $code -or $code -eq 0) { $code = 1 }
  }
} finally {
  Write-Host ''
  Write-Host '[start-dev] stopping background API / AGH ...' -ForegroundColor DarkGray
  Stop-Tree $apiProc
  Stop-Tree $aghProc
  try { Set-Location -LiteralPath $prevLocation.Path } catch { }
}

if ($null -eq $code) { exit 0 }
exit $code