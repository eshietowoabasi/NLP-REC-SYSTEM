#!/usr/bin/env bash
# Recreate the e2e database and its users. Needs DATABASE_URL pointing at a
# disposable database, and ADMIN_DB_URL (psql URL) that can drop/create it.
set -euo pipefail
: "${E2E_DB_NAME:?set E2E_DB_NAME}" "${ADMIN_DB_URL:?set ADMIN_DB_URL}"
psql "$ADMIN_DB_URL" -qc "DROP DATABASE IF EXISTS ${E2E_DB_NAME} WITH (FORCE)" -c "CREATE DATABASE ${E2E_DB_NAME}"
cd "$(dirname "$0")/../../../backend"
flask db upgrade >/dev/null
for spec in "admin|Admin" "planner|Curriculum Planner" "viewer|Viewer"; do
  flask create-user --username "${spec%%|*}" --email "${spec%%|*}@example.edu" --role "${spec#*|}" \
    --password "${E2E_PASSWORD:-Passw0rd!}" >/dev/null
done
echo "e2e database ready"
