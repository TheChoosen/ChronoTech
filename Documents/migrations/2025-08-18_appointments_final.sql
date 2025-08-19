-- Final migration: 2025-08-18_appointments_final.sql
-- Purpose: Definitive schema for the `appointments` table (create + indexes + foreign keys)
-- Apply this file in your DB migration pipeline for traceability.

-- Safety: this script uses CREATE TABLE IF NOT EXISTS and ADD CONSTRAINT IF NOT EXISTS patterns where reasonable.

-- Note: MySQL does not support IF NOT EXISTS for ADD CONSTRAINT, so run this file in a migration runner that
-- either supports idempotent execution or review the DDL before applying on production.

-- Create table with final structure
CREATE TABLE IF NOT EXISTS `appointments` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `customer_id` INT NOT NULL,
  `scheduled_date` DATETIME NOT NULL,
  `duration_minutes` INT DEFAULT NULL,
  `description` TEXT,
  `notes` TEXT,
  `status` ENUM('scheduled','confirmed','completed','cancelled') NOT NULL DEFAULT 'scheduled',
  `created_by_user_id` INT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_appointments_customer` (`customer_id`),
  KEY `idx_appointments_scheduled_date` (`scheduled_date`),
  KEY `idx_appointments_status` (`status`),
  KEY `idx_appointments_created_by` (`created_by_user_id`),
  KEY `idx_appointments_scheduled_status` (`scheduled_date`, `status`),
  CONSTRAINT `fk_appointments_customer` FOREIGN KEY (`customer_id`) REFERENCES `customers`(`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_appointments_created_by` FOREIGN KEY (`created_by_user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional: fulltext index on description for searching (enable if needed and MySQL version supports it)
-- ALTER TABLE `appointments` ADD FULLTEXT INDEX `ft_appointments_description` (`description`);

-- Rollback (if needed):
-- DROP TABLE IF EXISTS `appointments`;
