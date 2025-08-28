-- ========================================
-- SPRINT 1: Schéma & Migrations (DB-first)
-- ========================================
-- Objectif: Rendre techniquement impossible toute tâche hors Bon de travail
-- Date: 2025-08-27
-- Version: 1.0
-- ========================================

-- Désactiver les vérifications de clés étrangères temporairement
SET FOREIGN_KEY_CHECKS = 0;

-- ========================================
-- 1. TABLE: work_order_tasks
-- ========================================
-- Tâches de bon de travail (travaux à faire)
-- Chaque tâche DOIT appartenir à un Bon de travail
CREATE TABLE IF NOT EXISTS work_order_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    task_source ENUM('requested','suggested','preventive') NOT NULL,
    created_by ENUM('operator','ai','system') NOT NULL DEFAULT 'operator',
    status ENUM('pending','assigned','in_progress','done','cancelled') NOT NULL DEFAULT 'pending',
    priority ENUM('low','medium','high','urgent') DEFAULT 'medium',
    technician_id INT NULL,
    estimated_minutes INT NULL,
    scheduled_start DATETIME NULL,
    scheduled_end DATETIME NULL,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    
    -- Contraintes de sécurité
    CONSTRAINT fk_wot_wo FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    CONSTRAINT chk_wot_wo CHECK (work_order_id IS NOT NULL),
    CONSTRAINT chk_wot_title CHECK (TRIM(title) != ''),
    CONSTRAINT chk_wot_estimated CHECK (estimated_minutes IS NULL OR estimated_minutes > 0),
    CONSTRAINT chk_wot_dates CHECK (scheduled_start IS NULL OR scheduled_end IS NULL OR scheduled_start <= scheduled_end)
) ENGINE=InnoDB 
  COMMENT='Tâches de bon de travail - Aucune tâche ne peut exister sans Bon de travail';

-- Index pour les performances
CREATE INDEX idx_wot_wo_status ON work_order_tasks(work_order_id, status);
CREATE INDEX idx_wot_tech_status ON work_order_tasks(technician_id, status);
CREATE INDEX idx_wot_source ON work_order_tasks(task_source);
CREATE INDEX idx_wot_priority ON work_order_tasks(priority);
CREATE INDEX idx_wot_scheduled ON work_order_tasks(scheduled_start, scheduled_end);

-- ========================================
-- 2. TABLE: interventions (refactorée)
-- ========================================
-- Intervention 1-1 avec une tâche spécifique
DROP TABLE IF EXISTS interventions_backup;
CREATE TABLE interventions_backup AS SELECT * FROM interventions;

DROP TABLE IF EXISTS interventions;
CREATE TABLE interventions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_id INT NOT NULL,
    task_id INT NOT NULL UNIQUE,
    technician_id INT NULL,
    started_at DATETIME NULL,
    ended_at DATETIME NULL,
    result_status ENUM('ok','rework','cancelled') DEFAULT 'ok',
    summary TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    
    -- Contraintes de sécurité
    CONSTRAINT fk_int_wo FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    CONSTRAINT fk_int_task FOREIGN KEY (task_id) REFERENCES work_order_tasks(id) ON DELETE CASCADE,
    CONSTRAINT chk_int_dates CHECK (started_at IS NULL OR ended_at IS NULL OR started_at <= ended_at)
) ENGINE=InnoDB 
  COMMENT='Interventions - Une intervention = Une tâche spécifique';

-- Index pour les performances
CREATE INDEX idx_int_wo ON interventions(work_order_id);
CREATE INDEX idx_int_tech ON interventions(technician_id);
CREATE INDEX idx_int_status ON interventions(result_status);
CREATE INDEX idx_int_dates ON interventions(started_at, ended_at);

-- ========================================
-- 3. TABLE: intervention_notes (mise à jour)
-- ========================================
-- S'assurer que les notes référencent interventions.id
DROP TABLE IF EXISTS intervention_notes_backup;
CREATE TABLE intervention_notes_backup AS SELECT * FROM intervention_notes;

DROP TABLE IF EXISTS intervention_notes;
CREATE TABLE intervention_notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    intervention_id INT NOT NULL,
    author_user_id INT NOT NULL,
    note TEXT NOT NULL,
    note_type ENUM('general','issue','solution','recommendation') DEFAULT 'general',
    is_visible_to_customer BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    
    -- Contraintes
    CONSTRAINT fk_in_note FOREIGN KEY (intervention_id) REFERENCES interventions(id) ON DELETE CASCADE,
    CONSTRAINT chk_note_content CHECK (TRIM(note) != '')
) ENGINE=InnoDB 
  COMMENT='Notes d\'intervention - Toujours liées à une intervention valide';

