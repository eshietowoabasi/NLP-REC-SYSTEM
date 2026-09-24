#!/usr/bin/env bash
# Restore a backup made by scripts/backup.sh. THIS REPLACES CURRENT DATA.
# Usage: scripts/restore.sh backups/db-YYYYmmdd-HHMMSS.dump backups/files-YYYYmmdd-HHMMSS.tar.gz
set -euo pipefail
COMPOSE=${COMPOSE:-"docker compose -f docker-compose.yml -f docker-compose.prod.yml"}
DB_DUMP=${1:?database dump file}
FILES=${2:?files archive}
read -r -p "This replaces the database and all uploaded files. Type 'restore' to continue: " answer
[ "$answer" = "restore" ] || { echo "Aborted."; exit 1; }

$COMPOSE stop backend worker scheduler
$COMPOSE exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < "$DB_DUMP"
$COMPOSE run --rm -T --no-deps backend sh -c 'rm -rf /data/raw/* /data/reports/* && tar -C /data -xzf -' < "$FILES"
$COMPOSE start backend worker scheduler
$COMPOSE exec backend flask db upgrade   # in case the backup predates the current schema
echo "Restore complete."
