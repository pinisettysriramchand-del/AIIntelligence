# ADR-007: Prompt Registry for AI Governance

**Status:** Accepted  
**Date:** 2026-08-09  
**Part 4 ref:** Architecture § / AI Prompts § Prompt Governance

## Context

Part 4 requires every production prompt to carry an identifier, version, purpose, input/output schemas, evidence rules, failure behavior, and evaluation cases. Ad-hoc string constants across services make drift and untested hallucination modes likely.

## Decision

Maintain an in-code **prompt registry** (`infrastructure/ai/prompt_registry.py`):

- Canonical `PromptSpec` records for `rag.chat`, `kpi.domain_detect`, `kpi.extract`, `di.decision_cards`
- Registry version `part4-4i-v1`
- Eval cases covering extraction, missing/conflicting evidence, ambiguous names, incorrect units, out-of-period questions
- Authenticated introspection via `GET /api/v1/ai/prompts`
- Application services render templates from the registry (not duplicated literals)

## Alternatives considered

| Option | Why not |
|--------|---------|
| DB-backed prompt CMS | Overkill for MVP; harder review/diff |
| External prompt SaaS | Couples runtime to vendor; secrets/ops overhead |
| Keep free-form strings | Fails Part 4 governance acceptance |

## Consequences

- Prompt changes are code-reviewed with tests for schema + scenario coverage.
- Live LLM scoring of eval cases remains manual/CI-optional; structural validators run in unit tests.
- Future model swaps still go through `LLMClient` ports (Part 4 model abstraction).
