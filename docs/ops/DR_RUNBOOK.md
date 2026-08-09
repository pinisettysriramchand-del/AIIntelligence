# StratIQ Disaster Recovery Runbook

**Status:** Stage 4G  
**Audience:** Operators / on-call  
**Related:** Part 4 Architecture §21 · ADR-002 (Postgres) · ADR-003 (Qdrant) · ADR-004 (Redis)

---

## 1. Objectives and scope

This runbook defines **RPO/RTO targets**, **backup cadence**, and **recovery procedures** for StratIQ MVP infrastructure:

| Component | Role | Durability expectation |
|-----------|------|------------------------|
| PostgreSQL | System of record (users, documents metadata, KPIs, decisions, jobs, audit) | **Must backup** |
| Object / file storage (`STORAGE_PATH`) | Original uploads + generated reports | **Must backup** |
| Configuration (`.env`, Compose, Alembic) | Runtime secrets + schema path | **Must backup** (secrets via vault, not git) |
| Redis | Sessions, ARQ queue, DLQ list (transient) | Rebuild acceptable |
| Qdrant | Vector index | Rebuild from Postgres chunks + embeddings if needed |

Out of scope for this stage: multi-region active/active failover, automated secret rotation, customer-managed cloud DR contracts.

---

## 2. RPO / RTO targets (MVP)

| Tier | Data | RPO (max data loss) | RTO (max downtime) | Notes |
|------|------|---------------------|--------------------|-------|
| **T0** | PostgreSQL | **24 hours** | **4 hours** | Daily logical dump; restore + `alembic upgrade head` |
| **T0** | Object storage | **24 hours** | **4 hours** | Copy/snapshot of storage volume; enable versioning in cloud |
| **T1** | Configuration | **24 hours** | **1 hour** | Offline copy of non-secret config + secret vault restore |
| **T2** | Qdrant | **24 hours** *or* rebuild | **8 hours** | Prefer snapshot; else re-embed from chunks |
| **T3** | Redis | Accept loss | **30 minutes** | Empty Redis; users re-login; re-queue failed jobs from Postgres DLQ |

**Acceptance:** A release is DR-ready for §21 when these targets are documented, backup scripts exist, and a restore drill can be executed against a non-production database.

---

## 3. Backup procedures

### 3.1 PostgreSQL (automated logical dump)

**Compose / Docker Postgres**

```bash
# From repo root — creates backups/postgres/stratiq_YYYYMMDD_HHMMSS.sql.gz
./scripts/backup-postgres.sh
```

**Windows portable Postgres (`.tools/pgsql`)**

```bat
powershell -NoProfile -File scripts\backup-postgres.ps1
```

Cadence: **daily** (cron / Task Scheduler). Retain **14 days** locally; copy off-host weekly.

Verify dump non-empty:

```bat
dir backups\postgres
```

### 3.2 Object storage

1. Identify `STORAGE_PATH` (Compose volume `storage_data` or host path from `.env`).
2. Snapshot or `robocopy` / `rsync` the directory into `backups/storage/YYYYMMDD/`.
3. In cloud object stores (S3/Azure/GCS), enable **versioning** and lifecycle rules (keep noncurrent versions ≥ 14 days).

### 3.3 Configuration

```bat
powershell -NoProfile -File scripts\backup-config.ps1
```

Produces `backups/config/YYYYMMDD/` containing:

- `.env.example` (safe template)
- `docker-compose.yml`, `deploy/otel-collector-config.yaml`
- Alembic revision list (`alembic history` when DB reachable)
- `SECRETS_CHECKLIST.txt` (what must be restored from vault — **never** write real secrets into git)

Store real `.env` / JWT / API keys in an approved secret store (1Password, Azure Key Vault, AWS Secrets Manager, etc.).

### 3.4 Qdrant (optional snapshot)

If Qdrant is healthy:

```bash
curl -X POST "http://localhost:6333/collections/stratiq_chunks/snapshots"
```

