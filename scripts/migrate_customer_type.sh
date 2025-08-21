#!/usr/bin/env bash
set -euo pipefail

# migrate_customer_type.sh
# Safe migration helper to add `customer_type` column and index to the `customers` table.
# Default: dry-run (preview only). Use --apply to perform changes.

PROGNAME=$(basename "$0")
MIGRATION_FILE="${MIGRATION_FILE:-Documents/migrations/2025-08-20_add_customer_type_column.sql}"

usage() {
  cat <<EOF
Usage: $PROGNAME [--apply] [--db DB] [--user USER] [--host HOST] [--port PORT]

Options:
  --apply           Actually apply the migration (by default script runs in dry-run/preview mode)
  --db DB           Database name (defaults to current DB prompt)
  --user USER       DB user (default: prompt)
  --host HOST       DB host (default: localhost)
  --port PORT       DB port (default: 3306)
  --migration FILE  Path to migration SQL file (default: ${MIGRATION_FILE})
  -h, --help        Show this help and exit

Examples:
  # Dry-run (preview) - will create a dump and show planned actions
  $PROGNAME --db chronotech --user gsicloud

  # Apply migration
  $PROGNAME --apply --db chronotech --user gsicloud

Notes:
  - The script will create a table-level dump of `customers` before applying changes.
  - For automation, set MYSQL_PWD env var beforehand to avoid prompts (careful with security).
EOF
}

# Defaults
APPLY=0
DB_NAME="customers"
DB_USER="gsicloud"
DB_HOST="192.168.50.101"
DB_PORT=3306

# parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --db) DB_NAME="$2"; shift 2 ;;
    --user) DB_USER="$2"; shift 2 ;;
    --host) DB_HOST="$2"; shift 2 ;;
    --port) DB_PORT="$2"; shift 2 ;;
    --migration) MIGRATION_FILE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 2 ;;
  esac
done

# Helper for prompting if empty
prompt_if_empty() {
  local varname="$1"; local promptmsg="$2"; local is_secret=${3:-0}
  eval val="\$$varname"
  if [[ -z "$val" ]]; then
    if [[ "$is_secret" -eq 1 ]]; then
      read -r -s -p "$promptmsg: " val
      echo
    else
      read -r -p "$promptmsg: " val
    fi
    eval $varname="\$val"
  fi
}

# Require mysql and mysqldump
if ! command -v mysql >/dev/null 2>&1; then
  echo "mysql client not found in PATH. Install 'mysql-client' or ensure mysql is available." >&2
  exit 1
fi
if ! command -v mysqldump >/dev/null 2>&1; then
  echo "mysqldump not found in PATH. Install 'mysql-client' or ensure mysqldump is available." >&2
  exit 1
fi

prompt_if_empty DB_USER "DB user"
prompt_if_empty DB_NAME "DB name"
prompt_if_empty DB_HOST "DB host (default: localhost)"
prompt_if_empty DB_PORT "DB port (default: 3306)"

# Password: prefer MYSQL_PWD env, otherwise prompt (keeps it out of argv)
if [[ -z "${MYSQL_PWD:-}" ]]; then
  read -r -s -p "DB password for $DB_USER: " DB_PASS
  echo
else
  DB_PASS="$MYSQL_PWD"
fi

# small helper to run mysql with provided credentials
run_mysql() {
  # usage: run_mysql "SQL" (prints result) or run_mysql "--quiet" "SQL"
  local quiet=0
  if [[ "$1" == "--quiet" ]]; then quiet=1; shift; fi
  local SQL="$1"
  MYSQL_PWD="$DB_PASS" mysql -u "$DB_USER" -h "$DB_HOST" -P "$DB_PORT" -D "$DB_NAME" -N -B -e "$SQL"
}

echo "\n== Pre-checks =="
# Version
MYSQL_VERSION=$(MYSQL_PWD="$DB_PASS" mysql -u "$DB_USER" -h "$DB_HOST" -P "$DB_PORT" -D "$DB_NAME" -se "SELECT VERSION();" 2>/dev/null || true)
echo "MySQL version: ${MYSQL_VERSION:-(unknown)}"

# Column exists?
col_exists=$(run_mysql "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE table_schema=DATABASE() AND table_name='customers' AND column_name='customer_type';" || echo "0")
idx_exists=$(run_mysql "SELECT COUNT(*) FROM information_schema.STATISTICS WHERE table_schema=DATABASE() AND table_name='customers' AND index_name='idx_customers_customer_type';" || echo "0")

echo "customer_type column present: $col_exists"
echo "idx_customers_customer_type present: $idx_exists"

if [[ "$col_exists" -gt 0 && "$idx_exists" -gt 0 && "$APPLY" -eq 0 ]]; then
  echo "Both column and index already exist. Nothing to do (dry-run). Use --apply to re-run checks or skip." 
  exit 0
fi

# Create a dump of customers table
TS=$(date +%F_%H%M%S)
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/customers_backup_${TS}.sql"

