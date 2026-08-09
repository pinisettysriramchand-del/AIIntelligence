# ADR-003: Qdrant for Vector Retrieval

**Status:** Accepted  
**Date:** 2026-08-09  
**Part 3 ref:** Architecture §14, §17

## Context

RAG chat and evidence-backed Decision Intelligence need semantic retrieval over document chunks with metadata filters (document/user scope) and citation attachment.

## Decision

Use **Qdrant** as the vector store for chunk embeddings (`qdrant_collection`, OpenAI-compatible embedding dimensions from settings).

## Alternatives considered

| Option | Why not |
|--------|---------|
| pgvector only | Viable later; Qdrant keeps vector ops isolated from OLTP load |
| Pinecone / managed only | Harder local reproducible Compose for MVP |
| FAISS in-process | Weak multi-worker durability and filtering story |

## Consequences

- RAG pipeline: parse → chunk → embed → upsert → retrieve → cite.
- Vectors are not the source of truth for document status (Postgres remains authoritative).
- Reranking is optional/deferred; retrieval must still refuse unsupported claims when evidence is thin.
