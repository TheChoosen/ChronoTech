"""Safe migration script to optimize the appointments table.
It will:
- add a `status` ENUM column if missing
- add indexes if missing
- add foreign key constraint on created_by_user_id if missing

Run: python Documents/migrations/2025-08-18_optimize_appointments_table.py
"""
from core.config import get_db_config
import pymysql


def column_exists(conn, db, table, column):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) as cnt FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s
        """, (db, table, column))
        return cur.fetchone()['cnt'] > 0


def index_exists(conn, db, table, index_name):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) as cnt FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND INDEX_NAME=%s
        """, (db, table, index_name))
        return cur.fetchone()['cnt'] > 0


def fk_exists(conn, db, table, constraint_name):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) as cnt FROM information_schema.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND CONSTRAINT_NAME=%s AND CONSTRAINT_TYPE='FOREIGN KEY'
        """, (db, table, constraint_name))
        return cur.fetchone()['cnt'] > 0


def main():
    cfg = get_db_config()
    db = cfg['database']
    conn = pymysql.connect(**cfg)
    try:
        # 1) add status column if missing
        if not column_exists(conn, db, 'appointments', 'status'):
            print('Adding status column...')
            with conn.cursor() as cur:
                cur.execute("""
                    ALTER TABLE `appointments`
                    ADD COLUMN `status` ENUM('scheduled','confirmed','completed','cancelled') NOT NULL DEFAULT 'scheduled'
                """)
                conn.commit()
        else:
            print('status column already exists')

        # 2) add indexes if missing
        indexes = [
            ('idx_appointments_status', 'status'),
            ('idx_appointments_created_by', 'created_by_user_id'),
            ('idx_appointments_scheduled_status', 'scheduled_date, status')
        ]
        for idx_name, cols in indexes:
            if not index_exists(conn, db, 'appointments', idx_name):
                print(f'Adding index {idx_name} on ({cols})')
                with conn.cursor() as cur:
                    cur.execute(f"ALTER TABLE `appointments` ADD INDEX `{idx_name}` ({cols})")
                    conn.commit()
            else:
                print(f'Index {idx_name} already exists')

        # 3) add FK for created_by_user_id
        fk_name = 'fk_appointments_created_by'
        if not fk_exists(conn, db, 'appointments', fk_name):
            print('Adding foreign key', fk_name)
            with conn.cursor() as cur:
                # ensure column exists
                if not column_exists(conn, db, 'appointments', 'created_by_user_id'):
                    cur.execute('ALTER TABLE `appointments` ADD COLUMN `created_by_user_id` INT DEFAULT NULL')
                    conn.commit()
                cur.execute(f"ALTER TABLE `appointments` ADD CONSTRAINT `{fk_name}` FOREIGN KEY (`created_by_user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL ON UPDATE CASCADE")
                conn.commit()
        else:
            print('Foreign key already exists')

        print('Migration completed')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
