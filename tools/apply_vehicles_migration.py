#!/usr/bin/env python3
import os
import sys
from core.config import get_db_config
import pymysql
import traceback

MIGRATION_SQL = '''
CREATE TABLE IF NOT EXISTS vehicles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    make VARCHAR(128) DEFAULT NULL,
    model VARCHAR(128) DEFAULT NULL,
    year SMALLINT DEFAULT NULL,
    vin VARCHAR(64) DEFAULT NULL,
    license_plate VARCHAR(32) DEFAULT NULL,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
'''

cfg = get_db_config()
conn = None
try:
    conn = pymysql.connect(**cfg)
    conn.autocommit(True)
    with conn.cursor() as cursor:
        print('Creating vehicles table if needed...')
        cursor.execute(MIGRATION_SQL)

        def _get_count(q, params=None):
            cursor.execute(q, params or ())
            row = cursor.fetchone()
            if row is None:
                return 0
            if isinstance(row, dict):
                return int(next(iter(row.values())))
            return int(row[0])

        # Add vehicle_id to work_orders if not exists
        q = """
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE table_schema = DATABASE() AND table_name = 'work_orders' AND column_name = 'vehicle_id'
        """
        if _get_count(q) == 0:
            print('Adding vehicle_id to work_orders')
            cursor.execute("ALTER TABLE work_orders ADD COLUMN vehicle_id INT DEFAULT NULL")
        else:
            print('work_orders.vehicle_id already exists')

        # Add vehicle_id to appointments if table exists
        q_tables = """
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES
            WHERE table_schema = DATABASE() AND table_name = 'appointments'
        """
        if _get_count(q_tables) == 1:
            q_cols = """
                SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
                WHERE table_schema = DATABASE() AND table_name = 'appointments' AND column_name = 'vehicle_id'
            """
            if _get_count(q_cols) == 0:
                print('Adding vehicle_id to appointments')
                cursor.execute("ALTER TABLE appointments ADD COLUMN vehicle_id INT DEFAULT NULL")
            else:
                print('appointments.vehicle_id already exists')
        else:
            print('appointments table does not exist yet; skipping adding vehicle_id')

        # Add foreign keys if they don't exist
        q_fk_wo = """
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME AND tc.TABLE_NAME = kcu.TABLE_NAME
            WHERE tc.CONSTRAINT_TYPE = 'FOREIGN KEY' AND tc.TABLE_SCHEMA = DATABASE() AND tc.TABLE_NAME = 'work_orders' AND kcu.COLUMN_NAME = 'vehicle_id'
        """
        if _get_count(q_fk_wo) == 0:
            try:
                print('Adding FK fk_work_orders_vehicle')
                cursor.execute("ALTER TABLE work_orders ADD CONSTRAINT fk_work_orders_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL")
            except Exception as e:
                print('Could not add FK for work_orders.vehicle_id:', e)
        else:
            print('Foreign key for work_orders.vehicle_id already exists')

        q_fk_app = """
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME AND tc.TABLE_NAME = kcu.TABLE_NAME
            WHERE tc.CONSTRAINT_TYPE = 'FOREIGN KEY' AND tc.TABLE_SCHEMA = DATABASE() AND tc.TABLE_NAME = 'appointments' AND kcu.COLUMN_NAME = 'vehicle_id'
        """
        if _get_count(q_fk_app) == 0:
            try:
                print('Adding FK fk_appointments_vehicle')
                cursor.execute("ALTER TABLE appointments ADD CONSTRAINT fk_appointments_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL")
            except Exception as e:
                print('Could not add FK for appointments.vehicle_id:', e)
        else:
            print('Foreign key for appointments.vehicle_id already exists')

    print('Migration completed')
except Exception as e:
    print('Migration failed:', e)
    traceback.print_exc()
    sys.exit(1)
finally:
    try:
        if conn:
            conn.close()
    except Exception:
        pass
