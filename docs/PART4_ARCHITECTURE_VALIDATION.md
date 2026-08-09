# Part 4 Architecture Validation — Enterprise Hardening

**Status:** Stage 4A COMPLETE — AWAITING APPROVAL for next stage  
**Date:** 2026-08-09  
**Sources:** `docs/source/part4/` (01–03, 05–07)  
**Baseline:** Part 3 ACCEPTED · OTEL on master  

---

## Stage 4A result

**DONE.** Alembic revision `002_decision_intelligence` creates `decision_cards` and `executive_reports` (with FKs/indexes) and supports downgrade.

| Check | Result |
|-------|--------|
| Migration file | `apps/api/alembic/versions/002_decision_intelligence.py` |
| Head | `002_decision_intelligence` (revises `001_initial`) |
| Unit tests | `tests/unit/test_migration_di.py` |

Apply on environments already at `001_initial`:
```
cd apps/api
alembic upgrade head
```
Rollback:
```
alembic downgrade 001_initial
```

---

## Verdict (overall Part 4)

**CONDITIONAL FAIL** remains for full Part 4 until later stages. 4A closes the schema-truth blocker for DI tables.

---

## Scorecard

| # | Requirement | Verdict | Notes |
|---|-------------|---------|-------|
| 1 | KPI Intelligence (§24) | FAIL | Flat KPI only; no definition/observation split; meaning/confidence/dimensions thin; calc not deterministic |
| 2 | Decision Cards (§25) | CONDITIONAL PASS | Core fields present; missing **topic**, **expected outcome** |
| 3 | Data quality (§26) | FAIL | No DQ detector/API/UI warnings |
| 4 | Traceability (§27) | FAIL | No Part 4 matrix yet |
| 5 | Enterprise data (§18) | FAIL | No orgs; no jobs table; DI tables missing from Alembic initial migration |
| 6 | Reliability (§20) | FAIL | No idempotent reprocess, retries/DLQ, job entity |
| 7 | Disaster recovery (§21) | FAIL | No RPO/RTO / backup runbook |
| 8 | Observability (§22) | CONDITIONAL PASS | `/metrics` + OTEL exist; weak request/job/AI correlation IDs |
| 9 | UI L1/L2/L3 + charts | FAIL | Flat dashboard text; no chart library |
| 10 | Prompt governance | FAIL | Thin `part3-v1`; inline extract prompts; no eval cases |
| 11 | Model ports | PASS | `LLMClient` / embeddings / vector / storage / queue |

---

## Critical findings

1. **Alembic gap:** ORM has `decision_cards` / `executive_reports`, but `001_initial` migration may not create them — Compose `migrate` can leave DI tables missing.
2. **KPI model** is extraction-shaped, not Part 4 “definition + observation + deterministic calc.”
3. **Data quality** is product-visible only as forecast insufficient-history, not a DQ system.
4. **Dashboard** does not implement executive L1 → explanation L2 → action L3 with charts.

---

## Proposed stages (smallest production-ready slices)

| Stage | Scope |
|-------|--------|
| **4A** | Schema truth: Alembic migration for DI tables (+ any required indexes); upgrade/rollback check |
| **4B** | KPI Intelligence MVP: meaning, confidence, dimensions; persist prior/trend when computable; tabular deterministic path |
| **4C** | Data-quality warnings: detect + API + UI banners |
| **4D** | Decision Card Part 4 fields: `topic`, `expected_outcome` (+ signal clarity); tests |
| **4E** | Reliability: processing jobs, idempotent reprocess, ARQ retries/DLQ |
| **4F** | Correlation IDs across request → job → AI (OTEL attributes) |
| **4G** | DR runbook: RPO/RTO + backup procedures |
| **4H** | UI L1/L2/L3 + minimal charts |
| **4I** | Prompt registry (ID/version/schemas/eval cases) |
| **4J** | Traceability matrix doc |

**Recommended first approval:** **4A** (blocker), then **4B+4C**, then **4D**.

### Out of scope until later
Full multi-tenancy/orgs, ERP connectors, streaming, knowledge graphs, autonomous decision execution, LangGraph rewrite.

---

## Approval gate (next)

Stage 4A is complete. Reply with one of:

1. **Approve Stage 4B** — KPI Intelligence MVP
2. **Approve Stage 4B+4C** — KPI + data quality
3. **Approve Stage 4D** — Decision Card topic/expected_outcome
4. **Request git commit** of 4A
5. **Overrides**
