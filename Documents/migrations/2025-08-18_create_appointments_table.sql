-- Migration: 2025-08-18_create_appointments_table.sql
-- Purpose: Create a minimal appointments table for scheduling customer appointments
-- Run this against the MySQL database used by ChronoTech

CREATE TABLE IF NOT EXISTS `appointments` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `customer_id` INT NOT NULL,
  `scheduled_date` DATETIME NOT NULL,
  `duration_minutes` INT DEFAULT NULL,
  `description` TEXT,
  `notes` TEXT,
  `status` VARCHAR(32) NOT NULL DEFAULT 'scheduled',
  `created_by_user_id` INT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_appointments_customer` (`customer_id`),
  KEY `idx_appointments_scheduled_date` (`scheduled_date`),
  CONSTRAINT `fk_appointments_customer` FOREIGN KEY (`customer_id`) REFERENCES `customers`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional: add a small comment or metadata table entry if you track migrations manually

-- Rollback (if needed):
-- DROP TABLE IF EXISTS `appointments`;
