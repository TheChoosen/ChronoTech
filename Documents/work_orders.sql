-- Tables pour les travaux demandés (Work Orders)
CREATE TABLE IF NOT EXISTS `work_orders` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `claim_number` varchar(50) NOT NULL UNIQUE,
  `customer_name` varchar(255) NOT NULL,
  `customer_address` text NOT NULL,
  `customer_phone` varchar(20) DEFAULT NULL,
  `customer_email` varchar(255) DEFAULT NULL,
  `description` text NOT NULL,
  `priority` enum('low', 'medium', 'high', 'urgent') NOT NULL DEFAULT 'medium',
  `status` enum('draft', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled') NOT NULL DEFAULT 'draft',
  `assigned_technician_id` int(11) DEFAULT NULL,
  `created_by_user_id` int(11) NOT NULL,
  `estimated_duration` int(11) DEFAULT NULL COMMENT 'Durée estimée en minutes',
  `estimated_cost` decimal(10,2) DEFAULT NULL,
  `actual_duration` int(11) DEFAULT NULL COMMENT 'Durée réelle en minutes',
  `actual_cost` decimal(10,2) DEFAULT NULL,
  `scheduled_date` datetime DEFAULT NULL,
  `completion_date` datetime DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `assigned_technician_id` (`assigned_technician_id`),
  KEY `created_by_user_id` (`created_by_user_id`),
  KEY `status` (`status`),
  KEY `priority` (`priority`),
  KEY `scheduled_date` (`scheduled_date`),
  CONSTRAINT `work_orders_ibfk_1` FOREIGN KEY (`assigned_technician_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `work_orders_ibfk_2` FOREIGN KEY (`created_by_user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Table pour les produits/matériaux liés aux travaux
CREATE TABLE IF NOT EXISTS `work_order_products` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `work_order_id` int(11) NOT NULL,
  `product_name` varchar(255) NOT NULL,
  `product_reference` varchar(100) DEFAULT NULL,
  `quantity` decimal(10,2) NOT NULL DEFAULT 1.00,
  `unit_price` decimal(10,2) DEFAULT NULL,
  `total_price` decimal(10,2) DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `work_order_id` (`work_order_id`),
  CONSTRAINT `work_order_products_ibfk_1` FOREIGN KEY (`work_order_id`) REFERENCES `work_orders` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Table pour l'historique des changements de statut
CREATE TABLE IF NOT EXISTS `work_order_status_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `work_order_id` int(11) NOT NULL,
  `old_status` varchar(50) DEFAULT NULL,
  `new_status` varchar(50) NOT NULL,
  `changed_by_user_id` int(11) NOT NULL,
  `change_reason` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `work_order_id` (`work_order_id`),
  KEY `changed_by_user_id` (`changed_by_user_id`),
  CONSTRAINT `work_order_status_history_ibfk_1` FOREIGN KEY (`work_order_id`) REFERENCES `work_orders` (`id`) ON DELETE CASCADE,
  CONSTRAINT `work_order_status_history_ibfk_2` FOREIGN KEY (`changed_by_user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Table pour les lignes détaillées des bons de travail (Work Order Lines)
-- Cette table stocke chaque ligne individuelle d'un bon de travail avec ses détails opérationnels

CREATE TABLE IF NOT EXISTS `work_order_lines` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `work_order_id` int(11) NOT NULL COMMENT 'Référence vers le bon de travail parent',
  `CODE` varchar(100) NOT NULL COMMENT 'Code de la pièce ou opération (ex: PCS001)',
  `DESC` text NOT NULL COMMENT 'Description détaillée de la ligne',
  `QUANT` decimal(10,3) NOT NULL DEFAULT 1.000 COMMENT 'Quantité (peut être décimale)',
  `COUT` decimal(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Coût unitaire en euros',
  `MONTANT` decimal(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Montant total (QUANT * COUT)',
  `STATUS` enum('A', 'F', 'X') NOT NULL DEFAULT 'A' COMMENT 'A=Active, F=Facturée, X=Annulée',
  `line_order` int(11) DEFAULT NULL COMMENT 'Ordre d\'affichage des lignes',
  `notes` text DEFAULT NULL COMMENT 'Notes complémentaires sur la ligne',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `work_order_id` (`work_order_id`),
  KEY `CODE` (`CODE`),
  KEY `STATUS` (`STATUS`),
  KEY `line_order` (`line_order`),
  CONSTRAINT `work_order_lines_ibfk_1` FOREIGN KEY (`work_order_id`) REFERENCES `work_orders` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Lignes détaillées des bons de travail avec codes, quantités et coûts';

-- Index composite pour optimiser les requêtes fréquentes
CREATE INDEX `idx_work_order_status` ON `work_order_lines` (`work_order_id`, `STATUS`);
CREATE INDEX `idx_work_order_order` ON `work_order_lines` (`work_order_id`, `line_order`);

-- Trigger pour calculer automatiquement le MONTANT lors de l'insertion/mise à jour
DELIMITER //
CREATE TRIGGER `calculate_work_order_line_amount_insert` 
    BEFORE INSERT ON `work_order_lines` 
    FOR EACH ROW 
BEGIN
    -- Calculer automatiquement le montant si non fourni ou si égal à 0
    IF NEW.MONTANT = 0 OR NEW.MONTANT IS NULL THEN
        SET NEW.MONTANT = NEW.QUANT * NEW.COUT;
    END IF;
END//

CREATE TRIGGER `calculate_work_order_line_amount_update` 
    BEFORE UPDATE ON `work_order_lines` 
    FOR EACH ROW 
BEGIN
    -- Recalculer le montant si la quantité ou le coût change
    IF NEW.QUANT != OLD.QUANT OR NEW.COUT != OLD.COUT THEN
        SET NEW.MONTANT = NEW.QUANT * NEW.COUT;
    END IF;
END//
DELIMITER ;

-- Vue pour obtenir des statistiques par bon de travail
CREATE OR REPLACE VIEW `work_order_lines_summary` AS
SELECT 
    wol.work_order_id,
    wo.claim_number,
    wo.customer_name,
    COUNT(wol.id) as total_lines,
    COUNT(CASE WHEN wol.STATUS = 'A' THEN 1 END) as active_lines,
    COUNT(CASE WHEN wol.STATUS = 'F' THEN 1 END) as billed_lines,
    COUNT(CASE WHEN wol.STATUS = 'X' THEN 1 END) as cancelled_lines,
    SUM(wol.MONTANT) as total_amount,
    SUM(CASE WHEN wol.STATUS = 'A' THEN wol.MONTANT ELSE 0 END) as active_amount,
    SUM(CASE WHEN wol.STATUS = 'F' THEN wol.MONTANT ELSE 0 END) as billed_amount,
    AVG(wol.COUT) as average_unit_cost,
    SUM(wol.QUANT) as total_quantity
FROM work_order_lines wol
INNER JOIN work_orders wo ON wol.work_order_id = wo.id
GROUP BY wol.work_order_id, wo.claim_number, wo.customer_name;

-- Procédure stockée pour dupliquer les lignes d'un bon de travail vers un autre
DELIMITER //
CREATE PROCEDURE `duplicate_work_order_lines`(
    IN source_work_order_id INT,
    IN target_work_order_id INT
)
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_code VARCHAR(100);
    DECLARE v_desc TEXT;
    DECLARE v_quant DECIMAL(10,3);
    DECLARE v_cout DECIMAL(10,2);
    DECLARE v_status ENUM('A', 'F', 'X');
    DECLARE v_notes TEXT;
    
    DECLARE cur CURSOR FOR 
        SELECT CODE, `DESC`, QUANT, COUT, STATUS, notes 
        FROM work_order_lines 
        WHERE work_order_id = source_work_order_id 
        ORDER BY line_order, id;
    
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    OPEN cur;
    
    read_loop: LOOP
        FETCH cur INTO v_code, v_desc, v_quant, v_cout, v_status, v_notes;
        
        IF done THEN
            LEAVE read_loop;
        END IF;
        
        INSERT INTO work_order_lines (
            work_order_id, CODE, `DESC`, QUANT, COUT, STATUS, notes
        ) VALUES (
            target_work_order_id, v_code, v_desc, v_quant, v_cout, 'A', v_notes
        );
    END LOOP;
    
    CLOSE cur;
END//
DELIMITER ;

-- Données d'exemple pour tester la table
INSERT INTO `work_order_lines` (`work_order_id`, `CODE`, `DESC`, `QUANT`, `COUT`, `STATUS`, `line_order`) VALUES
(1, 'PCS001', 'Pièce de rechange principale', 2.000, 45.50, 'A', 1),
(1, 'LAB001', 'Main d\'œuvre installation', 3.500, 65.00, 'A', 2),
(1, 'MAT002', 'Matériel consommable', 1.000, 12.75, 'F', 3),
(2, 'PCS002', 'Composant électronique', 1.000, 125.00, 'A', 1),
(2, 'LAB002', 'Diagnostic technique', 2.000, 80.00, 'A', 2);

-- Requêtes utiles pour la gestion des lignes de bon de travail

-- 1. Obtenir toutes les lignes d'un bon de travail avec calcul des totaux
/*
SELECT 
    wol.*,
    (wol.QUANT * wol.COUT) as calculated_amount,
    CASE wol.STATUS 
        WHEN 'A' THEN 'Active'
        WHEN 'F' THEN 'Facturée' 
        WHEN 'X' THEN 'Annulée'
    END as status_label
FROM work_order_lines wol 
WHERE wol.work_order_id = ? 
ORDER BY wol.line_order, wol.id;
*/

-- 2. Résumé financier d'un bon de travail
/*
SELECT 
    COUNT(*) as total_lines,
    SUM(MONTANT) as total_amount,
    SUM(CASE WHEN STATUS = 'A' THEN MONTANT ELSE 0 END) as active_amount,
    SUM(CASE WHEN STATUS = 'F' THEN MONTANT ELSE 0 END) as billed_amount,
    AVG(COUT) as average_unit_cost
FROM work_order_lines 
WHERE work_order_id = ?;
*/

-- 3. Top des codes les plus utilisés
/*
SELECT 
    CODE,
    COUNT(*) as usage_count,
    AVG(COUT) as average_cost,
    SUM(QUANT) as total_quantity
FROM work_order_lines 
GROUP BY CODE 
ORDER BY usage_count DESC 
LIMIT 10;
*/

CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` varchar(255) NOT NULL DEFAULT 'technician',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `interventions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `customer_name` varchar(255) NOT NULL,
  `customer_address` text NOT NULL,
  `status` varchar(255) NOT NULL DEFAULT 'pending',
  `technician_id` int(11) DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `technician_id` (`technician_id`),
  CONSTRAINT `interventions_ibfk_1` FOREIGN KEY (`technician_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `intervention_steps` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `intervention_id` int(11) NOT NULL,
  `description` text NOT NULL,
  `timestamp` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `intervention_id` (`intervention_id`),
  CONSTRAINT `intervention_steps_ibfk_1` FOREIGN KEY (`intervention_id`) REFERENCES `interventions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE intervention_notes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  work_order_id INT NOT NULL,
  technician_id INT NOT NULL,
  note_type ENUM('public', 'private') NOT NULL DEFAULT 'private',
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
  FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE intervention_media (
  id INT AUTO_INCREMENT PRIMARY KEY,
  work_order_id INT NOT NULL,
  technician_id INT NOT NULL,
  media_type ENUM('photo', 'video', 'audio') NOT NULL,
  file_path VARCHAR(500) NOT NULL,
  transcription TEXT NULL,
  translation_fr TEXT NULL,
  translation_en TEXT NULL,
  translation_es TEXT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
  FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE CASCADE
);
