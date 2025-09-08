-- Migration pour ajouter la colonne département à la table vehicles
-- Date: 2025-09-04
-- Description: Ajout de la colonne département pour spécifier l'emplacement du véhicule dans l'entreprise

-- Vérifier et ajouter la colonne department
SET @col_exists = 0;
SELECT COUNT(*) INTO @col_exists 
FROM information_schema.columns 
WHERE table_schema = DATABASE() AND table_name = 'vehicles' AND column_name = 'department';

SET @sql = IF(@col_exists = 0, 'ALTER TABLE vehicles ADD COLUMN department VARCHAR(128) DEFAULT NULL AFTER fuel_type', 'SELECT "Column department already exists" as info');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Ajout d'un index pour améliorer les performances des filtres par département
SET @index_exists = 0;
SELECT COUNT(*) INTO @index_exists
FROM information_schema.statistics 
WHERE table_schema = DATABASE() AND table_name = 'vehicles' AND index_name = 'idx_vehicles_department';

SET @sql = IF(@index_exists = 0, 'ALTER TABLE vehicles ADD INDEX idx_vehicles_department (department)', 'SELECT "Index idx_vehicles_department already exists" as info');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Optionnel: Création d'une table de référence pour les départements si elle n'existe pas
CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE,
    description TEXT DEFAULT NULL,
    color VARCHAR(7) DEFAULT '#007bff' COMMENT 'Couleur hexadécimale pour l\'affichage',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_departments_active (is_active),
    INDEX idx_departments_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insertion de quelques départements par défaut si la table est vide
INSERT IGNORE INTO departments (name, description, color) VALUES
('Administration', 'Véhicules administratifs et direction', '#6c757d'),
('Commercial', 'Véhicules équipe commerciale', '#28a745'),
('Technique', 'Véhicules équipe technique', '#007bff'),
('Logistique', 'Véhicules transport et livraison', '#fd7e14'),
('Maintenance', 'Véhicules équipe maintenance', '#dc3545'),
('Direction', 'Véhicules de direction', '#6f42c1');

-- Optionnel: Mettre à jour quelques véhicules existants avec des départements d'exemple
-- UPDATE vehicles SET department = 'Technique' WHERE id IN (SELECT id FROM vehicles LIMIT 3);
-- UPDATE vehicles SET department = 'Commercial' WHERE id IN (SELECT id FROM vehicles ORDER BY id DESC LIMIT 2);

SELECT 'Migration terminée: Colonne department ajoutée à la table vehicles' as status;
