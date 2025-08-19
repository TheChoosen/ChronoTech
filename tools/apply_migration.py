#!/usr/bin/env python3
import sys
import os
from core.config import get_db_config
import pymysql

MIGRATION_FILE = sys.argv[1] if len(sys.argv) > 1 else None
if not MIGRATION_FILE:
    print('Usage: apply_migration.py <path-to-sql-file>')
    sys.exit(2)

if not os.path.exists(MIGRATION_FILE):
    print('Migration file not found:', MIGRATION_FILE)
    sys.exit(2)

cfg = get_db_config()
conn = None
try:
    conn = pymysql.connect(**cfg)
    conn.autocommit(True)
    with conn.cursor() as cursor:
        sql = open(MIGRATION_FILE, 'r', encoding='utf-8').read()
        # Split statements by semicolon. This is a simple splitter and may not
        # handle delimiter changes or stored routines, but is fine for DDL migration.
        statements = [s.strip() for s in sql.split(';')]
        for stmt in statements:
            if not stmt:
                continue
            try:
                cursor.execute(stmt)
                print('OK:', stmt.splitlines()[0] if stmt.splitlines() else stmt)
            except Exception as e:
                print('ERROR executing statement:', e)
                print('Statement:', stmt[:200])
                raise
    print('Migration applied successfully')
except Exception as e:
    print('Migration failed:', e)
    sys.exit(1)
finally:
    try:
        if conn:
            conn.close()
    except Exception:
        pass
