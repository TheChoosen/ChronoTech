-- Script simplifié pour créer uniquement les tables manquantes
-- ChronoTech - Correction des erreurs Kanban

USE bdm;

-- 1. Créer la table technician_status
CREATE TABLE IF NOT EXISTS technician_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    technician_id INT NOT NULL,
    status ENUM('online', 'offline', 'busy', 'available', 'break') DEFAULT 'available',
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    location VARCHAR(255) DEFAULT 'Bureau principal',
    current_task_id INT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_technician (technician_id),
    INDEX idx_status (status),
    INDEX idx_last_seen (last_seen)
);

-- 2. Insérer des données pour tous les techniciens
INSERT IGNORE INTO technician_status (technician_id, status, location)
SELECT 
    u.id,
    COALESCE(u.availability_status, 'available') as status,
    CONCAT('Zone ', COALESCE(u.zone, 'Générale')) as location
FROM users u
WHERE u.role = 'technician' AND u.is_active = 1;

-- 3. Créer une table pour les mises à jour de statut
CREATE TABLE IF NOT EXISTS status_updates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entity_type ENUM('work_order', 'technician', 'vehicle') NOT NULL,
    entity_id INT NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    updated_by_user_id INT,
    update_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_created_at (created_at DESC)
);

-- 4. Créer des index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_work_orders_kanban ON work_orders(status, assigned_technician_id, priority);
CREATE INDEX IF NOT EXISTS idx_users_technician ON users(role, is_active, availability_status);

COMMIT;

-- Vérification
SELECT 'Tables technician_status et status_updates créées' as status;
SELECT COUNT(*) as technicians_with_status FROM technician_status;
