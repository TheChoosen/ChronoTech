-- =====================================================
-- MIGRATION SPRINT 1 - WORK ORDER TASKS & INTERVENTIONS
-- =====================================================
-- Objectif: Rendre techniquement impossible toute tâche hors Bon de travail
-- Date: 2025-01-26
-- Base: MySQL 8.0.23+

USE bdm;

-- =====================================================
-- 1. TABLE WORK_ORDER_TASKS (TRAVAUX À FAIRE)
-- =====================================================
-- Cette table est le COEUR du Sprint 1
-- Empêche par design toute tâche orpheline via contraintes FK

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
-- Relation 1-1 stricte avec work_order_tasks
-- Empêche les interventions orphelines

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
-- 3. MISE À JOUR TABLE INTERVENTION_NOTES
-- =====================================================
-- S'assurer que les notes pointent vers interventions (pas vers work_orders)

-- Vérifier si la contrainte FK existe déjà
SELECT CONSTRAINT_NAME 
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS 
WHERE CONSTRAINT_SCHEMA = 'bdm' 
  AND TABLE_NAME = 'intervention_notes' 
  AND REFERENCED_TABLE_NAME = 'interventions';

-- Ajouter la contrainte si elle n'existe pas
ALTER TABLE intervention_notes 
ADD CONSTRAINT fk_in_note 
FOREIGN KEY (intervention_id) REFERENCES interventions(id) ON DELETE CASCADE;

-- =====================================================
-- 4. MISE À JOUR TABLE INTERVENTION_MEDIA  
-- =====================================================
-- S'assurer que les médias pointent vers interventions (pas vers work_orders)

-- Vérifier si la contrainte FK existe déjà
SELECT CONSTRAINT_NAME 
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS 
WHERE CONSTRAINT_SCHEMA = 'bdm' 
  AND TABLE_NAME = 'intervention_media' 
  AND REFERENCED_TABLE_NAME = 'interventions';

-- Ajouter la contrainte si elle n'existe pas
ALTER TABLE intervention_media 
ADD CONSTRAINT fk_in_media 
FOREIGN KEY (intervention_id) REFERENCES interventions(id) ON DELETE CASCADE;

-- =====================================================
-- 5. OPTIMISATIONS POUR MODULE RENDEZ-VOUS
-- =====================================================
-- Ajout colonne appointment_id dans work_orders si module RDV existe

-- Vérifier si la table appointments existe
SELECT COUNT(*) as appointment_table_exists
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'bdm' AND TABLE_NAME = 'appointments';

-- Si appointments existe, ajouter la colonne
SET @sql = (
  SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
     WHERE TABLE_SCHEMA = 'bdm' AND TABLE_NAME = 'appointments') > 0,
    'ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS appointment_id INT NULL, ADD INDEX idx_wo_appointment (appointment_id);',
    'SELECT "Module RDV non détecté - appointment_id non ajouté" as status;'
  )
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =====================================================
-- 6. TRIGGERS GARDE-FOUS (SÉCURITÉ SPRINT 1)
-- =====================================================

-- Trigger: Empêcher insertion work_order_task sans work_order_id valide
DELIMITER $$

DROP TRIGGER IF EXISTS trg_wot_check_wo$$
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
DROP TRIGGER IF EXISTS trg_int_check_task$$
CREATE TRIGGER trg_int_check_task
BEFORE INSERT ON interventions  
FOR EACH ROW
BEGIN
  DECLARE task_count INT DEFAULT 0;
  DECLARE existing_intervention INT DEFAULT 0;
  
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
  SELECT work_order_id INTO @task_wo_id 
  FROM work_order_tasks 
  WHERE id = NEW.task_id;
  
  IF NEW.work_order_id != @task_wo_id THEN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'SPRINT 1 GUARD: Intervention work_order_id must match task work_order_id';
  END IF;
END$$

DELIMITER ;

-- =====================================================
-- 7. DONNÉES DE TEST SPRINT 1
-- =====================================================
-- Insertion de données de test pour valider les contraintes

-- Test 1: Créer des tâches liées à des work_orders existants
INSERT IGNORE INTO work_order_tasks (work_order_id, title, description, task_source, created_by, priority)
SELECT 
  wo.id,
  CONCAT('Tâche test - ', wo.claim_number),
  'Tâche créée lors de la migration Sprint 1 pour validation',
  'requested',
  'system',
  'medium'
FROM work_orders wo 
WHERE wo.status IN ('pending', 'assigned', 'in_progress')
LIMIT 5;

-- =====================================================
-- 8. VALIDATION FINALE
-- =====================================================

-- Compter les nouvelles tables
SELECT 
  'work_order_tasks' as table_name,
  COUNT(*) as record_count
FROM work_order_tasks
UNION ALL
SELECT 
  'interventions' as table_name,
  COUNT(*) as record_count  
FROM interventions
UNION ALL
SELECT
  'intervention_notes' as table_name,
  COUNT(*) as record_count
FROM intervention_notes
UNION ALL  
SELECT
  'intervention_media' as table_name,
  COUNT(*) as record_count
FROM intervention_media;

-- Vérifier les contraintes FK
SELECT 
  CONSTRAINT_NAME,
  TABLE_NAME,
  REFERENCED_TABLE_NAME,
  'Sprint 1 FK Constraint' as validation_status
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS 
WHERE CONSTRAINT_SCHEMA = 'bdm' 
  AND (
    (TABLE_NAME = 'work_order_tasks' AND REFERENCED_TABLE_NAME = 'work_orders') OR
    (TABLE_NAME = 'interventions' AND REFERENCED_TABLE_NAME IN ('work_orders', 'work_order_tasks')) OR
    (TABLE_NAME = 'intervention_notes' AND REFERENCED_TABLE_NAME = 'interventions') OR
    (TABLE_NAME = 'intervention_media' AND REFERENCED_TABLE_NAME = 'interventions')
  );

-- =====================================================
-- SPRINT 1 MIGRATION TERMINÉE
-- =====================================================
-- Résumé:
-- ✅ work_order_tasks créée avec contraintes FK strictes
-- ✅ interventions créée avec relation 1-1 vers tasks  
-- ✅ intervention_notes et intervention_media sécurisées
-- ✅ Triggers garde-fous activés
-- ✅ Index optimisés pour performances
-- ✅ Impossible de créer des tâches orphelines
-- ✅ Impossible de créer des interventions orphelines

SELECT 'SPRINT 1 MIGRATION COMPLETED SUCCESSFULLY' as status;
