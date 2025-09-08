-- ====================================================================
-- CORRECTIONS CHRONOCHAT - Compatible MySQL 8.0
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

-- 2. Table pour historique des mouvements Kanban
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

-- 3. Table pour pièces jointes chat
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

-- 4. Améliorer table chat_messages (colonnes une par une)
-- Vérifier et ajouter colonnes manquantes
SET @exist_edited := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE table_schema = DATABASE() AND table_name = 'chat_messages' AND column_name = 'edited_at');

SET @sql = IF(@exist_edited = 0, 
    'ALTER TABLE chat_messages ADD COLUMN edited_at DATETIME NULL', 
    'SELECT "edited_at already exists" as status');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist_parent := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE table_schema = DATABASE() AND table_name = 'chat_messages' AND column_name = 'parent_message_id');

SET @sql = IF(@exist_parent = 0, 
    'ALTER TABLE chat_messages ADD COLUMN parent_message_id INT NULL COMMENT "Pour les threads/réponses"', 
    'SELECT "parent_message_id already exists" as status');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist_type := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE table_schema = DATABASE() AND table_name = 'chat_messages' AND column_name = 'message_type');

SET @sql = IF(@exist_type = 0, 
    'ALTER TABLE chat_messages ADD COLUMN message_type ENUM("text","file","system","notification") DEFAULT "text"', 
    'SELECT "message_type already exists" as status');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist_meta := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE table_schema = DATABASE() AND table_name = 'chat_messages' AND column_name = 'metadata');

SET @sql = IF(@exist_meta = 0, 
    'ALTER TABLE chat_messages ADD COLUMN metadata JSON COMMENT "Données additionnelles (mentions, reactions, etc)"', 
    'SELECT "metadata already exists" as status');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 5. Optimiser calendar_resources
UPDATE calendar_resources SET 
    description = CONCAT(COALESCE(description, ''), ' - Synchronisé ChronoChat'),
    is_active = 1
WHERE description IS NULL OR description NOT LIKE '%ChronoChat%';

-- 6. Index d'optimisation
CREATE INDEX IF NOT EXISTS idx_work_orders_status_priority ON work_orders(status, priority);
CREATE INDEX IF NOT EXISTS idx_work_orders_technician_status ON work_orders(assigned_technician_id, status);
CREATE INDEX IF NOT EXISTS idx_chat_messages_channel_created ON chat_messages(channel_type, channel_id, created_at);

-- 7. Vues optimisées
CREATE OR REPLACE VIEW online_team_view AS
SELECT 
    u.id,
    u.name,
    u.email,
    u.role,
    COALESCE(up.status, 'offline') as status,
    COALESCE(up.last_seen, u.updated_at) as last_seen,
    up.ip_address,
    CASE 
        WHEN up.last_seen >= DATE_SUB(NOW(), INTERVAL 2 MINUTE) THEN 'online'
        WHEN up.last_seen >= DATE_SUB(NOW(), INTERVAL 10 MINUTE) THEN 'away'
        ELSE 'offline'
    END as computed_status,
    COALESCE(TIMESTAMPDIFF(SECOND, up.last_seen, NOW()), 9999) as seconds_since_last_seen
FROM users u
LEFT JOIN user_presence up ON u.id = up.user_id
WHERE u.is_active = 1
AND u.role IN ('admin', 'manager', 'supervisor', 'technician')
ORDER BY 
    CASE WHEN COALESCE(up.status, 'offline') = 'online' THEN 1 
         WHEN COALESCE(up.status, 'offline') = 'away' THEN 2 
         WHEN COALESCE(up.status, 'offline') = 'busy' THEN 3 
         ELSE 4 END,
    u.name;

-- 8. Données de test pour user_presence
INSERT IGNORE INTO user_presence (user_id, status, last_seen) 
SELECT u.id, 'online', NOW() 
FROM users u 
WHERE u.is_active = 1 
AND u.role IN ('admin', 'manager', 'supervisor', 'technician')
LIMIT 5;

-- Vérification finale
SELECT 'ChronoChat corrections appliquées avec succès!' as status,
       COUNT(*) as tables_created
FROM INFORMATION_SCHEMA.TABLES 
WHERE table_schema = DATABASE() 
AND table_name IN ('user_presence', 'kanban_history', 'chat_attachments');
