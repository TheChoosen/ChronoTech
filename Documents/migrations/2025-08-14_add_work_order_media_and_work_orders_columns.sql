-- Migration: ajouter la table work_order_media et les colonnes de localisation & notes internes
-- Date: 2025-08-14

-- 1) Création de la table work_order_media si elle n'existe pas
CREATE TABLE IF NOT EXISTS work_order_media (
    id INT PRIMARY KEY AUTO_INCREMENT,
    work_order_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(100),
    file_size INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_by INT,
    INDEX idx_work_order_id (work_order_id),
    INDEX idx_created_at (created_at),
    CONSTRAINT fk_wom_work_order FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    CONSTRAINT fk_wom_uploaded_by FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2) Ajout des colonnes de localisation et notes internes dans work_orders (si nécessaire)
-- Note: MySQL 8+ supporte ADD COLUMN IF NOT EXISTS; si votre version est antérieure, adaptez la migration.

ALTER TABLE work_orders 
    ADD COLUMN IF NOT EXISTS location_address TEXT,
    ADD COLUMN IF NOT EXISTS location_latitude DECIMAL(10,6),
    ADD COLUMN IF NOT EXISTS location_longitude DECIMAL(10,6),
    ADD COLUMN IF NOT EXISTS internal_notes TEXT;

-- Fin de la migration
COMMIT;
