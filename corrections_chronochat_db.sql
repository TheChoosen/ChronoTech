-- ====================================================================
-- CORRECTIONS CHRONOCHAT - Table user_presence et optimisations
-- Date: 2 septembre 2025
-- ====================================================================

-- 1. Créer table user_presence complète pour équipe en ligne
CREATE TABLE IF NOT EXISTS user_presence (
    user_id INT PRIMARY KEY,
    status ENUM('online','away','busy','offline') DEFAULT 'online',
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,
    session_data JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_last_seen (last_seen),
    INDEX idx_status (status),
    INDEX idx_user_status (user_id, status)
);

-- 2. Table pour historique des mouvements Kanban (tracking)
CREATE TABLE IF NOT EXISTS kanban_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    moved_by INT,
    move_reason TEXT,
    moved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    duration_in_status INT COMMENT 'Durée en secondes dans le statut précédent',
    FOREIGN KEY (task_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (moved_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_task_id (task_id),
    INDEX idx_moved_at (moved_at),
    INDEX idx_moved_by (moved_by)
);

-- 3. Table pour pièces jointes chat (préparation WebSocket)
CREATE TABLE IF NOT EXISTS chat_attachments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size INT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    uploaded_by INT NOT NULL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (message_id) REFERENCES chat_messages(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_message_id (message_id),
    INDEX idx_uploaded_by (uploaded_by),
    INDEX idx_uploaded_at (uploaded_at)
);

-- 4. Améliorer table chat_messages pour WebSocket
ALTER TABLE chat_messages 
ADD COLUMN IF NOT EXISTS edited_at DATETIME NULL,
ADD COLUMN IF NOT EXISTS parent_message_id INT NULL COMMENT 'Pour les threads/réponses',
ADD COLUMN IF NOT EXISTS message_type ENUM('text','file','system','notification') DEFAULT 'text',
ADD COLUMN IF NOT EXISTS metadata JSON COMMENT 'Données additionnelles (mentions, reactions, etc)',
ADD INDEX IF NOT EXISTS idx_parent_message (parent_message_id),
ADD INDEX IF NOT EXISTS idx_message_type (message_type),
ADD FOREIGN KEY IF NOT EXISTS fk_parent_message (parent_message_id) REFERENCES chat_messages(id) ON DELETE CASCADE;

-- 5. Optimiser calendar_resources pour connexion avec événements
UPDATE calendar_resources SET 
    description = CONCAT(description, ' - Synchronisé avec ChronoChat Dashboard'),
    is_active = 1
WHERE is_active IS NULL OR description IS NULL;

-- 6. Vues optimisées pour le dashboard

-- Vue équipe en ligne avec détails
CREATE OR REPLACE VIEW online_team_view AS
SELECT 
    u.id,
    u.name,
    u.email,
    u.role,
    up.status,
    up.last_seen,
    up.ip_address,
    CASE 
        WHEN up.last_seen >= DATE_SUB(NOW(), INTERVAL 2 MINUTE) THEN 'online'
        WHEN up.last_seen >= DATE_SUB(NOW(), INTERVAL 10 MINUTE) THEN 'away'
        ELSE 'offline'
    END as computed_status,
    TIMESTAMPDIFF(SECOND, up.last_seen, NOW()) as seconds_since_last_seen
FROM users u
LEFT JOIN user_presence up ON u.id = up.user_id
WHERE u.is_active = 1
AND u.role IN ('admin', 'manager', 'supervisor', 'technician')
ORDER BY 
    CASE WHEN up.status = 'online' THEN 1 
         WHEN up.status = 'away' THEN 2 
         WHEN up.status = 'busy' THEN 3 
         ELSE 4 END,
    u.name;

-- Vue Kanban avec métriques
CREATE OR REPLACE VIEW kanban_metrics_view AS
SELECT 
    w.status,
    COUNT(*) as total_tasks,
    COUNT(CASE WHEN w.priority = 'urgent' THEN 1 END) as urgent_tasks,
    COUNT(CASE WHEN w.priority = 'high' THEN 1 END) as high_priority_tasks,
    AVG(CASE WHEN w.status = 'completed' THEN 
        TIMESTAMPDIFF(HOUR, w.created_at, w.updated_at) 
    END) as avg_completion_hours,
    COUNT(CASE WHEN w.assigned_technician_id IS NOT NULL THEN 1 END) as assigned_tasks
FROM work_orders w
WHERE w.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY w.status;

-- Vue chat avec statistiques
CREATE OR REPLACE VIEW chat_statistics_view AS
SELECT 
    cm.channel_type,
    cm.channel_id,
    COUNT(*) as total_messages,
    COUNT(DISTINCT cm.user_id) as active_users,
    MAX(cm.created_at) as last_activity,
    COUNT(CASE WHEN cm.created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY) THEN 1 END) as messages_today,
    COUNT(CASE WHEN cm.is_bot = 1 THEN 1 END) as bot_messages
FROM chat_messages cm
WHERE cm.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY cm.channel_type, cm.channel_id;

-- 7. Index d'optimisation pour performance
CREATE INDEX IF NOT EXISTS idx_work_orders_status_priority ON work_orders(status, priority);
CREATE INDEX IF NOT EXISTS idx_work_orders_technician_status ON work_orders(assigned_technician_id, status);
CREATE INDEX IF NOT EXISTS idx_chat_messages_channel_created ON chat_messages(channel_type, channel_id, created_at);

-- 8. Procédure stockée pour nettoyage automatique
DELIMITER //
CREATE OR REPLACE PROCEDURE CleanupChronoChatData()
BEGIN
    -- Nettoyer les anciennes présences (plus de 7 jours offline)
    DELETE FROM user_presence 
    WHERE status = 'offline' 
    AND last_seen < DATE_SUB(NOW(), INTERVAL 7 DAY);
    
    -- Nettoyer l'historique Kanban ancien (plus de 6 mois)
    DELETE FROM kanban_history 
    WHERE moved_at < DATE_SUB(NOW(), INTERVAL 6 MONTH);
    
    -- Marquer les vieux attachments comme supprimés (plus de 1 an)
    UPDATE chat_attachments 
    SET is_deleted = TRUE 
    WHERE uploaded_at < DATE_SUB(NOW(), INTERVAL 1 YEAR) 
    AND is_deleted = FALSE;
    
    SELECT 'Nettoyage ChronoChat terminé' as status;
END //
DELIMITER ;

-- 9. Triggers pour mise à jour automatique
DELIMITER //
CREATE OR REPLACE TRIGGER update_kanban_history 
AFTER UPDATE ON work_orders
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO kanban_history (
            task_id, old_status, new_status, moved_by, moved_at
        ) VALUES (
            NEW.id, OLD.status, NEW.status, 
            @current_user_id, NOW()
        );
    END IF;
END //
DELIMITER ;

-- 10. Données d'exemple pour tests (optionnel)
INSERT IGNORE INTO user_presence (user_id, status, last_seen) 
SELECT u.id, 'online', NOW() 
FROM users u 
WHERE u.is_active = 1 
AND u.role IN ('admin', 'manager', 'supervisor', 'technician')
LIMIT 5;

-- ====================================================================
-- RÉSULTAT: Base de données optimisée pour ChronoChat Dashboard
-- - Équipe en ligne temps réel ✅
-- - Kanban avec historique ✅  
-- - Chat avec pièces jointes ✅
-- - Vues optimisées ✅
-- - Nettoyage automatique ✅
-- ====================================================================
