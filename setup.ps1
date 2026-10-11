# Install monorepo dependencies and build AGH local CLI.
# Usage (from repo root, PowerShell):
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\setup.ps1
#
# Prerequisites the script cannot install for you:
#   - Node.js >= 24.10 (includes npm + corepack)
#   - Windows: Visual Studio C++ Build Tools + Windows SDK (for AGH native helpers)
#   - Optional later: Python 3 + pymupdf (EDA audit scripts)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
if (-not $Root) { $Root = Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location -LiteralPath $Root

$Agh = 'agnes-harness'
$Eda = 'engineering-document-acceptance'
$Cli = Join-Path $Agh 'packages\cli\dist\local\agnes.mjs'
$DistDir = Join-Path $Agh 'packages\cli\dist'
$BuildLock = Join-Path $DistDir 'local.build-lock'
$RequiredPnpm = '10.34.5'
$MinNodeMajor = 24
$MinNodeMinor = 10

function Assert-Cmd([string]$Name) {
  $cmd = Get-Command $Name -ErrorAction SilentlyContinue
  if (-not $cmd) {
    throw "Missing command: $Name. Install Node.js >= $MinNodeMajor.$MinNodeMinor (with npm/corepack), reopen the terminal, then rerun .\setup.ps1"
  }
  return $cmd
}

function Get-NodeVersionParts {
  $raw = (& node.exe -p "process.versions.node").Trim()
  if ($LASTEXITCODE -ne 0 -or -not $raw) { throw 'Cannot read Node.js version' }
  $parts = $raw.Split('.')
  return [pscustomobject]@{
    Raw   = $raw
    Major = [int]$parts[0]
    Minor = [int]$parts[1]
  }
}

function Resolve-PnpmInvoker {
  # Swallow child stdout so it cannot pollute the function output stream.
  $corepack = Get-Command corepack.cmd -ErrorAction SilentlyContinue
  if (-not $corepack) { $corepack = Get-Command corepack -ErrorAction SilentlyContinue }
  if ($corepack) {
    Write-Host "[setup] enabling Corepack pnpm@$RequiredPnpm ..." -ForegroundColor DarkGray
    try { & $corepack.Source enable *> $null } catch { }
    & $corepack.Source prepare "pnpm@$RequiredPnpm" --activate *> $null
    if ($LASTEXITCODE -ne 0) {
      throw "corepack prepare pnpm@$RequiredPnpm failed. Try: corepack enable ; corepack prepare pnpm@$RequiredPnpm --activate"
    }
    return [pscustomobject]@{
      Kind   = 'corepack'
      Exe    = $corepack.Source
      Prefix = @('pnpm')
    }
  }

  $pnpmCmd = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
  if (-not $pnpmCmd) { $pnpmCmd = Get-Command pnpm -ErrorAction SilentlyContinue }
  if ($pnpmCmd) {
    Write-Host "[setup] using existing pnpm -> $($pnpmCmd.Source)" -ForegroundColor DarkGray
    return [pscustomobject]@{
      Kind   = 'pnpm'
      Exe    = $pnpmCmd.Source
      Prefix = @()
    }
  }

  throw "pnpm/corepack not found. Install Node.js >= $MinNodeMajor.$MinNodeMinor with Corepack, or: npm install -g pnpm@$RequiredPnpm"
}

function Invoke-Pnpm {
  param(
    [Parameter(Mandatory = $true)]$Invoker,
    [Parameter(Mandatory = $true)][string[]]$PnpmArgs
  )
  $all = @()
  if ($Invoker.Prefix -and $Invoker.Prefix.Count -gt 0) { $all += [string[]]$Invoker.Prefix }
  $all += $PnpmArgs
  Write-Host "[setup] $($Invoker.Kind) pnpm $($PnpmArgs -join ' ')" -ForegroundColor Cyan
  & $Invoker.Exe @all
  if ($LASTEXITCODE -ne 0) {
    throw "pnpm $($PnpmArgs -join ' ') failed (exit $LASTEXITCODE)"
  }
}

function Test-CliReady([string]$Path) {
  return (Test-Path -LiteralPath $Path -PathType Leaf)
}

function Clear-StaleBuildLock([string]$LockPath) {
  if (-not (Test-Path -LiteralPath $LockPath)) { return }
  $builders = @(
    Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
      Where-Object { $_.CommandLine -and ($_.CommandLine -match 'build-local\.ts|build:local') }
  )
  if ($builders.Count -gt 0) {
    throw "build lock exists and a builder is still running (pid $($builders[0].ProcessId)). Wait or stop it, then rerun."
  }
  Write-Host "[setup] removing stale build lock: .\$LockPath" -ForegroundColor DarkYellow
  Remove-Item -LiteralPath $LockPath -Recurse -Force
}

if (-not (Test-Path (Join-Path $Agh 'package.json'))) {
  throw "missing .\$Agh"
}
if (-not (Test-Path (Join-Path $Eda 'README.md'))) {
  throw "missing .\$Eda"
}

Write-Host "[setup] repo root = ." -ForegroundColor Cyan

Assert-Cmd 'node.exe' | Out-Null
Assert-Cmd 'npm.cmd' | Out-Null

$nodeVer = Get-NodeVersionParts
Write-Host "[setup] Node $($nodeVer.Raw)" -ForegroundColor DarkGray
if ($nodeVer.Major -lt $MinNodeMajor -or ($nodeVer.Major -eq $MinNodeMajor -and $nodeVer.Minor -lt $MinNodeMinor)) {
  throw "Need Node.js >= $MinNodeMajor.$MinNodeMinor, found $($nodeVer.Raw). Upgrade, reopen terminal, rerun .\setup.ps1"
}

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if ($py) {
  Write-Host "[setup] Python ok -> $($py.Source) (EDA audit later needs pymupdf)" -ForegroundColor DarkGray
} else {
  Write-Host "[setup] WARN: Python not found. Setup continues; EDA audit scripts need Python 3 + pymupdf." -ForegroundColor DarkYellow
}

$pnpmInvoker = Resolve-PnpmInvoker
if (-not $pnpmInvoker -or -not $pnpmInvoker.Exe) {
  throw "internal error: Resolve-PnpmInvoker returned unexpected value: $($pnpmInvoker | Out-String)"
}
Write-Host "[setup] pnpm via $($pnpmInvoker.Kind) -> $($pnpmInvoker.Exe)" -ForegroundColor DarkGray

Push-Location $Agh
try {
  Invoke-Pnpm -Invoker $pnpmInvoker -PnpmArgs @('install', '--frozen-lockfile')

  $onWindows = ($env:OS -match 'Windows')
  if ((Get-Variable -Name IsWindows -ErrorAction SilentlyContinue) -and $IsWindows) { $onWindows = $true }

  if ($onWindows) {
    $prep = Join-Path $Agh '.github\scripts\prepare-windows-native.ps1'
    if (Test-Path $prep) {
      $cache = Join-Path $env:LOCALAPPDATA 'node-gyp\Cache'
      Write-Host "[setup] Windows: prepare Node headers -> $cache" -ForegroundColor Cyan
      try {
        & $prep -CacheRoot $cache
        if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) {
          throw "exit $LASTEXITCODE"
        }
      } catch {
        Write-Host "[setup] WARN: prepare-windows-native failed: $($_.Exception.Message)" -ForegroundColor DarkYellow
        Write-Host "[setup] WARN: continuing; build:local may still work if headers/native already present." -ForegroundColor DarkYellow
      }
    }
  }

  Clear-StaleBuildLock $BuildLock

  try {
    Invoke-Pnpm -Invoker $pnpmInvoker -PnpmArgs @('--filter', '@agnes/cli', 'build:local')
  } catch {
    if (Test-CliReady $Cli) {
      Write-Host "[setup] WARN: build:local failed, but existing CLI found -> .\$Cli" -ForegroundColor DarkYellow
      Write-Host "[setup] WARN: $($_.Exception.Message)" -ForegroundColor DarkYellow
    } else {
      throw
    }
  }
} finally {
  Pop-Location
}

