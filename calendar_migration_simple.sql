-- Migration simplifiée pour calendrier ChronoTech
-- Appliquer les colonnes essentielles

-- Vérifier et ajouter les colonnes de récurrence
SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'work_orders' AND column_name = 'recurrence_type' AND table_schema = DATABASE()) = 0, 'ALTER TABLE work_orders ADD COLUMN recurrence_type ENUM(\'none\', \'daily\', \'weekly\', \'monthly\', \'yearly\') DEFAULT \'none\'', 'SELECT "Column recurrence_type exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'work_orders' AND column_name = 'recurrence_interval' AND table_schema = DATABASE()) = 0, 'ALTER TABLE work_orders ADD COLUMN recurrence_interval INT DEFAULT 1', 'SELECT "Column recurrence_interval exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'work_orders' AND column_name = 'is_all_day' AND table_schema = DATABASE()) = 0, 'ALTER TABLE work_orders ADD COLUMN is_all_day BOOLEAN DEFAULT FALSE', 'SELECT "Column is_all_day exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'work_orders' AND column_name = 'event_color' AND table_schema = DATABASE()) = 0, 'ALTER TABLE work_orders ADD COLUMN event_color VARCHAR(7) DEFAULT \'#007bff\'', 'SELECT "Column event_color exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Créer la table calendar_resources si elle n'existe pas
CREATE TABLE IF NOT EXISTS calendar_resources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type ENUM('technician', 'equipment', 'vehicle', 'room') DEFAULT 'technician',
    description TEXT,
    capacity INT DEFAULT 1,
    color VARCHAR(7) DEFAULT '#007bff',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Ajouter des index essentiels
SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE table_name = 'work_orders' AND index_name = 'idx_scheduled_date' AND table_schema = DATABASE()) = 0, 'CREATE INDEX idx_scheduled_date ON work_orders(scheduled_date)', 'SELECT "Index exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Insérer quelques ressources de base
INSERT IGNORE INTO calendar_resources (name, type, description, capacity, color) VALUES
('Technicien principal', 'technician', 'Technicien senior pour interventions complexes', 1, '#007bff'),
('Équipement de diagnostic', 'equipment', 'Équipement de diagnostic automobile', 1, '#28a745'),
('Véhicule de service', 'vehicle', 'Véhicule d\'intervention avec équipement', 1, '#ffc107');
