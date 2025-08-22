-- Migration: create intervention_comments table
-- Date: 2025-08-22
-- Idempotent create (won't fail if table already exists)

CREATE TABLE IF NOT EXISTS intervention_comments (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  work_order_id BIGINT UNSIGNED NOT NULL,
  technician_id BIGINT UNSIGNED DEFAULT NULL,
  content LONGTEXT NOT NULL,
  is_private TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  INDEX idx_work_order_id (work_order_id),
  INDEX idx_technician_id (technician_id),
  CONSTRAINT fk_intervention_comments_work_orders FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional: grant minimal privileges or additional indexes can be added later.
