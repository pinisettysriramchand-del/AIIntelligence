# 02_ARCHITECTURE.md — Part 4

## 18. Enterprise Data Architecture

### Transactional Store
PostgreSQL stores users, organizations, documents, processing jobs, KPI definitions, KPI observations, insights, decisions, recommendations, forecasts, chat sessions and audit events.

### Vector Store
Qdrant stores embeddings with metadata for organization, document, page/section, domain, reporting period and evidence type.

### Object Storage
Original uploads and generated reports are stored outside the transactional database.

## 19. Logical Data Flow
Source → Ingestion → Normalization → Storage → KPI Computation → AI Analysis → Decision Card → Dashboard.

## 20. Reliability
Use idempotent processing, retry policies, dead-letter handling, transaction boundaries, health checks, backups and graceful degradation.

## 21. Disaster Recovery
Production should support automated PostgreSQL backups, object-storage versioning, configuration backup and documented recovery procedures. Define RPO/RTO targets.

## 22. Observability
Use logs, metrics and traces. Correlate requests, processing jobs and AI calls using a request/job identifier.
