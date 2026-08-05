FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

RUN pip install --no-cache-dir uv \
    && uv pip install --system --no-cache -e .

COPY src ./src
COPY alembic.ini .
COPY alembic ./alembic

# ── API stage ─────────────────────────────────────────────────────────────────
FROM base AS api
EXPOSE 8000
CMD ["uvicorn", "stratiq.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ── Worker stage ──────────────────────────────────────────────────────────────
FROM base AS worker
CMD ["arq", "stratiq.worker.WorkerSettings"]
