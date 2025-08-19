-- Migration: 2025-08-18_optimize_appointments_table.sql
-- Purpose: Add indexes, constraints and tighten column types for the appointments table

ALTER TABLE `appointments`
  -- Convert status to ENUM for predictable values
  MODIFY COLUMN `status` ENUM('scheduled','confirmed','completed','cancelled') NOT NULL DEFAULT 'scheduled',
  -- Add index on status for fast lookups
  ADD INDEX `idx_appointments_status` (`status`),
  -- Add index on created_by_user_id for user-related queries
  ADD INDEX `idx_appointments_created_by` (`created_by_user_id`),
  -- Add composite index to accelerate queries by scheduled_date + status
  ADD INDEX `idx_appointments_scheduled_status` (`scheduled_date`, `status`),
  -- Add foreign key to users table for created_by_user_id (SET NULL on delete)
  ADD CONSTRAINT `fk_appointments_created_by` FOREIGN KEY (`created_by_user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL ON UPDATE CASCADE;

-- Optional: consider adding fulltext index for description if search is required:
-- ALTER TABLE `appointments` ADD FULLTEXT INDEX `ft_description` (`description`);

-- No explicit COMMIT needed for this migration file when executed via a DB client
