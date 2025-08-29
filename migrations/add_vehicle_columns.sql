-- Migration pour ajouter les colonnes manquantes à la table vehicles
-- Date: 2025-08-28
-- Description: Ajout de colonnes pour kilométrage, couleur et type de carburant

-- Vérifier et ajouter la colonne mileage
SET @col_exists = 0;
SELECT COUNT(*) INTO @col_exists 
FROM information_schema.columns 
WHERE table_schema = 'bdm' AND table_name = 'vehicles' AND column_name = 'mileage';

SET @sql = IF(@col_exists = 0, 'ALTER TABLE vehicles ADD COLUMN mileage INT DEFAULT NULL AFTER year', 'SELECT "Column mileage already exists" as info');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Vérifier et ajouter la colonne color
SET @col_exists = 0;
SELECT COUNT(*) INTO @col_exists 
FROM information_schema.columns 
WHERE table_schema = 'bdm' AND table_name = 'vehicles' AND column_name = 'color';

SET @sql = IF(@col_exists = 0, 'ALTER TABLE vehicles ADD COLUMN color VARCHAR(64) DEFAULT NULL AFTER license_plate', 'SELECT "Column color already exists" as info');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Vérifier et ajouter la colonne fuel_type
SET @col_exists = 0;
SELECT COUNT(*) INTO @col_exists 
FROM information_schema.columns 
WHERE table_schema = 'bdm' AND table_name = 'vehicles' AND column_name = 'fuel_type';

SET @sql = IF(@col_exists = 0, 'ALTER TABLE vehicles ADD COLUMN fuel_type ENUM(\'essence\', \'diesel\', \'hybrid\', \'electric\', \'other\') DEFAULT NULL AFTER color', 'SELECT "Column fuel_type already exists" as info');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
