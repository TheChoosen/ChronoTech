-- Migration pour améliorer la table work_orders pour le calendrier
-- ChronoTech Calendar Enhancement

-- 1. Amélioration de la table work_orders pour le calendrier
-- Vérifier et ajouter les co-- Procédure pour générer des événements récurrents
DROP PROCEDURE IF EXISTS GenerateRecurringEvents//
CREATE PROCEDURE GenerateRecurringEvents(nnes une par une
SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'work_orders' AND column_name = 'recurrence_type' AND table_schema = DATABASE()) = 0, 'ALTER TABLE work_orders ADD COLUMN recurrence_type ENUM(\'none\', \'daily\', \'weekly\', \'monthly\', \'yearly\') DEFAULT \'none\'', 'SELECT "Column recurrence_type already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'work_orders' AND column_name = 'recurrence_interval' AND table_schema = DATABASE()) = 0, 'ALTER TABLE work_orders ADD COLUMN recurrence_interval INT DEFAULT 1', 'SELECT "Column recurrence_interval already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'work_orders' AND column_name = 'recurrence_end_date' AND table_schema = DATABASE()) = 0, 'ALTER TABLE work_orders ADD COLUMN recurrence_end_date DATETIME NULL', 'SELECT "Column recurrence_end_date already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'work_orders' AND column_name = 'is_all_day' AND table_schema = DATABASE()) = 0, 'ALTER TABLE work_orders ADD COLUMN is_all_day BOOLEAN DEFAULT FALSE', 'SELECT "Column is_all_day already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'work_orders' AND column_name = 'event_color' AND table_schema = DATABASE()) = 0, 'ALTER TABLE work_orders ADD COLUMN event_color VARCHAR(7) DEFAULT \'#007bff\'', 'SELECT "Column event_color already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'work_orders' AND column_name = 'parent_event_id' AND table_schema = DATABASE()) = 0, 'ALTER TABLE work_orders ADD COLUMN parent_event_id INT NULL', 'SELECT "Column parent_event_id already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'work_orders' AND column_name = 'is_exception' AND table_schema = DATABASE()) = 0, 'ALTER TABLE work_orders ADD COLUMN is_exception BOOLEAN DEFAULT FALSE', 'SELECT "Column is_exception already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'work_orders' AND column_name = 'exception_date' AND table_schema = DATABASE()) = 0, 'ALTER TABLE work_orders ADD COLUMN exception_date DATETIME NULL', 'SELECT "Column exception_date already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. Ajouter des index pour améliorer les performances du calendrier
-- Vérifier et créer les index s'ils n'existent pas
SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE table_name = 'work_orders' AND index_name = 'idx_work_orders_scheduled_date' AND table_schema = DATABASE()) = 0, 'CREATE INDEX idx_work_orders_scheduled_date ON work_orders(scheduled_date)', 'SELECT "Index idx_work_orders_scheduled_date already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE table_name = 'work_orders' AND index_name = 'idx_work_orders_technician_date' AND table_schema = DATABASE()) = 0, 'CREATE INDEX idx_work_orders_technician_date ON work_orders(assigned_technician_id, scheduled_date)', 'SELECT "Index idx_work_orders_technician_date already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE table_name = 'work_orders' AND index_name = 'idx_work_orders_status_date' AND table_schema = DATABASE()) = 0, 'CREATE INDEX idx_work_orders_status_date ON work_orders(status, scheduled_date)', 'SELECT "Index idx_work_orders_status_date already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE table_name = 'work_orders' AND index_name = 'idx_work_orders_recurrence' AND table_schema = DATABASE()) = 0, 'CREATE INDEX idx_work_orders_recurrence ON work_orders(recurrence_type, parent_event_id)', 'SELECT "Index idx_work_orders_recurrence already exists"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Ajouter une contrainte de clé étrangère pour parent_event_id
ALTER TABLE work_orders 
ADD CONSTRAINT fk_work_orders_parent 
FOREIGN KEY (parent_event_id) REFERENCES work_orders(id) ON DELETE CASCADE;

