# 03_IMPLEMENTATION_GUIDE.md — Part 4

## Implementation Standards

### Backend
Use FastAPI, Pydantic, SQLAlchemy, Alembic and pytest. Organize code by business capability.

### AI Layer
Separate prompt templates, model clients, retrieval, deterministic analytics and output validation.

### Frontend
Use reusable components and typed API clients. Every asynchronous operation must expose loading, success, empty and error states.

## Database Migration
Every schema change requires a migration, upgrade test, rollback consideration and test-data update.

## API Contract
Every endpoint requires request/response schemas, authentication rules, validation, stable error contracts, OpenAPI documentation and automated tests.

## Environment Management
Maintain Local, Test and Production configurations. Secrets must never be committed to source control.

## Release Checklist
- Tests pass
- Lint/type checks pass
- Migrations verified
- Docker build succeeds
- Security checks pass
- Critical journey verified
- Documentation updated
