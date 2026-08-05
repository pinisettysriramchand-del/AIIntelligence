# StratIQ

AI Decision Intelligence Platform — **MVP (Stages 1 + 2 accepted)**

> From Enterprise Data to Executive Decisions.

## Stack

- `apps/api` — FastAPI Clean Architecture (Auth, Documents, KPI, Dashboard, Chat, Decisions, Reports)
- `apps/web` — Next.js executive UI
- PostgreSQL · Redis · Qdrant
- ARQ worker for async document + decision pipeline

## Quick start (Docker)

1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
2. `docker compose up --build`
3. Open http://localhost:3000 and API docs at http://localhost:8000/docs

## Local API tests

```bat
cd apps\api
uv sync --extra dev
uv run pytest -q
```

## Stage status

- Architecture validation: approved
- Stage 1 (Analytical MVP): **accepted**
- Stage 2 (Decision Intelligence): **accepted**

See `docs/STAGE1_STATUS.md` and `docs/STAGE2_STATUS.md`.
