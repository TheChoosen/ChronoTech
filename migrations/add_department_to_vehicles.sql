-- Migration: Ajout colonne département pour véhicules
-- Date: 2025-09-04
-- Description: Ajouter une colonne département pour spécifier l'emplacement des véhicules dans l'entreprise

-- Ajouter la colonne département à la table vehicles
ALTER TABLE vehicles 
ADD COLUMN department VARCHAR(100) DEFAULT NULL 
COMMENT 'Département ou emplacement du véhicule dans l\'entreprise';

-- Créer un index pour optimiser les recherches par département
CREATE INDEX IF NOT EXISTS idx_vehicles_department ON vehicles(department);

-- Optionnel: Créer une table départements pour une gestion plus structurée
CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    location VARCHAR(255),
    manager_name VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insérer quelques départements par défaut
INSERT IGNORE INTO departments (name, description, location) VALUES
('Maintenance', 'Département de maintenance véhicules', 'Atelier principal'),
('Commercial', 'Véhicules commerciaux et livraisons', 'Zone commerciale'),
('Direction', 'Véhicules de direction', 'Parking direction'),
('Service Client', 'Véhicules service après-vente', 'Zone SAV'),
('Technique', 'Véhicules équipe technique', 'Hangar technique'),
('Logistique', 'Transport et logistique', 'Zone logistique');

-- Ajouter une contrainte optionnelle pour lier au tableau départements
-- (Commenté pour permettre la saisie libre, décommentez si vous voulez une contrainte)
-- ALTER TABLE vehicles 
-- ADD CONSTRAINT fk_vehicles_department 
-- FOREIGN KEY (department) REFERENCES departments(name) 
-- ON UPDATE CASCADE ON DELETE SET NULL;

-- Mettre à jour quelques véhicules existants avec des départements par défaut (optionnel)
UPDATE vehicles 
SET department = 'Maintenance' 
WHERE department IS NULL AND id % 3 = 0;

UPDATE vehicles 
SET department = 'Commercial' 
WHERE department IS NULL AND id % 3 = 1;

UPDATE vehicles 
SET department = 'Technique' 
WHERE department IS NULL AND id % 3 = 2;