-- Index pour les performances
CREATE INDEX idx_in_intervention ON intervention_notes(intervention_id);
CREATE INDEX idx_in_author ON intervention_notes(author_user_id);
CREATE INDEX idx_in_type ON intervention_notes(note_type);

-- ========================================
-- 4. TABLE: intervention_media (mise à jour)
-- ========================================
-- S'assurer que les médias référencent interventions.id
DROP TABLE IF EXISTS intervention_media_backup;
CREATE TABLE intervention_media_backup AS SELECT * FROM intervention_media;

DROP TABLE IF EXISTS intervention_media;
CREATE TABLE intervention_media (
    id INT AUTO_INCREMENT PRIMARY KEY,
    intervention_id INT NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    media_type ENUM('photo','video','audio','doc','other') NOT NULL,
    file_size_bytes BIGINT DEFAULT 0,
    mime_type VARCHAR(100),
    description TEXT,
    uploaded_by_user_id INT,
    is_before_work BOOLEAN DEFAULT FALSE,
    is_after_work BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Contraintes
    CONSTRAINT fk_in_media FOREIGN KEY (intervention_id) REFERENCES interventions(id) ON DELETE CASCADE,
    CONSTRAINT chk_media_path CHECK (TRIM(file_path) != ''),
    CONSTRAINT chk_media_size CHECK (file_size_bytes >= 0)
) ENGINE=InnoDB 
  COMMENT='Médias d\'intervention - Photos, vidéos, documents';

-- Index pour les performances
CREATE INDEX idx_im_intervention ON intervention_media(intervention_id);
CREATE INDEX idx_im_type ON intervention_media(media_type);
CREATE INDEX idx_im_uploader ON intervention_media(uploaded_by_user_id);

-- ========================================
-- 5. TABLE: work_order_status_history (si absente)
-- ========================================
CREATE TABLE IF NOT EXISTS work_order_status_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_id INT NOT NULL,
    old_status VARCHAR(32),
    new_status VARCHAR(32) NOT NULL,
    changed_by_user_id INT,
    change_reason TEXT,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Contraintes
    CONSTRAINT fk_wosh_wo FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE
) ENGINE=InnoDB 
  COMMENT='Historique des changements de statut des bons de travail';

-- Index pour les performances
CREATE INDEX idx_wosh_wo ON work_order_status_history(work_order_id);
CREATE INDEX idx_wosh_date ON work_order_status_history(changed_at);

-- ========================================
-- 6. TRIGGERS DE GARDE-FOUS
-- ========================================

-- Trigger: Empêcher la création de tâches sans work_order_id
DELIMITER $$
CREATE TRIGGER tr_wot_check_wo_id 
BEFORE INSERT ON work_order_tasks
FOR EACH ROW
BEGIN
    IF NEW.work_order_id IS NULL THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'ERREUR SPRINT 1: Une tâche doit obligatoirement appartenir à un Bon de travail';
    END IF;
    
    -- Vérifier que le work_order existe
    IF NOT EXISTS (SELECT 1 FROM work_orders WHERE id = NEW.work_order_id) THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'ERREUR SPRINT 1: Le Bon de travail spécifié n\'existe pas';
    END IF;
END$$

-- Trigger: Empêcher la création d'intervention sans task_id valide
CREATE TRIGGER tr_int_check_task_id 
BEFORE INSERT ON interventions
FOR EACH ROW
BEGIN
    -- Vérifier que la tâche existe et appartient au bon work_order
    IF NOT EXISTS (
        SELECT 1 FROM work_order_tasks 
        WHERE id = NEW.task_id AND work_order_id = NEW.work_order_id
    ) THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'ERREUR SPRINT 1: La tâche spécifiée n\'appartient pas au Bon de travail';
    END IF;
    
    -- Vérifier qu'une intervention n'existe pas déjà pour cette tâche
    IF EXISTS (SELECT 1 FROM interventions WHERE task_id = NEW.task_id) THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'ERREUR SPRINT 1: Une intervention existe déjà pour cette tâche';
    END IF;
END$$

-- Trigger: Historisation automatique des changements de statut WO
CREATE TRIGGER tr_wo_status_history 
AFTER UPDATE ON work_orders
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO work_order_status_history 
        (work_order_id, old_status, new_status, changed_at) 
        VALUES (NEW.id, OLD.status, NEW.status, NOW());
    END IF;
END$$

