# Stage 4G Verification — Disaster Recovery Runbook

**Status:** COMPLETE  
**Date:** 2026-08-09

## Scope
Part 4 §21: automated PostgreSQL backups, object-storage versioning guidance, configuration backup, documented recovery procedures, defined RPO/RTO.

## Files changed
- `docs/ops/DR_RUNBOOK.md` — RPO/RTO, backup/restore, severity, drill checklist
- `scripts/backup-postgres.ps1` / `backup-postgres.sh`
- `scripts/restore-postgres.ps1` / `restore-postgres.sh`
- `scripts/backup-config.ps1`
- `.gitignore` — ignore `backups/`
- `tests/unit/test_dr_runbook.py`
- docs updates

## Features
| Target | RPO | RTO |
|--------|-----|-----|
| PostgreSQL | 24h | 4h |
| Object storage | 24h | 4h |
| Config | 24h | 1h |
| Qdrant | 24h or rebuild | 8h |
| Redis | accept loss | 30m |

## Operator commands (cmd)
```bat
powershell -NoProfile -File scripts\backup-postgres.ps1
powershell -NoProfile -File scripts\backup-config.ps1
powershell -NoProfile -File scripts\restore-postgres.ps1 -DumpFile backups\postgres\<file>.sql.gz -Force
```

## Limitations
- Daily logical dumps (not continuous WAL shipping)
- Local `backups/` is not off-site HA by itself
- Qdrant rebuild is manual/reprocess until a dedicated job exists
- No quarterly drill executed in this stage (checklist provided)
