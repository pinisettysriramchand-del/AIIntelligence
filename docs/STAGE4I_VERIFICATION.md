# Stage 4I Verification — Prompt Registry

**Status:** COMPLETE  
**Date:** 2026-08-09

## Scope
Part 4 AI prompt governance: unique id, version, purpose, input/output schemas, evidence rules, failure behavior, evaluation cases.

## Files changed
- `infrastructure/ai/prompt_registry.py`
- `infrastructure/ai/prompts.py` (thin re-exports)
- `application/{chat,processing,decisions}.py` (render from registry)
- `interface/routers/ai_governance.py` + app/test wiring
- `docs/adr/ADR-007-prompt-registry.md`
- `tests/unit/test_prompt_registry.py`
- docs updates

## Registered prompts
| ID | Purpose |
|----|---------|
| `rag.chat` | Evidence-grounded Q&A |
| `kpi.domain_detect` | Domain classification |
| `kpi.extract` | KPI extraction w/ evidence ids |
| `di.decision_cards` | Decision Intelligence cards |

Registry version: **`part4-4i-v1`**

## Eval scenarios covered
`correct_extraction`, `missing_evidence`, `conflicting_evidence`, `ambiguous_kpi_names`, `incorrect_units`, `out_of_period`

## API
- `GET /api/v1/ai/prompts`
- `GET /api/v1/ai/prompts/{prompt_id}`

## Limitations
- Eval cases are fixtures + structural validators, not automated live-LLM scoring
- Prompt bodies are code-managed (no CMS UI)
