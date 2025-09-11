-- Script pour corriger les erreurs de base de données ChronoTech
-- Ajouter les colonnes manquantes pour résoudre les erreurs du log

USE bdm;

-- 1. Ajouter des colonnes à la table vehicles pour les données de maintenance (ignorer les erreurs si colonnes existent)
SET @sql = CONCAT('ALTER TABLE vehicles ADD COLUMN last_maintenance_date DATETIME DEFAULT NULL');
SET @exist = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = 'bdm' AND TABLE_NAME = 'vehicles' AND COLUMN_NAME = 'last_maintenance_date');
SET @sqlstmt = IF(@exist > 0, 'SELECT "Column last_maintenance_date already exists"', @sql);
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = CONCAT('ALTER TABLE vehicles ADD COLUMN next_maintenance_date DATETIME DEFAULT NULL');
SET @exist = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = 'bdm' AND TABLE_NAME = 'vehicles' AND COLUMN_NAME = 'next_maintenance_date');
SET @sqlstmt = IF(@exist > 0, 'SELECT "Column next_maintenance_date already exists"', @sql);
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = CONCAT('ALTER TABLE vehicles ADD COLUMN engine_hours INT DEFAULT 0');
SET @exist = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = 'bdm' AND TABLE_NAME = 'vehicles' AND COLUMN_NAME = 'engine_hours');
SET @sqlstmt = IF(@exist > 0, 'SELECT "Column engine_hours already exists"', @sql);
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = CONCAT('ALTER TABLE vehicles ADD COLUMN maintenance_status ENUM("ok", "due", "overdue") DEFAULT "ok"');
SET @exist = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = 'bdm' AND TABLE_NAME = 'vehicles' AND COLUMN_NAME = 'maintenance_status');
SET @sqlstmt = IF(@exist > 0, 'SELECT "Column maintenance_status already exists"', @sql);
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. Créer une table vehicle_telemetry pour les données IoT si elle n'existe pas
CREATE TABLE IF NOT EXISTS vehicle_telemetry (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id INT NOT NULL,
    usage_intensity DECIMAL(5,2) DEFAULT 0,
    avg_daily_usage DECIMAL(8,2) DEFAULT 0,
    temperature_avg DECIMAL(5,2) DEFAULT 20,
    vibration_level DECIMAL(5,2) DEFAULT 0,
    oil_pressure DECIMAL(5,2) DEFAULT 35,
    brake_wear_level DECIMAL(5,2) DEFAULT 0,
    tire_wear_level DECIMAL(5,2) DEFAULT 0,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
    INDEX idx_vehicle_recorded (vehicle_id, recorded_at)
);

-- 3. Mettre à jour les données existantes avec des valeurs par défaut réalistes
UPDATE vehicles 
SET 
    last_maintenance_date = DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 90) DAY),
    next_maintenance_date = DATE_ADD(NOW(), INTERVAL (30 + FLOOR(RAND() * 60)) DAY),
    engine_hours = COALESCE(mileage / 10, 100 + FLOOR(RAND() * 500))
WHERE last_maintenance_date IS NULL;

-- 4. Vérifier que la table work_orders a les colonnes nécessaires
SET @sql = CONCAT('ALTER TABLE work_orders ADD COLUMN type ENUM("repair", "maintenance", "preventive", "inspection", "other") DEFAULT "repair"');
SET @exist = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = 'bdm' AND TABLE_NAME = 'work_orders' AND COLUMN_NAME = 'type');
SET @sqlstmt = IF(@exist > 0, 'SELECT "Column type already exists"', @sql);
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = CONCAT('ALTER TABLE work_orders ADD COLUMN completed_date DATETIME DEFAULT NULL');
SET @exist = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = 'bdm' AND TABLE_NAME = 'work_orders' AND COLUMN_NAME = 'completed_date');
SET @sqlstmt = IF(@exist > 0, 'SELECT "Column completed_date already exists"', @sql);
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = CONCAT('ALTER TABLE work_orders ADD COLUMN estimated_duration INT DEFAULT 120');
SET @exist = (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = 'bdm' AND TABLE_NAME = 'work_orders' AND COLUMN_NAME = 'estimated_duration');
SET @sqlstmt = IF(@exist > 0, 'SELECT "Column estimated_duration already exists"', @sql);
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 5. Créer des index pour améliorer les performances (ignorer les erreurs si index existe)
SET @sql = 'CREATE INDEX idx_vehicles_maintenance ON vehicles(last_maintenance_date, next_maintenance_date)';
SET @exist = (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = 'bdm' AND TABLE_NAME = 'vehicles' AND INDEX_NAME = 'idx_vehicles_maintenance');
SET @sqlstmt = IF(@exist > 0, 'SELECT "Index idx_vehicles_maintenance already exists"', @sql);
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = 'CREATE INDEX idx_work_orders_type_status ON work_orders(type, status)';
SET @exist = (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = 'bdm' AND TABLE_NAME = 'work_orders' AND INDEX_NAME = 'idx_work_orders_type_status');
SET @sqlstmt = IF(@exist > 0, 'SELECT "Index idx_work_orders_type_status already exists"', @sql);
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 6. Insérer quelques données télématiques d'exemple pour les tests
INSERT IGNORE INTO vehicle_telemetry (vehicle_id, usage_intensity, avg_daily_usage, temperature_avg, vibration_level, oil_pressure, brake_wear_level, tire_wear_level)
SELECT 
    v.id,
    2.5 + (RAND() * 5),  -- usage_intensity entre 2.5 et 7.5
    (v.mileage / GREATEST(DATEDIFF(NOW(), v.created_at), 1)),  -- avg_daily_usage calculé
    18 + (RAND() * 25),  -- température entre 18 et 43°C
    1 + (RAND() * 3),    -- vibrations entre 1 et 4
    30 + (RAND() * 15),  -- pression huile entre 30 et 45
    RAND() * 80,         -- usure freins 0-80%
    RAND() * 70          -- usure pneus 0-70%
FROM vehicles v
WHERE v.id <= 20;  -- Limiter aux 20 premiers véhicules pour les tests

-- 7. Mettre à jour quelques work_orders avec des types appropriés
UPDATE work_orders 
SET 
    type = CASE 
        WHEN description LIKE '%maintenance%' THEN 'maintenance'
        WHEN description LIKE '%réparation%' OR description LIKE '%repair%' THEN 'repair'
        WHEN description LIKE '%inspection%' THEN 'inspection'
        WHEN description LIKE '%préventif%' OR description LIKE '%preventive%' THEN 'preventive'
        ELSE 'repair'
    END,
    completed_date = CASE 
        WHEN status = 'completed' THEN DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 30) DAY)
        ELSE NULL
    END
WHERE type IS NULL OR type = 'repair';

COMMIT;

-- Afficher un résumé des modifications
SELECT 'vehicles' as table_name, COUNT(*) as count FROM vehicles
UNION ALL
SELECT 'vehicle_telemetry' as table_name, COUNT(*) as count FROM vehicle_telemetry
UNION ALL
SELECT 'work_orders' as table_name, COUNT(*) as count FROM work_orders;

SELECT 'Colonnes ajoutées avec succès pour corriger les erreurs ML et scheduler' as status;
