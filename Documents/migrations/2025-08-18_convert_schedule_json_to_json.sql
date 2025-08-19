-- Migration: convert schedule_json to JSON type
-- Run this script as a DBA user with ALTER TABLE privileges.
-- This will change the column type to JSON. Existing JSON text values will be preserved if they are valid JSON.

ALTER TABLE users
  MODIFY COLUMN schedule_json JSON NULL;

-- Note: if your MySQL/MariaDB version does not support JSON, run this migration with caution.
-- Alternatively, create a backup of your users table before applying.
