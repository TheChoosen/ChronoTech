-- Migration: ajouter colonnes timestamps et is_active à la table users
-- Date: 2025-08-15
-- Ajoute : created_at DATETIME, updated_at DATETIME, is_active TINYINT(1)
-- Utilise information_schema pour ne rien casser si les colonnes existent déjà.

-- created_at
SELECT COUNT(*) INTO @cnt FROM information_schema.COLUMNS
 WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'created_at';
SET @s = IF(@cnt = 0,
    'ALTER TABLE users ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;',
    'SELECT "column created_at already exists";');
PREPARE stmt FROM @s; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- updated_at
SELECT COUNT(*) INTO @cnt FROM information_schema.COLUMNS
 WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'updated_at';
SET @s = IF(@cnt = 0,
    'ALTER TABLE users ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;',
    'SELECT "column updated_at already exists";');
PREPARE stmt FROM @s; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- is_active
SELECT COUNT(*) INTO @cnt FROM information_schema.COLUMNS
 WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'is_active';
SET @s = IF(@cnt = 0,
    'ALTER TABLE users ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1;',
    'SELECT "column is_active already exists";');
PREPARE stmt FROM @s; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SELECT 'migration users timestamps complete' as info;
