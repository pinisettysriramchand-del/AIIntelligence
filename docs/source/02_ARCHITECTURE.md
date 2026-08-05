# 02_ARCHITECTURE.md

# StratIQ MVP Architecture

## Principles
- Clean Architecture
- Modular services
- API-first
- Async Python
- Extensible by domain

## Logical Architecture
User -> Next.js UI -> FastAPI -> AI Services -> PostgreSQL/Qdrant

## Components
- Auth Service
- Document Intelligence
- KPI Intelligence
- Decision Intelligence
- Chat (RAG)
- Forecasting
- Reporting

## AI Pipeline
Upload -> Parse -> Markdown -> Chunk -> Embeddings -> Qdrant -> Retrieval -> KPI Extraction -> Decision Intelligence.

## Decision Pipeline
KPI -> Trend -> Root Cause -> Risks -> Opportunities -> Recommendation -> Forecast -> Decision Card

## Data Stores
PostgreSQL: Users, Documents, KPIs, Insights, Chats.
Qdrant: Embeddings.
Redis: Cache/Sessions.

## APIs
/auth,/documents,/kpis,/dashboard,/chat,/forecast,/reports

## Deployment
Docker Compose: frontend, backend, postgres, qdrant, redis.

## References
01_PRODUCT_REQUIREMENTS.md
03_IMPLEMENTATION_GUIDE.md
