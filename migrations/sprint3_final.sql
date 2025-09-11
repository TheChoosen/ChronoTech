-- Migration Sprint 3 - Collaboration immersive (VERSION FINALE CORRIGÉE)
-- Tables pour portail client, annotations visuelles et tokens

-- Table pour les tokens d'accès client sécurisés
CREATE TABLE IF NOT EXISTS client_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_id INT NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_used BOOLEAN DEFAULT FALSE,
    access_count INT DEFAULT 0,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    INDEX idx_token (token),
    INDEX idx_work_order (work_order_id),
    INDEX idx_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour logger les accès clients (audit)
CREATE TABLE IF NOT EXISTS client_access_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_id INT NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    user_agent TEXT,
    accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    session_duration INT DEFAULT 0,
    pages_viewed INT DEFAULT 1,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    INDEX idx_work_order (work_order_id),
    INDEX idx_accessed_at (accessed_at),
    INDEX idx_ip (ip_address)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour les annotations visuelles (corrigée pour utiliser work_order_media)
CREATE TABLE IF NOT EXISTS visual_annotations (
    id VARCHAR(36) PRIMARY KEY,
    work_order_id INT NOT NULL,
    media_id INT NOT NULL,
    annotation_type ENUM('arrow', 'circle', 'rectangle', 'text', 'freehand', 'highlight', 'problem', 'solution') NOT NULL,
    coordinates JSON NOT NULL,
    text_content TEXT NULL,
    color VARCHAR(7) DEFAULT '#ff0000',
    stroke_width INT DEFAULT 3,
    alpha DECIMAL(3,2) DEFAULT 1.00,
    created_by INT NOT NULL,
    created_by_name VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (media_id) REFERENCES work_order_media(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_work_order (work_order_id),
    INDEX idx_media (media_id),
    INDEX idx_type (annotation_type),
    INDEX idx_created_by (created_by),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour les préférences de notification client
CREATE TABLE IF NOT EXISTS client_notification_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_id INT NOT NULL,
    customer_email VARCHAR(255) NOT NULL,
    notify_on_status_change BOOLEAN DEFAULT TRUE,
    notify_on_completion BOOLEAN DEFAULT TRUE,
    notify_on_notes BOOLEAN DEFAULT FALSE,
    sms_notifications BOOLEAN DEFAULT FALSE,
    phone_number VARCHAR(20) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    UNIQUE KEY unique_work_order_customer (work_order_id, customer_email),
    INDEX idx_work_order (work_order_id),
    INDEX idx_email (customer_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour l'historique des consultations client
CREATE TABLE IF NOT EXISTS client_view_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_id INT NOT NULL,
    viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    progress_at_view INT DEFAULT 0,
    status_at_view VARCHAR(50) NOT NULL,
    view_duration_seconds INT DEFAULT 0,
    ip_address VARCHAR(45) NOT NULL,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    INDEX idx_work_order (work_order_id),
    INDEX idx_viewed_at (viewed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Améliorer la table work_order_notes pour la visibilité client
-- Vérifier si la colonne existe déjà
SET @col_exists = (SELECT COUNT(*) FROM information_schema.columns 
                   WHERE table_schema = DATABASE() 
                   AND table_name = 'work_order_notes' 
                   AND column_name = 'is_client_visible');

SET @sql = IF(@col_exists = 0, 
              'ALTER TABLE work_order_notes ADD COLUMN is_client_visible BOOLEAN DEFAULT FALSE AFTER content',
              'SELECT "Column is_client_visible already exists" as info');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Ajouter l'index pour is_client_visible
CREATE INDEX idx_client_visible ON work_order_notes (is_client_visible);

-- Index pour améliorer les performances des requêtes client
CREATE INDEX idx_wo_customer_status ON work_orders (customer_id, status);
CREATE INDEX idx_wo_updated_at ON work_orders (updated_at DESC);

-- Fonction pour calculer le pourcentage de progression
DELIMITER //
CREATE FUNCTION IF NOT EXISTS GetProgressPercentage(work_order_status VARCHAR(50))
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    CASE work_order_status
        WHEN 'draft' THEN RETURN 5;
        WHEN 'pending' THEN RETURN 10;
        WHEN 'assigned' THEN RETURN 20;
        WHEN 'in_progress' THEN RETURN 60;
        WHEN 'completed' THEN RETURN 100;
        WHEN 'cancelled' THEN RETURN 0;
        ELSE RETURN 0;
    END CASE;
END //
DELIMITER ;

-- Procédure pour nettoyer les tokens expirés
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS CleanExpiredClientTokens()
BEGIN
    DELETE FROM client_tokens 
    WHERE expires_at < NOW() 
    AND (is_used = TRUE OR created_at < DATE_SUB(NOW(), INTERVAL 30 DAY));
    
    SELECT CONCAT('Supprimé ', ROW_COUNT(), ' tokens expirés') as result;
END //
DELIMITER ;

-- Vue pour les statistiques du portail client
CREATE OR REPLACE VIEW client_portal_stats AS
SELECT 
    wo.id as work_order_id,
    wo.status,
    c.name as customer_name,
    c.email as customer_email,
    COUNT(DISTINCT ct.id) as token_count,
    COUNT(DISTINCT cal.id) as access_count,
    COUNT(DISTINCT va.id) as annotation_count,
    MAX(cal.accessed_at) as last_access,
    MIN(cal.accessed_at) as first_access
FROM work_orders wo
LEFT JOIN customers c ON wo.customer_id = c.id
LEFT JOIN client_tokens ct ON wo.id = ct.work_order_id
LEFT JOIN client_access_logs cal ON wo.id = cal.work_order_id
LEFT JOIN visual_annotations va ON wo.id = va.work_order_id
GROUP BY wo.id;

-- Marquer quelques notes comme visibles par les clients
UPDATE work_order_notes 
SET is_client_visible = TRUE 
WHERE content LIKE '%client%' OR content LIKE '%Terminé%' OR content LIKE '%Début%'
LIMIT 10;

-- Insertion de données de test pour le développement
INSERT IGNORE INTO client_tokens (work_order_id, token, expires_at) VALUES
(1, 'test_token_sprint3_123456', DATE_ADD(NOW(), INTERVAL 7 DAY)),
(2, 'demo_token_sprint3_987654', DATE_ADD(NOW(), INTERVAL 7 DAY));

-- Validation Sprint 3
SELECT 
    'Sprint 3 - Collaboration immersive' as component,
    'MIGRATION RÉUSSIE' as status,
    COUNT(*) as table_count
FROM information_schema.tables 
WHERE table_schema = DATABASE() 
AND table_name IN (
    'client_tokens', 
    'client_access_logs', 
    'visual_annotations',
    'client_notification_preferences',
    'client_view_history'
);

COMMIT;
