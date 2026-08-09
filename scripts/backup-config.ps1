# Backup non-secret configuration artifacts for StratIQ DR.
# Usage: powershell -NoProfile -File scripts\backup-config.ps1

param(
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
if (-not $OutDir) {
    $OutDir = Join-Path $Root "backups\config\$stamp"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$copyList = @(
    ".env.example",
    "docker-compose.yml",
    "deploy\otel-collector-config.yaml",
    "pyproject.toml",
    "apps\api\alembic.ini",
    "docs\ops\DR_RUNBOOK.md"
)

foreach ($rel in $copyList) {
    $src = Join-Path $Root $rel
    if (Test-Path $src) {
        $dest = Join-Path $OutDir $rel
        $destParent = Split-Path -Parent $dest
        New-Item -ItemType Directory -Force -Path $destParent | Out-Null
        Copy-Item $src $dest -Force
    }
}

$checklist = @"
StratIQ secrets restore checklist (DO NOT put real secret values in git)
=======================================================================
Restore these from your secret vault into .env (or orchestrator secrets):

- JWT_SECRET
- DATABASE_URL (or POSTGRES_*)
- REDIS_URL
- QDRANT_URL / QDRANT_COLLECTION
- OPENAI_API_KEY / OPENAI_BASE_URL / model names
- STORAGE_PATH
- OTEL_* (if used)

After restore:
1. docker compose up -d   (or start portable Postgres + API + worker)
2. alembic upgrade head
3. GET /health
4. Login smoke test

See docs/ops/DR_RUNBOOK.md
"@
Set-Content -Path (Join-Path $OutDir "SECRETS_CHECKLIST.txt") -Value $checklist -Encoding UTF8

# Best-effort alembic history (optional)
try {
    Push-Location (Join-Path $Root "apps\api")
    $hist = & uv run alembic history 2>$null
    if ($LASTEXITCODE -eq 0 -and $hist) {
        Set-Content -Path (Join-Path $OutDir "alembic_history.txt") -Value ($hist -join "`n") -Encoding UTF8
    }
} catch {
    # ignore
} finally {
    Pop-Location
}

Write-Output "OK: config backup at $OutDir"
Write-Output "Remember: real .env is NOT copied. Use SECRETS_CHECKLIST.txt + vault."
