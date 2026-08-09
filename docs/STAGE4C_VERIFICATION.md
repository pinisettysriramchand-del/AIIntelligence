# Stage 4C Verification — Data Quality Warnings

**Status:** COMPLETE  
**Date:** 2026-08-09

## Scope
Part 4 §26: detect missing values, duplicates, inconsistent units, invalid periods, conflicting values, insufficient history; make warnings visible.

## Files changed
- `domain/enums.py` (`DataQualityCode`)
- `application/data_quality.py`
- `domain/entities.py`, `db/models.py`, `repositories.py` (`quality_warnings` on documents)
- `alembic/versions/004_data_quality.py`
- `application/processing.py`, `application/dashboard.py`, `interface/deps.py`
- schemas/routers for documents + dashboard
- `apps/web/app/dashboard/page.tsx`, `apps/web/app/upload/page.tsx`
- `tests/unit/test_data_quality.py`

## Features
- Deterministic DQ detector over KPI sets
- Persist warnings on document after processing
- Dashboard `data_quality_warnings` + UI panel
- Upload list shows first warnings per document

## Apply migration
```
alembic upgrade head   # -> 004_data_quality
```

## Limitations
- Warnings are KPI-centric (not full row-level tabular scan of raw sheets)
- No dedicated DQ admin workflow yet
