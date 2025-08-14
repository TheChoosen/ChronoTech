-- Mise à jour du schéma de base de données ChronoTech
-- Tables manquantes et améliorations

-- Table des clients (manquante dans le schéma original)
CREATE TABLE IF NOT EXISTS `customers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `company` varchar(255) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `mobile` varchar(20) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `postal_code` varchar(10) DEFAULT NULL,
  `city` varchar(100) DEFAULT NULL,
  `country` varchar(100) DEFAULT 'France',
  `vehicle_info` text DEFAULT NULL COMMENT 'Informations sur les véhicules du client',
  `maintenance_history` text DEFAULT NULL COMMENT 'Historique de maintenance',
  `notes` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `email` (`email`),
  KEY `phone` (`phone`),
  KEY `company` (`company`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Mise à jour de la table intervention_notes pour correspondre au code
ALTER TABLE `intervention_notes` 
MODIFY COLUMN `note_type` ENUM('private', 'internal', 'customer') NOT NULL DEFAULT 'private';

-- Table des notifications système
CREATE TABLE IF NOT EXISTS `notifications` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `title` varchar(255) NOT NULL,
  `message` text NOT NULL,
  `type` enum('info', 'success', 'warning', 'error', 'parts_request') NOT NULL DEFAULT 'info',
  `related_id` int(11) DEFAULT NULL,
  `related_type` varchar(50) DEFAULT NULL,
  `is_read` boolean NOT NULL DEFAULT FALSE,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `is_read` (`is_read`),
  KEY `type` (`type`),
  CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table des sessions utilisateur
CREATE TABLE IF NOT EXISTS `user_sessions` (
  `id` varchar(255) NOT NULL,
  `user_id` int(11) NOT NULL,
  `data` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `expires_at` timestamp NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `expires_at` (`expires_at`),
  CONSTRAINT `user_sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table des logs d'activité
CREATE TABLE IF NOT EXISTS `activity_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `action` varchar(100) NOT NULL,
  `entity_type` varchar(50) DEFAULT NULL,
  `entity_id` int(11) DEFAULT NULL,
  `details` json DEFAULT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `action` (`action`),
  KEY `entity_type` (`entity_type`),
  KEY `created_at` (`created_at`),
  CONSTRAINT `activity_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table des paramètres système
CREATE TABLE IF NOT EXISTS `system_settings` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `setting_key` varchar(100) NOT NULL UNIQUE,
  `setting_value` text DEFAULT NULL,
  `setting_type` enum('string', 'integer', 'boolean', 'json') NOT NULL DEFAULT 'string',
  `description` text DEFAULT NULL,
  `is_public` boolean NOT NULL DEFAULT FALSE,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `setting_key` (`setting_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Mise à jour des contraintes pour la table work_orders
ALTER TABLE `work_orders` 
ADD COLUMN `customer_id` int(11) DEFAULT NULL AFTER `created_by_user_id`,
ADD KEY `customer_id` (`customer_id`),
ADD CONSTRAINT `work_orders_ibfk_3` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`) ON DELETE SET NULL;

-- Données de configuration par défaut
INSERT IGNORE INTO `system_settings` (`setting_key`, `setting_value`, `setting_type`, `description`, `is_public`) VALUES
('app_name', 'ChronoTech', 'string', 'Nom de l\'application', true),
('app_version', '2.0.0', 'string', 'Version de l\'application', true),
('maintenance_mode', 'false', 'boolean', 'Mode maintenance activé', false),
('max_upload_size', '16777216', 'integer', 'Taille maximum upload en bytes', false),
('supported_languages', '["fr", "en", "es"]', 'json', 'Langues supportées', true),
('default_language', 'fr', 'string', 'Langue par défaut', true),
('ai_enabled', 'true', 'boolean', 'Fonctionnalités IA activées', false),
('transcription_enabled', 'true', 'boolean', 'Transcription audio activée', false),
('translation_enabled', 'true', 'boolean', 'Traduction automatique activée', false),
('notification_email_enabled', 'false', 'boolean', 'Notifications email activées', false);

