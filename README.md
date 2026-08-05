# StratIQ

**AI-powered strategic intelligence platform** — ingest documents, extract KPIs with evidence, and chat with your data using RAG.

---

## Architecture Overview

```
apps/
  api/          FastAPI backend (Clean Architecture)
  web/          Frontend (stub, nginx in docker-compose)
docker-compose.yml
.env.example
docs/
  ARCHITECTURE_VALIDATION.md
```

### Clean Architecture layers

| Layer | Path | Responsibility |
|---|---|---|
| Domain | `src/stratiq/domain/` | Entities, enums, domain exceptions |
| Application | `src/stratiq/application/` | Use cases, port interfaces |
| Infrastructure | `src/stratiq/infrastructure/` | DB, storage, AI clients, vector store |
| Interface | `src/stratiq/interface/` | FastAPI routers, schemas, DI |

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ and [uv](https://github.com/astral-sh/uv)

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY and JWT_SECRET
```

### 2. Start all services

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

---

## Running Tests

```bash
cd apps/api
uv sync
uv run pytest
```

Run with coverage:

```bash
uv run pytest --cov=stratiq --cov-report=term-missing
```

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/auth/register` | POST | Create a new user account |
| `/api/v1/auth/login` | POST | Obtain access + refresh tokens |
| `/api/v1/auth/refresh` | POST | Rotate refresh token |
| `/api/v1/auth/logout` | POST | Blacklist current access token |
| `/api/v1/auth/me` | GET | Get current user profile |
| `/api/v1/documents` | POST | Upload a document (PDF/XLSX/CSV) |
| `/api/v1/documents` | GET | List documents |
| `/api/v1/documents/{id}` | GET | Get document by ID |
| `/api/v1/documents/{id}/process` | POST | Enqueue document for processing |
| `/api/v1/documents/{id}` | DELETE | Delete document |
| `/api/v1/kpis` | GET | List KPIs (filter by domain/document) |
| `/api/v1/kpis/{id}` | GET | Get KPI by ID |
| `/api/v1/kpis/{id}/evidence` | GET | Get evidence chunks for a KPI |
| `/api/v1/dashboard` | GET | Aggregated KPI dashboard |
| `/api/v1/chat/sessions` | POST | Create a chat session |
| `/api/v1/chat/sessions` | GET | List chat sessions |
| `/api/v1/chat/sessions/{id}/messages` | GET | List messages in a session |
| `/api/v1/chat/sessions/{id}/messages` | POST | Post a message (RAG response) |

---

## Document Processing Pipeline

```
Upload → POST /documents
             ↓
         (DB: status=uploaded, file stored locally)
             ↓
Process → POST /documents/{id}/process
             ↓
         ARQ job enqueued → Worker picks up
             ↓
         Parse (PDF/XLSX/CSV) → Markdown
             ↓
         SemanticChunker → Chunks
             ↓
         Embed (OpenAI) → Qdrant upsert
             ↓
         LLM domain detect + KPI extraction (JSON with evidence_chunk_ids)
             ↓
         DB: KPIs saved, status=ready
```

---

## Configuration Reference

All settings are via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | postgresql+asyncpg://... | Async PostgreSQL URL |
| `REDIS_URL` | redis://localhost:6379/0 | Redis URL |
| `QDRANT_URL` | http://localhost:6333 | Qdrant HTTP URL |
| `QDRANT_COLLECTION` | stratiq_chunks | Qdrant collection name |
| `JWT_SECRET` | *(required)* | JWT signing secret |
| `JWT_ACCESS_TTL_MINUTES` | 30 | Access token TTL |
| `JWT_REFRESH_TTL_DAYS` | 7 | Refresh token TTL |
| `STORAGE_PATH` | /tmp/stratiq_storage | Local file storage root |
| `OPENAI_API_KEY` | *(required)* | API key for LLM/embeddings |
| `OPENAI_BASE_URL` | https://api.openai.com/v1 | Compatible API base URL |
| `OPENAI_CHAT_MODEL` | gpt-4o-mini | Chat completion model |
| `OPENAI_EMBEDDING_MODEL` | text-embedding-3-small | Embedding model |
| `CORS_ORIGINS` | http://localhost:3000 | Comma-separated CORS origins |

---

## Worker

Run the ARQ background worker:

```bash
cd apps/api
arq stratiq.worker.WorkerSettings
```

---

## Technology Stack

- **Python 3.12** with full type hints
- **FastAPI** + **Pydantic v2** + **pydantic-settings**
- **SQLAlchemy 2.0 async** + **asyncpg** + **Alembic**
- **python-jose** (JWT) + **passlib[bcrypt]** (passwords)
- **redis asyncio** (token storage) + **ARQ** (task queue)
- **qdrant-client** (vector search)
- **httpx** (OpenAI-compatible API calls)
- **pypdf** + **openpyxl** + **pandas** (document parsing)
- **pytest** + **pytest-asyncio** + **aiosqlite** (testing)
