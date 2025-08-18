-- Migration: ajouter colonnes utilisateurs manquantes (phone, specialty, status, notes)
-- Date: 2025-08-15
-- Cette migration ajoute les colonnes uniquement si elles n'existent pas.
-- Elle utilise information_schema pour être compatible avec MySQL 5.7+ / 8.x

-- phone
SELECT COUNT(*) INTO @cnt FROM information_schema.COLUMNS
 WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'phone';
SET @s = IF(@cnt = 0,
    'ALTER TABLE users ADD COLUMN phone VARCHAR(50) NULL;',
    'SELECT "column phone already exists";');
PREPARE stmt FROM @s; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- specialty
SELECT COUNT(*) INTO @cnt FROM information_schema.COLUMNS
 WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'specialty';
SET @s = IF(@cnt = 0,
    'ALTER TABLE users ADD COLUMN specialty VARCHAR(100) NULL;',
    'SELECT "column specialty already exists";');
PREPARE stmt FROM @s; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- status
SELECT COUNT(*) INTO @cnt FROM information_schema.COLUMNS
 WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'status';
SET @s = IF(@cnt = 0,
    'ALTER TABLE users ADD COLUMN status VARCHAR(32) NULL;',
    'SELECT "column status already exists";');
PREPARE stmt FROM @s; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- notes
SELECT COUNT(*) INTO @cnt FROM information_schema.COLUMNS
 WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'notes';
SET @s = IF(@cnt = 0,
    'ALTER TABLE users ADD COLUMN notes TEXT NULL;',
    'SELECT "column notes already exists";');
PREPARE stmt FROM @s; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Fin de migration
SELECT 'migration complete' as info;