-- Créer une table pour les exceptions de récurrence (événements modifiés ou supprimés)
CREATE TABLE IF NOT EXISTS recurring_event_exceptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    parent_event_id INT NOT NULL,
    exception_date DATETIME NOT NULL,
    exception_type ENUM('modified', 'deleted') NOT NULL,
    modified_event_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_event_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (modified_event_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    UNIQUE KEY unique_exception (parent_event_id, exception_date)
);

-- Créer une table pour les ressources du calendrier (salles, équipements, etc.)
CREATE TABLE IF NOT EXISTS calendar_resources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type ENUM('room', 'equipment', 'vehicle', 'other') DEFAULT 'other',
    description TEXT,
    capacity INT DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    color VARCHAR(7) DEFAULT '#6c757d',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Créer une table de liaison pour les ressources assignées aux événements
CREATE TABLE IF NOT EXISTS work_order_resources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_id INT NOT NULL,
    resource_id INT NOT NULL,
    quantity INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES calendar_resources(id) ON DELETE CASCADE,
    UNIQUE KEY unique_assignment (work_order_id, resource_id)
);

-- Créer une vue pour les événements du calendrier avec toutes les informations nécessaires
CREATE OR REPLACE VIEW calendar_events_view AS
SELECT 
    w.id,
    w.claim_number,
    w.customer_name,
    w.customer_address,
    w.customer_phone,
    w.description as title,
    w.priority,
    w.status,
    w.scheduled_date as start,
    DATE_ADD(w.scheduled_date, INTERVAL COALESCE(w.estimated_duration, 60) MINUTE) as end,
    w.estimated_duration as duration,
    w.assigned_technician_id as technician_id,
    u.name as technician_name,
    u.email as technician_email,
    w.notes,
    w.recurrence_type,
    w.recurrence_interval,
    w.recurrence_end_date,
    w.is_all_day,
    w.event_color as color,
    w.parent_event_id,
    w.is_exception,
    w.exception_date,
    w.created_at,
    w.updated_at,
    GROUP_CONCAT(DISTINCT ts.name) as required_skills,
    GROUP_CONCAT(DISTINCT CONCAT(cr.name, ':', wor.quantity)) as assigned_resources
FROM work_orders w
LEFT JOIN users u ON w.assigned_technician_id = u.id
LEFT JOIN user_tech_skills uts ON u.id = uts.user_id AND uts.is_active = 1
LEFT JOIN tech_skills ts ON uts.skill_id = ts.id
LEFT JOIN work_order_resources wor ON w.id = wor.work_order_id
LEFT JOIN calendar_resources cr ON wor.resource_id = cr.id AND cr.is_active = 1
WHERE w.scheduled_date IS NOT NULL
GROUP BY w.id, w.claim_number, w.customer_name, w.customer_address, w.customer_phone, 
         w.description, w.priority, w.status, w.scheduled_date, w.estimated_duration,
         w.assigned_technician_id, u.name, u.email, w.notes, w.recurrence_type,
         w.recurrence_interval, w.recurrence_end_date, w.is_all_day, w.event_color,
         w.parent_event_id, w.is_exception, w.exception_date, w.created_at, w.updated_at;

-- Insérer quelques ressources de base
INSERT IGNORE INTO calendar_resources (name, type, description, capacity, color) VALUES
('Salle de réunion A', 'room', 'Salle de réunion principale', 8, '#28a745'),
('Salle de réunion B', 'room', 'Petite salle de réunion', 4, '#17a2b8'),
('Camion 1', 'vehicle', 'Camion de service principal', 1, '#fd7e14'),
('Camion 2', 'vehicle', 'Camion de service secondaire', 1, '#ffc107'),
('Équipement diagnostic', 'equipment', 'Équipement de diagnostic avancé', 1, '#6f42c1'),
('Équipement de nettoyage', 'equipment', 'Équipement de nettoyage professionnel', 2, '#e83e8c');

-- Créer des procédures stockées pour les opérations complexes du calendrier

DELIMITER //

