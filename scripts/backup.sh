#!/usr/bin/env bash
# Back up the database and uploaded/generated files (spec §18).
# Usage: scripts/backup.sh [backup-dir]     (run from the repository root)
# Schedule nightly, e.g. cron: 30 1 * * * cd /opt/nlp-rs && scripts/backup.sh /var/backups/nlp-rs
set -euo pipefail
COMPOSE=${COMPOSE:-"docker compose -f docker-compose.yml -f docker-compose.prod.yml"}
DEST=${1:-backups}
STAMP=$(date -u +%Y%m%d-%H%M%S)
mkdir -p "$DEST"

echo "Dumping database…"
$COMPOSE exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$DEST/db-$STAMP.dump"

echo "Archiving uploads and reports…"
$COMPOSE exec -T backend tar -C /data -czf - raw reports > "$DEST/files-$STAMP.tar.gz"

# Keep the most recent 14 of each.
ls -1t "$DEST"/db-*.dump 2>/dev/null | tail -n +15 | xargs -r rm --
ls -1t "$DEST"/files-*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm --
echo "Backup written to $DEST (db-$STAMP.dump, files-$STAMP.tar.gz)"