echo "Creating backup of table 'customers' to $BACKUP_FILE ..."
MYSQL_PWD="$DB_PASS" mysqldump -u "$DB_USER" -h "$DB_HOST" -P "$DB_PORT" --single-transaction --quick --lock-tables=false "$DB_NAME" customers > "$BACKUP_FILE"
if [[ $? -ne 0 ]]; then
  echo "Backup failed. Aborting." >&2
  exit 1
fi

echo "Backup created. Size: $(du -h "$BACKUP_FILE" | cut -f1)"

# Dry-run: show planned SQL and exit
if [[ "$APPLY" -eq 0 ]]; then
  echo "\n== Dry-run preview =="
  if [[ "$col_exists" -eq 0 ]]; then
    echo "Planned action: ALTER TABLE customers ADD COLUMN customer_type VARCHAR(50) NULL DEFAULT NULL;"
  else
    echo "Planned action: (column already exists - will skip ALTER)"
  fi
  if [[ "$idx_exists" -eq 0 ]]; then
    echo "Planned action: CREATE INDEX idx_customers_customer_type ON customers (customer_type);"
  else
    echo "Planned action: (index already exists - will skip CREATE INDEX)"
  fi
  echo "\nTo apply these changes run with --apply"
  exit 0
fi

# APPLY MODE
echo "\n== Apply mode =="
# Re-check inside apply to avoid race
col_exists=$(run_mysql "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE table_schema=DATABASE() AND table_name='customers' AND column_name='customer_type';" || echo "0")
idx_exists=$(run_mysql "SELECT COUNT(*) FROM information_schema.STATISTICS WHERE table_schema=DATABASE() AND table_name='customers' AND index_name='idx_customers_customer_type';" || echo "0")

set +e
if [[ "$col_exists" -eq 0 ]]; then
  echo "Adding column customer_type..."
  MYSQL_PWD="$DB_PASS" mysql -u "$DB_USER" -h "$DB_HOST" -P "$DB_PORT" -D "$DB_NAME" -e "ALTER TABLE customers ADD COLUMN customer_type VARCHAR(50) NULL DEFAULT NULL;"
  rc=$?
  if [[ $rc -ne 0 ]]; then
    echo "ERROR: ALTER TABLE failed (code $rc). Please inspect and retry. Migration aborted." >&2
    exit $rc
  fi
else
  echo "Column customer_type already exists; skipping ALTER TABLE."
fi

# Create index if missing
if [[ "$idx_exists" -eq 0 ]]; then
  echo "Creating index idx_customers_customer_type..."
  MYSQL_PWD="$DB_PASS" mysql -u "$DB_USER" -h "$DB_HOST" -P "$DB_PORT" -D "$DB_NAME" -e "CREATE INDEX idx_customers_customer_type ON customers (customer_type);"
  rc=$?
  if [[ $rc -ne 0 ]]; then
    echo "ERROR: CREATE INDEX failed (code $rc). Please inspect and retry. Migration aborted." >&2
    exit $rc
  fi
else
  echo "Index idx_customers_customer_type already exists; skipping.";
fi
set -e

# Post-checks
echo "\n== Post-checks =="
col_exists_after=$(run_mysql "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE table_schema=DATABASE() AND table_name='customers' AND column_name='customer_type';" || echo "0")
idx_exists_after=$(run_mysql "SELECT COUNT(*) FROM information_schema.STATISTICS WHERE table_schema=DATABASE() AND table_name='customers' AND index_name='idx_customers_customer_type';" || echo "0")

if [[ "$col_exists_after" -gt 0 ]]; then
  echo "Column customer_type verified present."
else
  echo "ERROR: Column customer_type not found after migration." >&2
fi
if [[ "$idx_exists_after" -gt 0 ]]; then
  echo "Index idx_customers_customer_type verified present."
else
  echo "WARNING: Index not found after migration. You may create it manually if needed."
fi

# Optional: offer backfill normalization
read -r -p "Do you want to run a normalization backfill (map french tokens to canonical tokens) now? [y/N] " DO_BACKFILL
if [[ "$DO_BACKFILL" =~ ^[Yy]$ ]]; then
  echo "Running backfill normalization..."
  MYSQL_PWD="$DB_PASS" mysql -u "$DB_USER" -h "$DB_HOST" -P "$DB_PORT" -D "$DB_NAME" -e "UPDATE customers SET customer_type = CASE WHEN LOWER(customer_type) IN ('particulier','particulier') THEN 'individual' WHEN LOWER(customer_type) IN ('entreprise','company') THEN 'company' WHEN LOWER(customer_type) IN ('government','administration') THEN 'government' ELSE customer_type END WHERE customer_type IS NOT NULL;"
  echo "Backfill completed."
fi

echo "\nMigration completed. Keep backup at: $BACKUP_FILE"

# Summary instructions
cat <<EOF
Verification suggestions:
 - Check application logs for errors
 - Run a UI smoke test: add a customer, edit a customer, list filter by customer_type
 - If you need to rollback: restore from the backup file:
     mysql -u <user> -p <database> < $BACKUP_FILE

EOF

exit 0
