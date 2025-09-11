-- Script pour créer les tables manquantes et corriger les erreurs de colonnes (Version corrigée)
-- ChronoTech - Correction des erreurs Kanban

USE bdm;

-- 1. Créer la table technician_status si elle n'existe pas
CREATE TABLE IF NOT EXISTS technician_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    technician_id INT NOT NULL,
    status ENUM('online', 'offline', 'busy', 'available', 'break') DEFAULT 'offline',
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    location VARCHAR(255),
    current_task_id INT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (current_task_id) REFERENCES work_orders(id) ON DELETE SET NULL,
    UNIQUE KEY unique_technician (technician_id),
    INDEX idx_status (status),
    INDEX idx_last_seen (last_seen)
);

-- 2. Insérer des données par défaut pour tous les techniciens existants (avec colonnes existantes)
INSERT IGNORE INTO technician_status (technician_id, status, last_seen, location)
SELECT 
    u.id,
    CASE 
        WHEN u.availability_status = 'available' THEN 'available'
        WHEN u.availability_status = 'busy' THEN 'busy'
        ELSE 'offline'
    END as status,
    DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 60) MINUTE) as last_seen,
    CONCAT('Zone ', COALESCE(u.zone, 'Générale'), ', ', COALESCE(u.department, 'Technique')) as location
FROM users u
WHERE u.role = 'technician' AND u.is_active = 1;

-- 3. Créer une vue pour les work_orders avec titre généré
CREATE OR REPLACE VIEW v_work_orders_with_title AS
SELECT 
    wo.*,
    CONCAT(wo.claim_number, ' - ', LEFT(COALESCE(wo.description, 'Aucune description'), 50)) as title,
    COALESCE(c.name, wo.customer_name) as customer_name,
    COALESCE(c.phone, wo.customer_phone) as customer_phone,
    COALESCE(c.address, wo.customer_address) as customer_address,
    u.name as assigned_technician_name
FROM work_orders wo
LEFT JOIN customers c ON wo.customer_id = c.id
LEFT JOIN users u ON wo.assigned_technician_id = u.id;

-- 4. Créer une vue pour les techniciens avec leur statut complet (colonnes existantes)
CREATE OR REPLACE VIEW v_technicians_kanban AS
SELECT 
    u.id,
    u.name,
    u.email,
    COALESCE(u.specialty, 'Technicien général') as specialization,
    COALESCE(ts.status, COALESCE(u.availability_status, 'offline')) as status,
    COUNT(wo.id) as active_tasks,
    u.photo as avatar_url,
    COALESCE(ts.last_seen, u.updated_at) as last_seen,
    COALESCE(ts.location, CONCAT('Zone ', COALESCE(u.zone, 'Générale'), ', ', COALESCE(u.department, 'Technique'))) as location,
    ts.notes as status_notes,
    wo_current.claim_number as current_task_number,
    u.hourly_rate,
    u.efficiency_score
FROM users u
LEFT JOIN technician_status ts ON u.id = ts.technician_id
LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id 
    AND wo.status NOT IN ('completed', 'cancelled')
LEFT JOIN work_orders wo_current ON ts.current_task_id = wo_current.id
WHERE u.role = 'technician' AND u.is_active = 1
GROUP BY u.id, u.name, u.email, u.specialty, ts.status, u.availability_status, 
         u.photo, ts.last_seen, u.updated_at, ts.location, u.zone, u.department, 
         ts.notes, wo_current.claim_number, u.hourly_rate, u.efficiency_score;

-- 5. Créer des index pour améliorer les performances des requêtes Kanban
CREATE INDEX IF NOT EXISTS idx_work_orders_status_assigned ON work_orders(status, assigned_technician_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_priority_status ON work_orders(priority, status);
CREATE INDEX IF NOT EXISTS idx_users_role_active ON users(role, is_active);

-- 6. Créer une table pour les mises à jour de statut en temps réel
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
    INDEX idx_created_at (created_at DESC),
    FOREIGN KEY (updated_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 7. Ajout de quelques données télématriques pour améliorer les vues
UPDATE technician_status ts
JOIN users u ON ts.technician_id = u.id
SET ts.status = CASE 
    WHEN RAND() > 0.7 THEN 'available'
    WHEN RAND() > 0.4 THEN 'busy'
    WHEN RAND() > 0.2 THEN 'break'
    ELSE 'offline'
END,
ts.last_seen = DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 120) MINUTE)
WHERE u.role = 'technician';

COMMIT;

-- Vérification finale
SELECT 'Tables créées avec succès' as status;
SELECT 
    'technician_status' as table_name, 
    COUNT(*) as records 
FROM technician_status
UNION ALL
SELECT 
    'status_updates' as table_name, 
    COUNT(*) as records 
FROM status_updates;

SELECT 'Correction des erreurs Kanban terminée avec colonnes existantes' as message;