-- Procédure pour vérifier les conflits de ressources
DROP PROCEDURE IF EXISTS CheckResourceConflicts//
CREATE PROCEDURE CheckResourceConflicts(
    IN p_start_date DATETIME,
    IN p_end_date DATETIME,
    IN p_resource_id INT,
    IN p_exclude_work_order_id INT
)
BEGIN
    SELECT 
        w.id,
        w.claim_number,
        w.customer_name,
        w.scheduled_date,
        DATE_ADD(w.scheduled_date, INTERVAL w.estimated_duration MINUTE) as end_time,
        wor.quantity
    FROM work_orders w
    JOIN work_order_resources wor ON w.id = wor.work_order_id
    WHERE wor.resource_id = p_resource_id
    AND w.id != COALESCE(p_exclude_work_order_id, 0)
    AND w.status NOT IN ('cancelled', 'completed')
    AND w.scheduled_date IS NOT NULL
    AND (
        (w.scheduled_date <= p_start_date AND DATE_ADD(w.scheduled_date, INTERVAL w.estimated_duration MINUTE) > p_start_date)
        OR (w.scheduled_date < p_end_date AND DATE_ADD(w.scheduled_date, INTERVAL w.estimated_duration MINUTE) >= p_end_date)
        OR (w.scheduled_date >= p_start_date AND w.scheduled_date < p_end_date)
    );
END //

-- Procédure pour générer les événements récurrents
CREATE PROCEDURE IF NOT EXISTS GenerateRecurringEvents(
    IN p_parent_id INT,
    IN p_start_date DATETIME,
    IN p_end_date DATETIME,
    IN p_recurrence_type VARCHAR(20),
    IN p_interval_value INT
)
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE current_date DATETIME;
    DECLARE base_claim_number VARCHAR(255);
    DECLARE counter INT DEFAULT 1;
    
    -- Récupérer les informations de base de l'événement parent
    SELECT claim_number INTO base_claim_number 
    FROM work_orders WHERE id = p_parent_id;
    
    SET current_date = p_start_date;
    
    -- Boucle pour créer les événements récurrents
    WHILE current_date <= p_end_date DO
        -- Calculer la prochaine date selon le type de récurrence
        CASE p_recurrence_type
            WHEN 'daily' THEN 
                SET current_date = DATE_ADD(current_date, INTERVAL p_interval_value DAY);
            WHEN 'weekly' THEN 
                SET current_date = DATE_ADD(current_date, INTERVAL p_interval_value WEEK);
            WHEN 'monthly' THEN 
                SET current_date = DATE_ADD(current_date, INTERVAL p_interval_value MONTH);
            WHEN 'yearly' THEN 
                SET current_date = DATE_ADD(current_date, INTERVAL p_interval_value YEAR);
            ELSE 
                LEAVE;
        END CASE;
        
        -- Créer un nouvel événement basé sur le parent
        IF current_date <= p_end_date THEN
            INSERT INTO work_orders (
                claim_number, customer_name, customer_address, customer_phone,
                description, priority, status, scheduled_date, estimated_duration,
                assigned_technician_id, notes, parent_event_id,
                recurrence_type, recurrence_interval, recurrence_end_date,
                is_all_day, event_color, created_at, updated_at
            )
            SELECT 
                CONCAT(base_claim_number, '-', LPAD(counter, 3, '0')),
                customer_name, customer_address, customer_phone,
                description, priority, status, current_date, estimated_duration,
                assigned_technician_id, notes, p_parent_id,
                recurrence_type, recurrence_interval, recurrence_end_date,
                is_all_day, event_color, NOW(), NOW()
            FROM work_orders 
            WHERE id = p_parent_id;
            
            SET counter = counter + 1;
        END IF;
        
        -- Sécurité pour éviter les boucles infinies
        IF counter > 1000 THEN
            LEAVE;
        END IF;
    END WHILE;
END //

DELIMITER ;

-- Ajouter des commentaires sur les tables pour la documentation
ALTER TABLE work_orders COMMENT = 'Table principale des bons de travail avec support calendrier avancé';
ALTER TABLE recurring_event_exceptions COMMENT = 'Exceptions pour les événements récurrents (modifications/suppressions)';
ALTER TABLE calendar_resources COMMENT = 'Ressources assignables aux événements (salles, équipements, véhicules)';
ALTER TABLE work_order_resources COMMENT = 'Liaison entre bons de travail et ressources';

-- Optimisations finales
ANALYZE TABLE work_orders;
ANALYZE TABLE recurring_event_exceptions;
ANALYZE TABLE calendar_resources;
ANALYZE TABLE work_order_resources;

SELECT 'Migration calendrier terminée avec succès!' as message;
