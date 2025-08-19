-- Migration: add extended technician fields to users
-- Adds columns used by the edit form so data can be persisted

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS certification_level VARCHAR(64) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS experience_years INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS hourly_rate DECIMAL(10,2) DEFAULT 0.00,
  ADD COLUMN IF NOT EXISTS zone VARCHAR(64) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS max_weekly_hours INT DEFAULT 40,
  ADD COLUMN IF NOT EXISTS vehicle_assigned VARCHAR(128) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS tools_assigned TEXT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS schedule_json JSON DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS photo VARCHAR(255) DEFAULT NULL;

-- Optional: backfill sensible defaults for existing rows
UPDATE users
SET experience_years = COALESCE(experience_years, 0),
    hourly_rate = COALESCE(hourly_rate, 0.00),
    max_weekly_hours = COALESCE(max_weekly_hours, 40)
WHERE 1=1;

-- End of migration
