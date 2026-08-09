# 05_CURSOR_RULES.md — Part 3

## AI Engineering Rules
- Evidence before inference.
- Never fabricate KPI values.
- Preserve source references.
- Return confidence where meaningful.
- Version prompts.
- Separate deterministic calculations from LLM reasoning.
- Validate structured LLM output.
- Retry transient AI failures safely.

## Data Rules
Validate uploads, never trust client metadata, use parameterized queries/ORM, keep secrets out of source code, and audit important actions.

## Testing Rules
Every new module requires unit tests. Critical workflows require integration tests. AI components require fixture-based tests where possible.