-- Trigger: Synchronisation statut tâche -> intervention
CREATE TRIGGER tr_task_status_sync 
AFTER UPDATE ON work_order_tasks
FOR EACH ROW
BEGIN
    -- Mettre à jour les timestamps d'intervention selon le statut de la tâche
    IF OLD.status != NEW.status AND EXISTS (SELECT 1 FROM interventions WHERE task_id = NEW.id) THEN
        CASE NEW.status
            WHEN 'in_progress' THEN
                UPDATE interventions 
                SET started_at = COALESCE(started_at, NOW()) 
                WHERE task_id = NEW.id;
            WHEN 'done' THEN
                UPDATE interventions 
                SET ended_at = COALESCE(ended_at, NOW()) 
                WHERE task_id = NEW.id;
            ELSE BEGIN END;
        END CASE;
    END IF;
END$$

DELIMITER ;

-- ========================================
-- 7. VUES UTILES POUR LE SPRINT 1
-- ========================================

-- Vue: Tâches avec informations complètes
CREATE OR REPLACE VIEW v_work_order_tasks_complete AS
SELECT 
    wot.*,
    wo.title as wo_title,
    wo.status as wo_status,
    wo.customer_id,
    u.name as technician_name,
    i.id as intervention_id,
    i.started_at as intervention_started,
    i.ended_at as intervention_ended,
    i.result_status as intervention_result
FROM work_order_tasks wot
JOIN work_orders wo ON wot.work_order_id = wo.id
LEFT JOIN users u ON wot.technician_id = u.id
LEFT JOIN interventions i ON wot.id = i.task_id;

-- Vue: Interventions avec contexte complet
CREATE OR REPLACE VIEW v_interventions_complete AS
SELECT 
    i.*,
    wot.title as task_title,
    wot.description as task_description,
    wot.task_source,
    wot.priority as task_priority,
    wo.title as wo_title,
    wo.customer_id,
    c.name as customer_name,
    u.name as technician_name,
    COUNT(DISTINCT n.id) as notes_count,
    COUNT(DISTINCT m.id) as media_count
FROM interventions i
JOIN work_order_tasks wot ON i.task_id = wot.id
JOIN work_orders wo ON i.work_order_id = wo.id
LEFT JOIN customers c ON wo.customer_id = c.id
LEFT JOIN users u ON i.technician_id = u.id
LEFT JOIN intervention_notes n ON i.id = n.intervention_id
LEFT JOIN intervention_media m ON i.id = m.intervention_id
GROUP BY i.id;

-- ========================================
-- 8. DONNÉES DE TEST (optionnel)
-- ========================================

-- Exemple de tâches pour les bons de travail existants
INSERT IGNORE INTO work_order_tasks (work_order_id, title, description, task_source, priority) 
SELECT 
    id as work_order_id,
    CONCAT('Tâche principale - ', title) as title,
    CONCAT('Description générée automatiquement pour le WO #', id) as description,
    'requested' as task_source,
    'medium' as priority
FROM work_orders 
WHERE id <= 10
LIMIT 10;

-- ========================================
-- 9. VÉRIFICATIONS FINALES
-- ========================================

-- Réactiver les vérifications de clés étrangères
SET FOREIGN_KEY_CHECKS = 1;

-- Tests de vérification
SELECT 'SPRINT 1 - VÉRIFICATION: Tables créées' as test_status;
SELECT COUNT(*) as work_order_tasks_count FROM work_order_tasks;
SELECT COUNT(*) as interventions_count FROM interventions;
SELECT COUNT(*) as intervention_notes_count FROM intervention_notes;
SELECT COUNT(*) as intervention_media_count FROM intervention_media;

-- Affichage des contraintes actives
SELECT 
    TABLE_NAME,
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE,
    ENFORCED
FROM information_schema.TABLE_CONSTRAINTS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME IN ('work_order_tasks', 'interventions', 'intervention_notes', 'intervention_media')
ORDER BY TABLE_NAME, CONSTRAINT_TYPE;

-- ========================================
-- REMARQUES IMPORTANTES POUR L'ÉQUIPE DEV:
-- ========================================
-- 1. AUCUNE tâche ne peut être créée sans work_order_id (contrainte + trigger)
-- 2. AUCUNE intervention ne peut être créée sans task_id valide (contrainte + trigger)  
-- 3. Relation 1-1 stricte entre intervention et tâche (UNIQUE sur task_id)
-- 4. Historisation automatique des changements de statut
-- 5. Synchronisation automatique statut tâche ↔ intervention
-- 6. Vues préconstruites pour simplifier les requêtes
-- 7. Index optimisés pour les filtres les plus fréquents
-- ========================================

SELECT 'SPRINT 1 TERMINÉ - Architecture sécurisée implémentée' as final_status;