-- Données d'exemple pour les clients
INSERT IGNORE INTO `customers` (`id`, `name`, `company`, `email`, `phone`, `address`, `city`, `postal_code`, `vehicle_info`) VALUES
(1, 'Martin Dubois', 'Entreprise ABC', 'martin.dubois@abc.fr', '0123456789', '123 Rue de la Paix', 'Paris', '75001', 'Véhicule utilitaire Renault Master 2020'),
(2, 'Sophie Laurent', 'Société XYZ', 'sophie.laurent@xyz.fr', '0987654321', '456 Avenue des Champs', 'Lyon', '69002', 'Camion Iveco Daily 2019'),
(3, 'Pierre Moreau', 'SARL Tech Plus', 'pierre.moreau@techplus.fr', '0555123456', '789 Boulevard Tech', 'Marseille', '13001', 'Fourgon Peugeot Boxer 2021');

-- Vue pour les statistiques globales
CREATE OR REPLACE VIEW `dashboard_stats` AS
SELECT 
    (SELECT COUNT(*) FROM work_orders WHERE status = 'pending') as pending_orders,
    (SELECT COUNT(*) FROM work_orders WHERE status = 'in_progress') as active_orders,
    (SELECT COUNT(*) FROM work_orders WHERE status = 'completed' AND DATE(completion_date) = CURDATE()) as completed_today,
    (SELECT COUNT(*) FROM work_orders WHERE priority = 'urgent' AND status NOT IN ('completed', 'cancelled')) as urgent_orders,
    (SELECT COUNT(*) FROM users WHERE role = 'technician') as total_technicians,
    (SELECT COUNT(*) FROM customers) as total_customers,
    (SELECT COUNT(*) FROM intervention_notes WHERE DATE(created_at) = CURDATE()) as notes_today,
    (SELECT COUNT(*) FROM intervention_media WHERE DATE(created_at) = CURDATE()) as media_today;

-- Procédure pour nettoyer les anciennes données
DELIMITER //
CREATE PROCEDURE `cleanup_old_data`(IN days_to_keep INT)
BEGIN
    -- Nettoyage des logs d'activité anciens
    DELETE FROM activity_logs WHERE created_at < DATE_SUB(NOW(), INTERVAL days_to_keep DAY);
    
    -- Nettoyage des sessions expirées
    DELETE FROM user_sessions WHERE expires_at < NOW();
    
    -- Nettoyage des notifications anciennes lues
    DELETE FROM notifications WHERE is_read = TRUE AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
    
    SELECT CONCAT('Nettoyage terminé - données antérieures à ', days_to_keep, ' jours supprimées') as result;
END//
DELIMITER ;

-- Index pour améliorer les performances
CREATE INDEX `idx_work_orders_customer_status` ON `work_orders` (`customer_id`, `status`);
CREATE INDEX `idx_intervention_notes_work_order_created` ON `intervention_notes` (`work_order_id`, `created_at`);
CREATE INDEX `idx_intervention_media_work_order_type` ON `intervention_media` (`work_order_id`, `media_type`);
CREATE INDEX `idx_notifications_user_read` ON `notifications` (`user_id`, `is_read`);
CREATE INDEX `idx_activity_logs_user_action` ON `activity_logs` (`user_id`, `action`, `created_at`);

-- Triggers pour l'audit automatique
DELIMITER //
CREATE TRIGGER `work_orders_audit_insert` 
    AFTER INSERT ON `work_orders` 
    FOR EACH ROW 
BEGIN
    INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) 
    VALUES (NEW.created_by_user_id, 'CREATE', 'work_order', NEW.id, JSON_OBJECT('claim_number', NEW.claim_number, 'status', NEW.status));
END//

CREATE TRIGGER `work_orders_audit_update` 
    AFTER UPDATE ON `work_orders` 
    FOR EACH ROW 
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details) 
        VALUES (NEW.created_by_user_id, 'STATUS_CHANGE', 'work_order', NEW.id, 
                JSON_OBJECT('old_status', OLD.status, 'new_status', NEW.status, 'claim_number', NEW.claim_number));
        
        INSERT INTO work_order_status_history (work_order_id, old_status, new_status, changed_by_user_id) 
        VALUES (NEW.id, OLD.status, NEW.status, NEW.created_by_user_id);
    END IF;
END//
DELIMITER ;
