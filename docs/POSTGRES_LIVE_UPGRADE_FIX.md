# Live Postgres / Alembic unblock — root cause & fix

**Date:** 2026-08-09

## Root cause

Live `alembic upgrade` failed with `ConnectionRefusedError` on `127.0.0.1:5432` because **no Postgres was listening**.

Why Docker Compose could not provide it:

1. `com.docker.service` was **Stopped** (Manual).
2. After elevated start, the service briefly ran then **stopped again**.
3. `wsl` is **not installed / not usable** on this machine (`wsl --status` shows install help only).
4. Docker Desktop **Linux engine requires WSL2**. Without WSL, the `dockerDesktopLinuxEngine` pipe disappears and Compose Postgres never starts.

Secondary issues found while fixing:

- Missing `.env` blocked some Compose invocations (copied from `.env.example`).
- PowerShell `Expand-Archive` hung / left incomplete `pgsql` extract; `.NET ZipFile.ExtractToDirectory` works.

## Fix applied

1. Added `scripts/ensure-postgres.ps1`:
   - Prefer healthy Docker Compose Postgres
   - Else download/run **workspace-local portable PostgreSQL 16** under `.tools/` (gitignored)
2. Started portable Postgres; created role/db `stratiq`/`stratiq`
3. Verified Alembic against it

## Verification evidence

```
uv run alembic upgrade head
→ Running upgrade  -> 001_initial
→ Running upgrade 001_initial -> 002_decision_intelligence
uv run alembic current
→ 002_decision_intelligence (head)
```

Downgrade/re-upgrade cycle: run after this note if not already completed in same session.

## Long-term (Docker) fix for the machine

Install/enable WSL2, then restart Docker Desktop:

```powershell
wsl --install
# reboot if prompted
# open Docker Desktop until Engine running
cd D:\AIIntelligence
docker compose up -d postgres
```

Until then, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ensure-postgres.ps1
cd apps\api
$env:DATABASE_URL='postgresql+asyncpg://stratiq:stratiq@127.0.0.1:5432/stratiq'
uv run alembic upgrade head
```
