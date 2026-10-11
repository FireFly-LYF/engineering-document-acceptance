# Install monorepo dependencies and build AGH local CLI.
# Usage: .\setup.ps1   (from repo root)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
if (-not $Root) { $Root = Split-Path -Parent $MyInvocation.MyCommand.Path }
$Root = (Resolve-Path -LiteralPath $Root).Path

$Agh = Join-Path $Root 'agnes-harness'
$Eda = Join-Path $Root 'engineering-document-acceptance'
$Cli = Join-Path $Agh 'packages\cli\dist\local\agnes.mjs'

if (-not (Test-Path (Join-Path $Agh 'package.json'))) {
  throw "missing agnes-harness at $Agh"
}
if (-not (Test-Path (Join-Path $Eda 'README.md'))) {
  throw "missing engineering-document-acceptance at $Eda"
}

Write-Host "[setup] AGH: pnpm install --frozen-lockfile" -ForegroundColor Cyan
Push-Location $Agh
try {
  & pnpm.cmd install --frozen-lockfile
  if ($LASTEXITCODE -ne 0) { throw "pnpm install failed ($LASTEXITCODE)" }

  Write-Host "[setup] AGH: pnpm --filter @agnes/cli build:local" -ForegroundColor Cyan
  & pnpm.cmd --filter @agnes/cli build:local
  if ($LASTEXITCODE -ne 0) { throw "build:local failed ($LASTEXITCODE)" }
} finally {
  Pop-Location
}

if (-not (Test-Path $Cli)) {
  throw "AGH CLI missing after build: $Cli"
}
Write-Host "[setup] AGH CLI ok -> $Cli" -ForegroundColor Green

function Invoke-NpmCi([string]$Dir) {
  if (-not (Test-Path (Join-Path $Dir 'package.json'))) {
    throw "package.json not found: $Dir"
  }
  Write-Host "[setup] npm ci -> $Dir" -ForegroundColor Cyan
  Push-Location $Dir
  try {
    if (Test-Path (Join-Path $Dir 'package-lock.json')) {
      & npm.cmd ci
    } else {
      & npm.cmd install
    }
    if ($LASTEXITCODE -ne 0) { throw "npm failed in $Dir ($LASTEXITCODE)" }
  } finally {
    Pop-Location
  }
}

Invoke-NpmCi (Join-Path $Eda 'server')
Invoke-NpmCi (Join-Path $Eda 'web')
Invoke-NpmCi (Join-Path $Eda '.agh\skills\engineering-doc-generator')

Write-Host "[setup] done. Start with:" -ForegroundColor Green
Write-Host "  cd engineering-document-acceptance" -ForegroundColor DarkGray
Write-Host "  .\start-dev.ps1" -ForegroundColor DarkGray
