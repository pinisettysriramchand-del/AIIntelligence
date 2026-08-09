# Backup PostgreSQL (StratIQ)

# Usage (cmd):
#   powershell -NoProfile -File scripts\backup-postgres.ps1
#
# Env overrides:
#   DATABASE_URL, PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE

param(
    [string]$OutDir = "",
    [string]$HostName = "127.0.0.1",
    [int]$Port = 5432,
    [string]$User = "stratiq",
    [string]$Password = "stratiq",
    [string]$Database = "stratiq"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $OutDir) {
    $OutDir = Join-Path $Root "backups\postgres"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# Prefer portable tools, then PATH
$pgDump = $null
$portable = Join-Path $Root ".tools\pgsql\bin\pg_dump.exe"
if (Test-Path $portable) {
    $pgDump = $portable
    $env:Path = "$(Join-Path $Root '.tools\pgsql\bin');$env:Path"
} else {
    $cmd = Get-Command pg_dump -ErrorAction SilentlyContinue
    if ($cmd) { $pgDump = $cmd.Source }
}

if (-not $pgDump) {
    Write-Error "pg_dump not found. Start portable Postgres (.tools) or install client tools / use Docker."
}

if ($env:PGPASSWORD) { $Password = $env:PGPASSWORD }
if ($env:PGUSER) { $User = $env:PGUSER }
if ($env:PGDATABASE) { $Database = $env:PGDATABASE }
if ($env:PGHOST) { $HostName = $env:PGHOST }
if ($env:PGPORT) { $Port = [int]$env:PGPORT }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outFile = Join-Path $OutDir "stratiq_$stamp.sql"
$env:PGPASSWORD = $Password

Write-Output "Dumping $Database from ${HostName}:$Port ..."
& $pgDump -h $HostName -p $Port -U $User -d $Database -F p -f $outFile
if ($LASTEXITCODE -ne 0) {
    Write-Error "pg_dump failed with exit $LASTEXITCODE"
}

# Compress with .NET (no external gzip dependency)
Add-Type -AssemblyName System.IO.Compression.FileSystem
$gzPath = "$outFile.gz"
if (Test-Path $gzPath) { Remove-Item $gzPath -Force }
$inStream = [System.IO.File]::OpenRead($outFile)
$outStream = [System.IO.File]::Create($gzPath)
$gzip = New-Object System.IO.Compression.GZipStream($outStream, [System.IO.Compression.CompressionLevel]::Optimal)
$inStream.CopyTo($gzip)
$gzip.Close()
$outStream.Close()
$inStream.Close()
Remove-Item $outFile -Force

$size = (Get-Item $gzPath).Length
Write-Output "OK: $gzPath ($size bytes)"
Write-Output "Retain policy: keep 14 local days; copy off-host weekly (see docs/ops/DR_RUNBOOK.md)."
