# StratIQ API (Stage 1)

## Run locally

```bash
uv sync --extra dev
uv run uvicorn stratiq.main:app --reload --app-dir src
uv run arq stratiq.worker.WorkerSettings
uv run pytest
```

OpenAPI: http://localhost:8000/docs