if (-not (Test-CliReady $Cli)) {
  throw "AGH CLI missing after build: .\$Cli. Often missing VS C++ Build Tools / Windows SDK, or nodejs.org headers download failed. Check output above."
}
Write-Host "[setup] AGH CLI ok -> .\$Cli" -ForegroundColor Green

function Invoke-NpmCi([string]$Dir) {
  if (-not (Test-Path (Join-Path $Dir 'package.json'))) {
    throw "package.json not found: .\$Dir"
  }
  Write-Host "[setup] npm -> .\$Dir" -ForegroundColor Cyan
  Push-Location $Dir
  try {
    if (Test-Path (Join-Path $Dir 'package-lock.json')) {
      & npm.cmd ci
    } else {
      & npm.cmd install
    }
    if ($LASTEXITCODE -ne 0) { throw "npm failed in $Dir (exit $LASTEXITCODE)" }
  } finally {
    Pop-Location
  }
}

Invoke-NpmCi (Join-Path $Eda 'server')
Invoke-NpmCi (Join-Path $Eda 'web')
Invoke-NpmCi (Join-Path $Eda '.agh\skills\engineering-doc-generator')

Write-Host "[setup] done. Start with:" -ForegroundColor Green
Write-Host "  .\start.ps1" -ForegroundColor DarkGray