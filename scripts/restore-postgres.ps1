# Restore PostgreSQL from a StratIQ logical dump (.sql or .sql.gz)

# Usage (cmd):
#   powershell -NoProfile -File scripts\restore-postgres.ps1 -DumpFile backups\postgres\stratiq_....sql.gz

param(
    [Parameter(Mandatory = $true)]
    [string]$DumpFile,
    [string]$HostName = "127.0.0.1",
    [int]$Port = 5432,
    [string]$User = "stratiq",
    [string]$Password = "stratiq",
    [string]$Database = "stratiq",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path $DumpFile)) {
    $candidate = Join-Path $Root $DumpFile
    if (Test-Path $candidate) { $DumpFile = $candidate }
}
if (-not (Test-Path $DumpFile)) {
    Write-Error "Dump file not found: $DumpFile"
}

$portableBin = Join-Path $Root ".tools\pgsql\bin"
if (Test-Path (Join-Path $portableBin "psql.exe")) {
    $env:Path = "$portableBin;$env:Path"
}

$psql = (Get-Command psql -ErrorAction SilentlyContinue)
if (-not $psql) {
    Write-Error "psql not found on PATH (or .tools/pgsql/bin)."
}

if ($env:PGPASSWORD) { $Password = $env:PGPASSWORD }
$env:PGPASSWORD = $Password

if (-not $Force) {
    Write-Warning "This will apply SQL into database '$Database' on ${HostName}:$Port."
    Write-Warning "Pass -Force after confirming this is a scratch/restore target."
    Write-Error "Refusing to continue without -Force (safety)."
}

$tmpSql = $DumpFile
$cleanup = $false
if ($DumpFile -like "*.gz") {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $tmpSql = Join-Path $env:TEMP ("stratiq_restore_" + [guid]::NewGuid().ToString() + ".sql")
    $inStream = [System.IO.File]::OpenRead((Resolve-Path $DumpFile))
    $gzip = New-Object System.IO.Compression.GZipStream($inStream, [System.IO.Compression.CompressionMode]::Decompress)
    $outStream = [System.IO.File]::Create($tmpSql)
    $gzip.CopyTo($outStream)
    $outStream.Close()
    $gzip.Close()
    $inStream.Close()
    $cleanup = $true
}

Write-Output "Restoring into $Database ..."
& psql -h $HostName -p $Port -U $User -d $Database -v ON_ERROR_STOP=1 -f $tmpSql
$code = $LASTEXITCODE
if ($cleanup -and (Test-Path $tmpSql)) { Remove-Item $tmpSql -Force }

if ($code -ne 0) {
    Write-Error "psql restore failed with exit $code"
}

Write-Output "Restore finished. Next: alembic upgrade head && alembic current (see docs/ops/DR_RUNBOOK.md)."