Download snapshot artifacts from Qdrant’s snapshot API/storage and place under `backups/qdrant/`.

If snapshots are unavailable, plan **rebuild**: after Postgres restore, re-run embedding upsert for documents (future operator job; until then, reprocess critical documents via `POST /documents/{id}/process`).

### 3.5 Redis

No durable backup required for MVP. Document that refresh tokens and in-flight ARQ jobs are lost on Redis wipe (ADR-004).

---

## 4. Recovery procedures

### 4.1 Severity guide

| Severity | Example | Immediate action |
|----------|---------|------------------|
| **SEV-1** | Postgres volume lost / corrupt | Restore latest dump; block writes until verified |
| **SEV-2** | Storage volume lost | Restore storage backup; reconcile document `storage_path` |
| **SEV-3** | Redis / worker queue lost | Restart Redis/worker; re-queue dead-letter jobs from Postgres |
| **SEV-4** | Qdrant empty/corrupt | Restore snapshot or reprocess documents |

### 4.2 PostgreSQL restore (Compose)

1. Stop API and worker (keep Postgres up if possible).
2. Restore:

```bash
./scripts/restore-postgres.sh backups/postgres/stratiq_YYYYMMDD_HHMMSS.sql.gz
```

Windows:

```bat
powershell -NoProfile -File scripts\restore-postgres.ps1 -DumpFile backups\postgres\<file>.sql.gz
```

3. Run migrations to head:

```bat
cd apps\api
set DATABASE_URL=postgresql+asyncpg://stratiq:stratiq@127.0.0.1:5432/stratiq
uv run alembic upgrade head
uv run alembic current
```

4. Start API/worker; hit `GET /health`.
5. Spot-check: login, list documents, open a known decision card.

### 4.3 Object storage restore

1. Stop API/worker if they write to storage.
2. Restore files into `STORAGE_PATH` preserving relative keys (`{owner_id}/{doc_id}/...`).
3. Restart services; open a document that previously uploaded.

### 4.4 Configuration restore

1. Recreate `.env` from vault using `SECRETS_CHECKLIST.txt`.
2. Confirm `JWT_SECRET`, `DATABASE_URL`, `REDIS_URL`, `QDRANT_URL`, `OPENAI_API_KEY`, `STORAGE_PATH`.
3. `docker compose up -d` (or local process restart).

### 4.5 Redis recovery

1. Start empty Redis.
2. Users re-authenticate.
3. Inspect Postgres `processing_jobs` with `status=dead_letter` and re-queue via `POST /documents/{id}/process` (idempotent while active).

### 4.6 Qdrant recovery

1. Prefer snapshot restore per Qdrant docs.
2. Else: ensure Postgres chunks exist, then reprocess priority documents to rebuild vectors.

---

## 5. Drill checklist (quarterly)

- [ ] Take a fresh Postgres dump with the backup script  
- [ ] Restore into a **scratch** database (not production)  
- [ ] Confirm `alembic current` matches expected head  
- [ ] Confirm API health + one authenticated document list  
- [ ] Confirm a storage file path from the dump era still resolves  
- [ ] Record drill date, RTO measured, gaps in `docs/ops/DR_DRILL_LOG.md` (optional)

---

## 6. Contacts and escalation

| Role | Responsibility |
|------|----------------|
| On-call engineer | Execute restore steps; communicate status |
| Tech lead | Approve production restore window; SEV-1 go/no-go |
| Security | Secret vault access; rotate JWT if `.env` leaked during incident |

Update this table for your deployment environment.

---

## 7. Limitations (honest MVP)

- Default cadence is **daily** logical dumps (RPO 24h), not continuous WAL archiving.
- Local `backups/` is not off-site HA — copy off-host for real production.
- Qdrant rebuild automation is manual/reprocess-based until a dedicated rebuild job exists.
- Multi-AZ cloud failover is not configured by these scripts.
