# 05_CURSOR_RULES.md — Part 4

## Architecture Governance
Cursor must preserve layer boundaries, dependency direction, API contracts, domain ownership and security controls.

## Error Handling
Errors must be logged appropriately, avoid leaking secrets, return stable API structures, provide actionable UI messages and preserve correlation IDs.

## Performance
Avoid N+1 queries, unbounded retrieval, blocking long AI operations in request threads and large synchronous file processing. Use background jobs for expensive work.

## Security
Never commit API keys, passwords, tokens, private certificates or production credentials. Validate file types, sizes and content before processing.

## Maintainability
Prefer clear code over clever abstractions. New abstractions must solve a demonstrated reuse or boundary requirement.
