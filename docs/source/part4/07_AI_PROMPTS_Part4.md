# 07_AI_PROMPTS.md — Part 4

## Prompt Governance
Every production prompt should have a unique identifier, version, purpose, input schema, output schema, evidence rules, failure behavior and evaluation cases.

## Structured Output
Prefer schema-constrained outputs for KPI extraction, business health, root cause, risk, opportunity, recommendation and Decision Intelligence Cards.

## Hallucination Controls
Prompts must instruct the model to use supplied evidence for factual claims, distinguish calculation from interpretation, never invent missing values, state insufficient evidence and preserve source references.

## Evaluation
Maintain test cases for correct extraction, missing evidence, conflicting evidence, ambiguous KPI names, incorrect units and out-of-period questions. Evaluate correctness and evidence grounding.

## Model Abstraction
Application code must call a model-provider interface rather than embedding provider-specific logic throughout the application, allowing future model changes without rewriting business services.
