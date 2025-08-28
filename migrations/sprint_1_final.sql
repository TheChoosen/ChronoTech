-- =====================================================
-- MIGRATION SPRINT 1 - WORK ORDER TASKS & INTERVENTIONS (FINALE)
-- =====================================================
-- Objectif: Rendre techniquement impossible toute tâche hors Bon de travail
-- Date: 2025-01-26 - Version finale MySQL 8.0 compatible
-- Base: MySQL 8.0.23+

USE bdm;

-- =====================================================
-- 1. TABLE WORK_ORDER_TASKS (TRAVAUX À FAIRE)
-- =====================================================

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
  
  -- CONTRAINTES CRITIQUES POUR SPRINT 1
  CONSTRAINT fk_wot_wo FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
  CONSTRAINT chk_wot_wo CHECK (work_order_id IS NOT NULL),
  
  -- Index pour performances
  INDEX idx_wot_wo_status (work_order_id, status),
  INDEX idx_wot_tech_status (technician_id, status),
  INDEX idx_wot_source (task_source),
  INDEX idx_wot_priority (priority, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 2. TABLE INTERVENTIONS (1-1 AVEC TASK)
-- =====================================================

CREATE TABLE IF NOT EXISTS interventions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  work_order_id INT NOT NULL,
  task_id INT NOT NULL UNIQUE, -- UNIQUE = relation 1-1 stricte
  technician_id INT NULL,
  started_at DATETIME NULL,
  ended_at DATETIME NULL,
  result_status ENUM('ok','rework','cancelled') DEFAULT 'ok',
  summary TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  -- CONTRAINTES CRITIQUES POUR SPRINT 1
  CONSTRAINT fk_int_wo FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
  CONSTRAINT fk_int_task FOREIGN KEY (task_id) REFERENCES work_order_tasks(id) ON DELETE CASCADE,
  
  -- Index pour performances
  INDEX idx_int_wo (work_order_id),
  INDEX idx_int_tech (technician_id),
  INDEX idx_int_status (result_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 3. ADAPTATION DES TABLES EXISTANTES
-- =====================================================

-- Vérifier et ajouter intervention_id à intervention_notes
SET @count_notes = (
  SELECT COUNT(*) 
  FROM INFORMATION_SCHEMA.COLUMNS 
  WHERE TABLE_SCHEMA = 'bdm' 
    AND TABLE_NAME = 'intervention_notes' 
    AND COLUMN_NAME = 'intervention_id'
);

SET @sql_notes = IF(@count_notes = 0, 
  'ALTER TABLE intervention_notes ADD COLUMN intervention_id INT NULL AFTER id, ADD INDEX idx_in_intervention (intervention_id);',
  'SELECT "intervention_id already exists in intervention_notes" as status;'
);

PREPARE stmt FROM @sql_notes;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Vérifier et ajouter intervention_id à intervention_media
SET @count_media = (
  SELECT COUNT(*) 
  FROM INFORMATION_SCHEMA.COLUMNS 
  WHERE TABLE_SCHEMA = 'bdm' 
    AND TABLE_NAME = 'intervention_media' 
    AND COLUMN_NAME = 'intervention_id'
);

SET @sql_media = IF(@count_media = 0, 
  'ALTER TABLE intervention_media ADD COLUMN intervention_id INT NULL AFTER id, ADD INDEX idx_im_intervention (intervention_id);',
  'SELECT "intervention_id already exists in intervention_media" as status;'
);

PREPARE stmt FROM @sql_media;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =====================================================
-- 4. APPOINTMENT_ID POUR MODULE RDV
-- =====================================================

SET @count_appointment = (
  SELECT COUNT(*) 
  FROM INFORMATION_SCHEMA.COLUMNS 
  WHERE TABLE_SCHEMA = 'bdm' 
    AND TABLE_NAME = 'work_orders' 
    AND COLUMN_NAME = 'appointment_id'
);

SET @sql_appointment = IF(@count_appointment = 0, 
  'ALTER TABLE work_orders ADD COLUMN appointment_id INT NULL, ADD INDEX idx_wo_appointment (appointment_id);',
  'SELECT "appointment_id already exists in work_orders" as status;'
);

PREPARE stmt FROM @sql_appointment;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =====================================================
-- 5. TRIGGERS GARDE-FOUS (SÉCURITÉ SPRINT 1)
-- =====================================================

DELIMITER $$

-- Supprimer les triggers existants s'ils existent
DROP TRIGGER IF EXISTS trg_wot_check_wo$$
DROP TRIGGER IF EXISTS trg_int_check_task$$

-- Trigger: Empêcher insertion work_order_task sans work_order_id valide
CREATE TRIGGER trg_wot_check_wo 
BEFORE INSERT ON work_order_tasks
FOR EACH ROW
BEGIN
  DECLARE wo_count INT DEFAULT 0;
  
  -- Vérifier que le work_order existe
  SELECT COUNT(*) INTO wo_count 
  FROM work_orders 
  WHERE id = NEW.work_order_id;
  
  IF wo_count = 0 THEN
    SIGNAL SQLSTATE '45000' 
    SET MESSAGE_TEXT = 'SPRINT 1 GUARD: Cannot create task without valid work_order_id';
  END IF;
  
  -- Forcer task_source à être non-NULL  
  IF NEW.task_source IS NULL THEN
    SIGNAL SQLSTATE '45000' 
    SET MESSAGE_TEXT = 'SPRINT 1 GUARD: task_source is required (requested/suggested/preventive)';
  END IF;
END$$

-- Trigger: Empêcher intervention sans task_id valide et unique
CREATE TRIGGER trg_int_check_task
BEFORE INSERT ON interventions  
FOR EACH ROW
BEGIN
  DECLARE task_count INT DEFAULT 0;
  DECLARE existing_intervention INT DEFAULT 0;
  DECLARE task_wo_id INT DEFAULT 0;
  
  -- Vérifier que la tâche existe
  SELECT COUNT(*) INTO task_count 
  FROM work_order_tasks 
  WHERE id = NEW.task_id;
  
  IF task_count = 0 THEN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'SPRINT 1 GUARD: Cannot create intervention without valid task_id';
  END IF;
  
  -- Vérifier qu'il n'y a pas déjà une intervention pour cette tâche
  SELECT COUNT(*) INTO existing_intervention
  FROM interventions 
  WHERE task_id = NEW.task_id;
  
  IF existing_intervention > 0 THEN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'SPRINT 1 GUARD: Task already has an intervention (1-1 relationship)';
  END IF;
  
  -- S'assurer que work_order_id correspond à celui de la tâche
  SELECT work_order_id INTO task_wo_id 
  FROM work_order_tasks 
  WHERE id = NEW.task_id;
  
  IF NEW.work_order_id != task_wo_id THEN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'SPRINT 1 GUARD: Intervention work_order_id must match task work_order_id';
  END IF;
END$$

DELIMITER ;

-- =====================================================
-- 6. DONNÉES DE TEST SPRINT 1
-- =====================================================

-- Insérer des tâches test pour validation
INSERT IGNORE INTO work_order_tasks (work_order_id, title, description, task_source, created_by, priority)
SELECT 
  wo.id,
  CONCAT('Tâche test Sprint 1 - ', wo.claim_number),
  'Tâche créée lors de la migration Sprint 1 pour validation des contraintes',
  'requested',
  'system',
  'medium'
FROM work_orders wo 
WHERE wo.status IN ('pending', 'assigned', 'in_progress')
LIMIT 5;

-- Insérer une intervention test
INSERT IGNORE INTO interventions (work_order_id, task_id, technician_id, summary)
SELECT 
  wot.work_order_id,
  wot.id,
  NULL,
  'Intervention test créée lors de la migration Sprint 1'
FROM work_order_tasks wot
WHERE wot.created_by = 'system'
  AND NOT EXISTS (SELECT 1 FROM interventions WHERE task_id = wot.id)
LIMIT 1;

-- =====================================================
-- 7. VALIDATION FINALE
-- =====================================================

SELECT 'VALIDATION SPRINT 1 - TABLES CRÉÉES' as section;

SELECT 
  'work_order_tasks' as table_name,
  COUNT(*) as record_count,
  'Core Sprint 1 table' as description
FROM work_order_tasks
UNION ALL
SELECT 
  'interventions' as table_name,
  COUNT(*) as record_count,
  '1-1 relationship with tasks' as description
FROM interventions
UNION ALL
SELECT
  'intervention_notes' as table_name,
  COUNT(*) as record_count,
  'Notes linked to interventions' as description
FROM intervention_notes
UNION ALL  
SELECT
  'intervention_media' as table_name,
  COUNT(*) as record_count,
  'Media linked to interventions' as description
FROM intervention_media;

SELECT 'VALIDATION SPRINT 1 - CONTRAINTES FK' as section;

SELECT 
  CONSTRAINT_NAME,
  TABLE_NAME,
  REFERENCED_TABLE_NAME,
  'Critical Sprint 1 Constraint' as status
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS 
WHERE CONSTRAINT_SCHEMA = 'bdm' 
  AND (
    (TABLE_NAME = 'work_order_tasks' AND REFERENCED_TABLE_NAME = 'work_orders') OR
    (TABLE_NAME = 'interventions' AND REFERENCED_TABLE_NAME IN ('work_orders', 'work_order_tasks'))
  );

SELECT 'VALIDATION SPRINT 1 - TRIGGERS SÉCURITÉ' as section;

SELECT 
  TRIGGER_NAME,
  EVENT_MANIPULATION,
  EVENT_OBJECT_TABLE,
  'Anti-orphan Security Trigger' as status
FROM INFORMATION_SCHEMA.TRIGGERS
WHERE TRIGGER_SCHEMA = 'bdm'
  AND TRIGGER_NAME IN ('trg_wot_check_wo', 'trg_int_check_task');

SELECT 'VALIDATION SPRINT 1 - COLONNES AJOUTÉES' as section;

SELECT 
  TABLE_NAME,
  COLUMN_NAME,
  DATA_TYPE,
  'New column for Sprint 1' as status
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'bdm'
  AND (
    (TABLE_NAME = 'intervention_notes' AND COLUMN_NAME = 'intervention_id') OR
    (TABLE_NAME = 'intervention_media' AND COLUMN_NAME = 'intervention_id') OR
    (TABLE_NAME = 'work_orders' AND COLUMN_NAME = 'appointment_id')
  );

-- =====================================================
-- SPRINT 1 TERMINÉ AVEC SUCCÈS
-- =====================================================

SELECT 
  'SPRINT 1 MIGRATION COMPLETED SUCCESSFULLY' as status,
  'Anti-orphan architecture is now active' as description,
  'Ready for Sprint 2 API development' as next_step;
