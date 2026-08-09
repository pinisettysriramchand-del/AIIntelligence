# Ensure a local Postgres is available for Alembic / API development.
# Prefer Docker Compose when the engine is healthy; otherwise use a
# workspace-local portable PostgreSQL under .tools/pgsql (no system install).
#
# Root cause this addresses:
#   Docker Desktop Linux engine requires WSL2. If WSL is missing/broken,
#   com.docker.service starts then stops and localhost:5432 refuses connections.

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
$Pgsql = Join-Path $Tools "pgsql"
$Data = Join-Path $Tools "pgdata"
$Log = Join-Path $Tools "postgres.log"
$Zip = Join-Path $Tools "postgresql-windows-binaries.zip"
$SqlDir = Join-Path $Tools "sql"
$Url = "https://get.enterprisedb.com/postgresql/postgresql-16.6-1-windows-x64-binaries.zip"

New-Item -ItemType Directory -Force -Path $Tools | Out-Null
New-Item -ItemType Directory -Force -Path $SqlDir | Out-Null

if (-not (Test-Path (Join-Path $Pgsql "bin\pg_ctl.exe"))) {
    Write-Output "Downloading portable PostgreSQL binaries (~290MB)..."
    Invoke-WebRequest -Uri $Url -OutFile $Zip -UseBasicParsing
    Write-Output "Extracting..."
    Expand-Archive -Path $Zip -DestinationPath $Tools -Force
    if (-not (Test-Path (Join-Path $Pgsql "bin\pg_ctl.exe"))) {
        $found = Get-ChildItem $Tools -Recurse -Filter pg_ctl.exe | Select-Object -First 1
        if (-not $found) { throw "pg_ctl.exe not found after extract" }
        $Pgsql = $found.Directory.Parent.FullName
    }
}

$Bin = Join-Path $Pgsql "bin"
$Initdb = Join-Path $Bin "initdb.exe"
$PgCtl = Join-Path $Bin "pg_ctl.exe"
$Psql = Join-Path $Bin "psql.exe"

if (-not (Test-Path $Data)) {
    Write-Output "Initializing data directory..."
    & $Initdb -D $Data -U postgres -A trust -E UTF8 --locale=C | Out-Null
}

Write-Output "Starting portable Postgres on port $Port..."
& $PgCtl -D $Data -l $Log -o "-p $Port" start | Out-Null
Start-Sleep -Seconds 3

if (-not (Test-TcpPort $Port)) {
    if (Test-Path $Log) { Get-Content $Log -Tail 40 }
    throw "Portable Postgres failed to start (see $Log)"
}

$roleFile = Join-Path $SqlDir "ensure_role.sql"
@(
    'DO $$ BEGIN',
    "  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DbUser') THEN",
    "    CREATE ROLE $DbUser LOGIN PASSWORD '$Password';",
    '  END IF;',
    'END $$;'
) | Set-Content -Path $roleFile -Encoding ascii

& $Psql -U postgres -h 127.0.0.1 -p $Port -d postgres -v ON_ERROR_STOP=1 -f $roleFile | Out-Null

$checkFile = Join-Path $SqlDir "check_db.sql"
Set-Content -Path $checkFile -Encoding ascii -Value "SELECT 1 FROM pg_database WHERE datname='$Database';"
$exists = & $Psql -U postgres -h 127.0.0.1 -p $Port -d postgres -tAc -f $checkFile
if (($exists | Out-String).Trim() -ne "1") {
    $createFile = Join-Path $SqlDir "create_db.sql"
    Set-Content -Path $createFile -Encoding ascii -Value "CREATE DATABASE $Database OWNER $DbUser;"
    & $Psql -U postgres -h 127.0.0.1 -p $Port -d postgres -v ON_ERROR_STOP=1 -f $createFile | Out-Null
}

Write-Output "POSTGRES_READY (portable) port=$Port user=$DbUser db=$Database"
Write-Output ("DATABASE_URL=postgresql+asyncpg://" + $DbUser + ":" + $Password + "@127.0.0.1:" + $Port + "/" + $Database)
exit 0
