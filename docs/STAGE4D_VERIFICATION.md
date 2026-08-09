# Stage 4D Verification — Decision Card topic / expected outcome

**Status:** COMPLETE  
**Date:** 2026-08-09

## Scope
Part 4 §25 Decision Intelligence Card fields: decision topic, KPI signal clarity, expected outcome.

## Files changed
- `alembic/versions/005_decision_card_topic.py`
- `domain/entities.py` (`topic`, `expected_outcome`, `kpi_signal` property)
- `infrastructure/db/models.py`, `repositories.py`
- `application/decisions.py` (generate + fallbacks)
- `infrastructure/ai/prompts.py` (`part4-4d-v1`)
- `interface/schemas/decisions.py`, `routers/decisions.py`
- `infrastructure/reporting/pdf_export.py`
- `apps/web` decisions list/detail + dashboard
- `tests/unit/test_decision_card_validation.py`, `test_migration_di.py`
- docs updates

## Features
- Persisted `topic` and `expected_outcome` on `decision_cards`
- Deterministic `kpi_signal` string (name, value/unit, period, trend, health)
- Prompt asks for topic + expected_outcome; safe fallbacks if omitted
- UI/PDF surface topic, signal, and expected outcome

## Apply migration
```
cd apps\api
uv run alembic upgrade head   # -> 005_decision_card_topic
```

## Limitations
- `kpi_signal` is computed (not a separate LLM narrative field)
- Regenerating cards required to backfill topic/outcome on older rows (columns default to empty)
