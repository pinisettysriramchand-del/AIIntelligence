#!/usr/bin/env bash
# Backup PostgreSQL via Docker Compose service "postgres" or local pg_dump.
# Usage: ./scripts/backup-postgres.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${OUT_DIR:-$ROOT/backups/postgres}"
mkdir -p "$OUT_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="$OUT_DIR/stratiq_${STAMP}.sql.gz"

if docker compose -f "$ROOT/docker-compose.yml" ps postgres 2>/dev/null | grep -q "Up\|running"; then
  echo "Dumping via docker compose service postgres..."
  docker compose -f "$ROOT/docker-compose.yml" exec -T postgres \
    pg_dump -U "${POSTGRES_USER:-stratiq}" -d "${POSTGRES_DB:-stratiq}" | gzip -c > "$OUT_FILE"
else
  echo "Dumping via local pg_dump..."
  export PGPASSWORD="${PGPASSWORD:-stratiq}"
  pg_dump -h "${PGHOST:-127.0.0.1}" -p "${PGPORT:-5432}" -U "${PGUSER:-stratiq}" -d "${PGDATABASE:-stratiq}" \
    | gzip -c > "$OUT_FILE"
fi

BYTES=$(wc -c < "$OUT_FILE" | tr -d ' ')
echo "OK: $OUT_FILE ($BYTES bytes)"
echo "See docs/ops/DR_RUNBOOK.md for retention and restore."
