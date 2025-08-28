-- Migration: add customer_type column to customers
-- Created: 2025-08-20
-- Safely adds a nullable `customer_type` VARCHAR column and an index if missing.

-- Use a transaction where supported
START TRANSACTION;

-- Add column if not exists (MySQL 8 supports IF NOT EXISTS)
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS customer_type VARCHAR(50) NULL DEFAULT NULL;

-- Create index if not exists (MySQL doesn't support CREATE INDEX IF NOT EXISTS until 8.0.13,
-- so guard by checking information_schema)
DELIMITER $$
CREATE PROCEDURE add_index_if_missing()
BEGIN
    DECLARE idx_count INT DEFAULT 0;
    SELECT COUNT(*) INTO idx_count
    FROM information_schema.STATISTICS
    WHERE table_schema = DATABASE() AND table_name = 'customers' AND index_name = 'idx_customers_customer_type';

    IF idx_count = 0 THEN
        CREATE INDEX idx_customers_customer_type ON customers (customer_type);
    END IF;
END$$
DELIMITER ;

CALL add_index_if_missing();
DROP PROCEDURE IF EXISTS add_index_if_missing;

COMMIT;

-- Notes:
-- - This migration is idempotent: it won't fail if the column or index already exists.
-- - If your MySQL version doesn't support ALTER TABLE ... ADD COLUMN IF NOT EXISTS,
--   run a manual check against information_schema before applying.
