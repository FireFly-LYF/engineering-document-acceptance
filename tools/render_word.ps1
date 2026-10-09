param([Parameter(Mandatory=$true)][string]$InputPath,[Parameter(Mandatory=$true)][string]$OutputPdf)
$sourcePath = (Resolve-Path -LiteralPath $InputPath).Path
$pdfPath = [System.IO.Path]::GetFullPath($OutputPdf)
New-Item -ItemType Directory -Path ([System.IO.Path]::GetDirectoryName($pdfPath)) -Force | Out-Null
$wordInstance = New-Object -ComObject Word.Application
$wordInstance.Visible = $false
$wordInstance.DisplayAlerts = 0
try {
    $documentInstance = $wordInstance.Documents.Open($sourcePath,$false,$true)
    try { $documentInstance.ExportAsFixedFormat($pdfPath,17) }
    finally { $documentInstance.Close($false) }
} finally { $wordInstance.Quit() }
Write-Output 'Word PDF render complete'
