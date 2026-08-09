# Ensure a local Postgres is available for Alembic / API development.
# Prefer Docker Compose when the engine is healthy; otherwise use a
# workspace-local portable PostgreSQL under .tools/pgsql-complete (no system install).
#
# Root cause this addresses:
#   Docker Desktop Linux engine requires WSL2. If WSL is missing/broken,
#   com.docker.service starts then stops and localhost:5432 refuses connections.
#   Symptom: alembic ConnectionRefusedError on 127.0.0.1:5432.

param(
    [int]$Port = 5432,
    [string]$DbUser = "stratiq",
    [string]$Password = "stratiq",
    [string]$Database = "stratiq"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Test-TcpPort([int]$PortToTest) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect("127.0.0.1", $PortToTest, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(800)
        if (-not $ok) { return $false }
        $client.EndConnect($iar) | Out-Null
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

function Test-DockerEngine {
    try {
        $prev = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        docker info 1>$null 2>$null
        $ok = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = $prev
        return $ok
    } catch {
        return $false
    }
}

Write-Output "=== StratIQ Postgres ensure ==="

if (Test-TcpPort $Port) {
    Write-Output "Postgres already listening on port $Port"
    exit 0
}

if (Test-DockerEngine) {
    Write-Output "Docker engine healthy - starting compose postgres"
    if (-not (Test-Path (Join-Path $Root ".env"))) {
        Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root ".env")
    }
    docker compose up -d postgres
    $deadline = (Get-Date).AddMinutes(2)
    do {
        Start-Sleep -Seconds 3
        docker compose exec -T postgres pg_isready -U $DbUser 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Output "POSTGRES_READY (docker)"
            exit 0
        }
    } while ((Get-Date) -lt $deadline)
    Write-Output "Docker postgres failed healthcheck; falling back to portable Postgres"
} else {
    $svc = Get-Service com.docker.service -ErrorAction SilentlyContinue
    $status = if ($svc) { $svc.Status } else { "missing" }
    Write-Output "Docker engine unavailable (service=$status). WSL2 is required for Docker Desktop Linux containers."
    Write-Output "Falling back to workspace-local portable PostgreSQL."
}

$Tools = Join-Path $Root ".tools"
$ExtractRoot = Join-Path $Tools "pgsql-complete"
$Pgsql = Join-Path $ExtractRoot "pgsql"
$Data = Join-Path $Tools "pgdata-complete"
$Log = Join-Path $Tools "postgres-complete.log"
$Zip = Join-Path $Tools "postgresql-windows-binaries.zip"
$Url = "https://get.enterprisedb.com/postgresql/postgresql-16.6-1-windows-x64-binaries.zip"

New-Item -ItemType Directory -Force -Path $Tools | Out-Null

if (-not (Test-Path (Join-Path $Pgsql "bin\pg_ctl.exe")) -or -not (Test-Path (Join-Path $Pgsql "share\postgres.bki"))) {
    if (-not (Test-Path $Zip) -or ((Get-Item $Zip).Length -lt 300000000)) {
        Write-Output "Downloading portable PostgreSQL binaries (~290MB)..."
        Invoke-WebRequest -Uri $Url -OutFile $Zip -UseBasicParsing
    }
    Write-Output "Extracting with .NET ZipFile..."
    if (Test-Path $ExtractRoot) { Remove-Item $ExtractRoot -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $ExtractRoot | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($Zip, $ExtractRoot)
}

$Bin = Join-Path $Pgsql "bin"
$Initdb = Join-Path $Bin "initdb.exe"
$PgCtl = Join-Path $Bin "pg_ctl.exe"
$CreateUser = Join-Path $Bin "createuser.exe"
$CreateDb = Join-Path $Bin "createdb.exe"
$Psql = Join-Path $Bin "psql.exe"
$PgIsReady = Join-Path $Bin "pg_isready.exe"

if (-not (Test-Path $Data)) {
    Write-Output "Initializing data directory..."
    & $Initdb -D $Data -U postgres -A trust -E UTF8 --locale=C | Out-Null
}

Write-Output "Starting portable Postgres on port $Port..."
& $PgCtl -D $Data -l $Log -o "-p $Port" start | Out-Null
Start-Sleep -Seconds 4
& $PgIsReady -h 127.0.0.1 -p $Port
if ($LASTEXITCODE -ne 0) {
    if (Test-Path $Log) { Get-Content $Log -Tail 40 }
    throw "Portable Postgres failed to start (see $Log)"
}

& $CreateUser -U postgres -h 127.0.0.1 -p $Port $DbUser 2>$null | Out-Null
& $Psql -U postgres -h 127.0.0.1 -p $Port -d postgres -c "ALTER USER $DbUser WITH PASSWORD '$Password' LOGIN;" | Out-Null
& $CreateDb -U postgres -h 127.0.0.1 -p $Port -O $DbUser $Database 2>$null | Out-Null

Write-Output "POSTGRES_READY (portable) port=$Port user=$DbUser db=$Database"
Write-Output ("DATABASE_URL=postgresql+asyncpg://" + $DbUser + ":" + $Password + "@127.0.0.1:" + $Port + "/" + $Database)
exit 0
