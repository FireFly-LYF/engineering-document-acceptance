# Start EDA workbench + API + AGH (foreground Vite).
# Usage (from repo root): .\start.ps1   or double-click start.cmd
# First-time / new machine: run .\setup.ps1 first.

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
if (-not $Root) { $Root = Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location -LiteralPath $Root

$EdaRel = 'engineering-document-acceptance'
$AghCliRel = 'agnes-harness\packages\cli\dist\local\agnes.mjs'
$StartDevRel = Join-Path $EdaRel 'start-dev.ps1'
$ServerNmRel = Join-Path $EdaRel 'server\node_modules'
$WebNmRel = Join-Path $EdaRel 'web\node_modules'

function Fail([string]$Msg) {
  Write-Host "[start] $Msg" -ForegroundColor Red
  Write-Host "[start] First install/build:  .\setup.ps1" -ForegroundColor Yellow
  exit 1
}

if (-not (Test-Path -LiteralPath $StartDevRel -PathType Leaf)) { Fail "missing .\$StartDevRel" }
if (-not (Test-Path -LiteralPath $AghCliRel -PathType Leaf)) { Fail "AGH CLI not found: .\$AghCliRel" }
if (-not (Test-Path -LiteralPath $ServerNmRel)) { Fail "EDA server deps missing: .\$ServerNmRel" }
if (-not (Test-Path -LiteralPath $WebNmRel)) { Fail "EDA web deps missing: .\$WebNmRel" }

Write-Host "[start] repo root = ." -ForegroundColor Cyan
Write-Host "[start] launching .\$StartDevRel ..." -ForegroundColor Cyan
Write-Host "[start] Ctrl+C stops Vite and background API/AGH." -ForegroundColor DarkGray

& ".\$StartDevRel"
exit $LASTEXITCODE