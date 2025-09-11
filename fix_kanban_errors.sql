-- Script pour créer les tables manquantes et corriger les erreurs de colonnes
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

-- 2. Insérer des données par défaut pour tous les techniciens existants
INSERT IGNORE INTO technician_status (technician_id, status, last_seen, location)
SELECT 
    u.id,
    CASE 
        WHEN u.availability_status = 'available' THEN 'available'
        WHEN u.availability_status = 'busy' THEN 'busy'
        ELSE 'offline'
    END as status,
    COALESCE(u.last_login, DATE_SUB(NOW(), INTERVAL 1 HOUR)) as last_seen,
    CONCAT(COALESCE(u.city, 'Non défini'), ', ', COALESCE(u.department, 'Général')) as location
FROM users u
WHERE u.role = 'technician' AND u.is_active = 1;

-- 3. Vérifier si la colonne title existe dans work_orders, sinon créer une vue
-- Cette vue permettra d'avoir un "titre" généré à partir du claim_number et description
CREATE OR REPLACE VIEW v_work_orders_with_title AS
SELECT 
    wo.*,
    CONCAT(wo.claim_number, ' - ', LEFT(COALESCE(wo.description, 'Aucune description'), 50)) as title,
    c.name as customer_name,
    c.phone as customer_phone,
    c.address as customer_address,
    u.name as assigned_technician_name
FROM work_orders wo
LEFT JOIN customers c ON wo.customer_id = c.id
LEFT JOIN users u ON wo.assigned_technician_id = u.id;

-- 4. Créer une vue pour les techniciens avec leur statut complet
CREATE OR REPLACE VIEW v_technicians_kanban AS
SELECT 
    u.id,
    u.name,
    u.email,
    COALESCE(u.specialization, 'Technicien général') as specialization,
    COALESCE(ts.status, COALESCE(u.availability_status, 'offline')) as status,
    COUNT(wo.id) as active_tasks,
    u.avatar_url,
    COALESCE(ts.last_seen, u.last_login) as last_seen,
    COALESCE(ts.location, CONCAT(COALESCE(u.city, ''), ', ', COALESCE(u.department, ''))) as location,
    ts.notes as status_notes,
    wo_current.claim_number as current_task_number
FROM users u
LEFT JOIN technician_status ts ON u.id = ts.technician_id
LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id 
    AND wo.status NOT IN ('completed', 'cancelled')
LEFT JOIN work_orders wo_current ON ts.current_task_id = wo_current.id
WHERE u.role = 'technician' AND u.is_active = 1
GROUP BY u.id, u.name, u.email, u.specialization, ts.status, u.availability_status, 
         u.avatar_url, ts.last_seen, u.last_login, ts.location, u.city, u.department, 
         ts.notes, wo_current.claim_number;

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

SELECT 'Correction des erreurs Kanban terminée' as message;
