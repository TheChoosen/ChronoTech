"""Safe conversion helper: backup schedule_json, fix invalid JSON, and convert column to JSON type.
Run with project's venv: PYTHONPATH=. ./venv/bin/python scripts/convert_schedule_json.py
Requires DB user with ALTER TABLE privileges.
"""
import sys
import pymysql
from core.config import get_db_config

def main():
    cfg = get_db_config()
    conn = pymysql.connect(**cfg)
    try:
        cur = conn.cursor()
        db = cfg.get('database')
        print('Connected to', cfg.get('host'), 'db=', db)

        # 1) Add backup column if missing
        cur.execute("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE table_schema=%s AND table_name='users' AND column_name='schedule_json_bkp'", (db,))
        row = cur.fetchone()
        cnt = None
        if isinstance(row, dict):
            cnt = next(iter(row.values()), 0)
        else:
            try:
                cnt = row[0]
            except Exception:
                cnt = 0
        if cnt == 0:
            print('Adding backup column schedule_json_bkp')
            cur.execute("ALTER TABLE users ADD COLUMN schedule_json_bkp TEXT NULL")
            conn.commit()
        else:
            print('Backup column schedule_json_bkp already present')

        # 2) Copy existing values to backup (only where null)
        cur.execute("UPDATE users SET schedule_json_bkp = schedule_json WHERE schedule_json_bkp IS NULL")
        print('Copied schedule_json -> schedule_json_bkp')
        conn.commit()

        # 3) Find rows with invalid JSON (JSON_VALID(schedule_json)=0). If any, set to empty object
        try:
            cur.execute("SELECT COUNT(*) FROM users WHERE schedule_json IS NOT NULL AND JSON_VALID(schedule_json) = 0")
            row = cur.fetchone()
            if isinstance(row, dict):
                bad = next(iter(row.values()), 0)
            else:
                try:
                    bad = row[0]
                except Exception:
                    bad = 0
        except Exception as e:
            print('JSON_VALID not supported or error:', e)
            bad = 0

        if bad:
            print(f"Found {bad} rows with invalid JSON; replacing with '{{}}'")
            cur.execute("UPDATE users SET schedule_json = '{}' WHERE schedule_json IS NOT NULL AND JSON_VALID(schedule_json) = 0")
            conn.commit()
        else:
            print('No invalid JSON rows found (or JSON_VALID unsupported).')

        # 4) Modify column to JSON type
        print('Altering column schedule_json to JSON NULL')
        cur.execute("ALTER TABLE users MODIFY COLUMN schedule_json JSON NULL")
        conn.commit()

        # 5) Verify
        cur.execute("SELECT DATA_TYPE FROM information_schema.COLUMNS WHERE table_schema=%s AND table_name='users' AND column_name='schedule_json'", (db,))
        row = cur.fetchone()
        dtype = None
        if row:
            if isinstance(row, dict):
                dtype = next(iter(row.values()), None)
            else:
                try:
                    dtype = row[0]
                except Exception:
                    dtype = None

        if dtype:
            print('schedule_json data_type after ALTER:', dtype)
        else:
            print('Could not verify column type')

        print('Conversion complete')
    except Exception as e:
        print('Error during conversion:', e)
        import traceback
        traceback.print_exc()
        sys.exit(2)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
