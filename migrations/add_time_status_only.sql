-- Migration: Ajouter la colonne time_status à work_orders si elle n'existe pas
-- Date: 2025-01-22

-- Vérifier et ajouter la colonne time_status seulement si elle n'existe pas
SET @column_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                      WHERE TABLE_SCHEMA = 'bdm' 
                      AND TABLE_NAME = 'work_orders' 
                      AND COLUMN_NAME = 'time_status');

SET @sql = IF(@column_exists = 0, 
              'ALTER TABLE work_orders ADD COLUMN time_status ENUM(''not_started'', ''in_progress'', ''paused'', ''completed'') DEFAULT ''not_started'' AFTER priority;', 
              'SELECT ''Column time_status already exists'' AS message;');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Créer l'index sur time_status si la colonne a été ajoutée
SET @index_sql = IF(@column_exists = 0, 
                    'CREATE INDEX idx_work_orders_time_status ON work_orders(time_status);', 
                    'SELECT ''Index not needed - column already exists'' AS message;');

PREPARE idx_stmt FROM @index_sql;
EXECUTE idx_stmt;
DEALLOCATE PREPARE idx_stmt;
