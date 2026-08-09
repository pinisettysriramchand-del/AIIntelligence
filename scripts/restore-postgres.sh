#!/usr/bin/env bash
# Restore PostgreSQL from .sql.gz dump.
# Usage: ./scripts/restore-postgres.sh backups/postgres/stratiq_....sql.gz
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DUMP="${1:-}"
if [[ -z "$DUMP" || ! -f "$DUMP" ]]; then
  echo "Usage: $0 <dump.sql.gz|dump.sql>" >&2
  exit 1
fi
if [[ "${FORCE:-}" != "1" ]]; then
  echo "Refusing without FORCE=1 (safety). Example: FORCE=1 $0 $DUMP" >&2
  exit 1
fi

DB_USER="${POSTGRES_USER:-stratiq}"
DB_NAME="${POSTGRES_DB:-stratiq}"

if docker compose -f "$ROOT/docker-compose.yml" ps postgres 2>/dev/null | grep -q "Up\|running"; then
  echo "Restoring via docker compose service postgres..."
  if [[ "$DUMP" == *.gz ]]; then
    gzip -dc "$DUMP" | docker compose -f "$ROOT/docker-compose.yml" exec -T postgres \
      psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1
  else
    docker compose -f "$ROOT/docker-compose.yml" exec -T postgres \
      psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 < "$DUMP"
  fi
else
  export PGPASSWORD="${PGPASSWORD:-stratiq}"
  if [[ "$DUMP" == *.gz ]]; then
    gzip -dc "$DUMP" | psql -h "${PGHOST:-127.0.0.1}" -p "${PGPORT:-5432}" -U "${PGUSER:-stratiq}" -d "${PGDATABASE:-stratiq}" -v ON_ERROR_STOP=1
  else
    psql -h "${PGHOST:-127.0.0.1}" -p "${PGPORT:-5432}" -U "${PGUSER:-stratiq}" -d "${PGDATABASE:-stratiq}" -v ON_ERROR_STOP=1 -f "$DUMP"
  fi
fi

echo "Restore finished. Next: alembic upgrade head (see docs/ops/DR_RUNBOOK.md)."
