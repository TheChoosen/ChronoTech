"""Idempotent migration runner to add idx_vehicles_customer_id on vehicles.customer_id
Uses core.config.get_db_config() to obtain DB credentials.
"""
import pymysql
from core.config import get_db_config
from core.utils import log_info, log_error


def ensure_index():
    cfg = get_db_config()
    conn = None
    try:
        conn = pymysql.connect(**cfg)
        cur = conn.cursor(pymysql.cursors.DictCursor)
        # Check if vehicles table exists
        cur.execute("""
            SELECT COUNT(*) as cnt FROM information_schema.tables
            WHERE table_schema = %s AND table_name = 'vehicles'
        """, (cfg.get('database'),))
        row = cur.fetchone()
        if not row or row.get('cnt', 0) == 0:
            log_info('Table vehicles does not exist; skipping index creation')
            return
        # Check existing indexes
        cur.execute("""
            SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'vehicles'
        """, (cfg.get('database'),))
        existing = [r['INDEX_NAME'] for r in cur.fetchall()]
        if 'idx_vehicles_customer_id' in existing:
            log_info('Index idx_vehicles_customer_id already exists')
            return
        # Create index
        cur.execute('ALTER TABLE vehicles ADD INDEX idx_vehicles_customer_id (customer_id)')
        conn.commit()
        log_info('Index idx_vehicles_customer_id created successfully')
    except Exception as e:
        log_error(f'Error creating index: {e}')
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    ensure_index()
