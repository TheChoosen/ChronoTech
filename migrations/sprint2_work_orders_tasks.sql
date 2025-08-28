-- Migration Sprint 2 - Interventions & Work Orders Tasks
-- DDL MySQL 8.0.23 (idempotent) - Création des tables manquantes
-- Rend techniquement impossible toute tâche hors Bon de travail

-- ===============================================
-- 1. TÂCHES DE BON DE TRAVAIL (TRAVAUX À FAIRE)
-- ===============================================

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
  
  -- Contraintes d'intégrité
  CONSTRAINT fk_wot_wo FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
  CONSTRAINT fk_wot_tech FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT chk_wot_wo CHECK (work_order_id IS NOT NULL),
  CONSTRAINT chk_wot_title CHECK (LENGTH(TRIM(title)) >= 3),
  CONSTRAINT chk_wot_estimated_minutes CHECK (estimated_minutes IS NULL OR estimated_minutes > 0),
  CONSTRAINT chk_wot_scheduled_order CHECK (scheduled_start IS NULL OR scheduled_end IS NULL OR scheduled_start <= scheduled_end),
  CONSTRAINT chk_wot_execution_order CHECK (started_at IS NULL OR completed_at IS NULL OR started_at <= completed_at)
) ENGINE=InnoDB COMMENT='Tâches de bon de travail - Sprint 2';

-- Index pour les performances
CREATE INDEX idx_wot_wo_status ON work_order_tasks(work_order_id, status);
CREATE INDEX idx_wot_tech_status ON work_order_tasks(technician_id, status);
CREATE INDEX idx_wot_source_priority ON work_order_tasks(task_source, priority);
CREATE INDEX idx_wot_scheduled ON work_order_tasks(scheduled_start, scheduled_end);

-- ===============================================
-- 2. INTERVENTIONS (1-1 AVEC TÂCHE)
-- ===============================================

CREATE TABLE IF NOT EXISTS interventions (
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
  
  -- Contraintes d'intégrité
  CONSTRAINT fk_int_wo FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
  CONSTRAINT fk_int_task FOREIGN KEY (task_id) REFERENCES work_order_tasks(id) ON DELETE CASCADE,
  CONSTRAINT fk_int_tech FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT chk_int_execution_order CHECK (started_at IS NULL OR ended_at IS NULL OR started_at <= ended_at)
) ENGINE=InnoDB COMMENT='Interventions - Relation 1-1 avec tâches - Sprint 2';

-- Index pour les performances
CREATE INDEX idx_int_wo ON interventions(work_order_id);
CREATE INDEX idx_int_tech_status ON interventions(technician_id, result_status);
CREATE INDEX idx_int_dates ON interventions(started_at, ended_at);

-- ===============================================
-- 3. NOTES D'INTERVENTION
-- ===============================================

-- Mise à jour de la table existante si nécessaire
ALTER TABLE intervention_notes 
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP;

-- Vérification et ajout de contraintes si nécessaire
ALTER TABLE intervention_notes 
  ADD CONSTRAINT IF NOT EXISTS fk_in_note_intervention 
    FOREIGN KEY (intervention_id) REFERENCES interventions(id) ON DELETE CASCADE,
  ADD CONSTRAINT IF NOT EXISTS fk_in_note_author 
    FOREIGN KEY (author_user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Index pour les performances
CREATE INDEX IF NOT EXISTS idx_in_intervention_date ON intervention_notes(intervention_id, created_at);

-- ===============================================
-- 4. MÉDIAS D'INTERVENTION
-- ===============================================

-- Mise à jour de la table existante
ALTER TABLE intervention_media 
  ADD COLUMN IF NOT EXISTS original_filename VARCHAR(255) NULL AFTER file_path,
  ADD COLUMN IF NOT EXISTS file_size INT NULL AFTER media_type,
  ADD COLUMN IF NOT EXISTS is_before_work BOOLEAN DEFAULT FALSE AFTER file_size,
  ADD COLUMN IF NOT EXISTS is_after_work BOOLEAN DEFAULT FALSE AFTER is_before_work,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP;

-- Mise à jour de l'enum media_type
ALTER TABLE intervention_media 
  MODIFY COLUMN media_type ENUM('photo','video','audio','doc','other') NOT NULL;

-- Contraintes d'intégrité
ALTER TABLE intervention_media 
  ADD CONSTRAINT IF NOT EXISTS fk_in_media_intervention 
    FOREIGN KEY (intervention_id) REFERENCES interventions(id) ON DELETE CASCADE;

-- Index pour les performances
CREATE INDEX IF NOT EXISTS idx_im_intervention_type ON intervention_media(intervention_id, media_type);
CREATE INDEX IF NOT EXISTS idx_im_work_phase ON intervention_media(intervention_id, is_before_work, is_after_work);

-- ===============================================
-- 5. HISTORIQUE DE STATUT WORK ORDER
-- ===============================================

CREATE TABLE IF NOT EXISTS work_order_status_history (
  id INT AUTO_INCREMENT PRIMARY KEY,
  work_order_id INT NOT NULL,
  old_status VARCHAR(32),
  new_status VARCHAR(32) NOT NULL,
  changed_by_user_id INT,
  reason TEXT,
  changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  -- Contraintes d'intégrité
  CONSTRAINT fk_wosh_wo FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
  CONSTRAINT fk_wosh_user FOREIGN KEY (changed_by_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Historique des changements de statut - Sprint 2';

-- Index pour les performances
CREATE INDEX idx_wosh_wo_date ON work_order_status_history(work_order_id, changed_at);
CREATE INDEX idx_wosh_user ON work_order_status_history(changed_by_user_id);

-- ===============================================
-- 6. AMÉLIORATIONS WORK_ORDERS (OPTIONNEL)
-- ===============================================

-- Ajout de colonnes utiles pour le suivi
ALTER TABLE work_orders 
  ADD COLUMN IF NOT EXISTS closed_at DATETIME NULL AFTER updated_at,
  ADD COLUMN IF NOT EXISTS closing_notes TEXT NULL AFTER closed_at,
  ADD COLUMN IF NOT EXISTS has_no_parts_used BOOLEAN DEFAULT FALSE AFTER closing_notes;

-- Index pour les recherches par date de fermeture
CREATE INDEX IF NOT EXISTS idx_wo_closed_at ON work_orders(closed_at);

-- ===============================================
-- 7. TRIGGERS DE VALIDATION (GARDE-FOUS)
-- ===============================================

-- Trigger pour empêcher la création de tâches orphelines
DELIMITER $$
CREATE TRIGGER IF NOT EXISTS trg_wot_prevent_orphan
  BEFORE INSERT ON work_order_tasks
  FOR EACH ROW
BEGIN
  IF NEW.work_order_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'work_order_id cannot be NULL - Orphan tasks not allowed';
  END IF;
  
  -- Vérifier que le work_order existe
  IF NOT EXISTS (SELECT 1 FROM work_orders WHERE id = NEW.work_order_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Referenced work_order does not exist';
  END IF;
END$$
DELIMITER ;

-- Trigger pour maintenir la cohérence intervention/tâche
DELIMITER $$
CREATE TRIGGER IF NOT EXISTS trg_int_task_consistency
  BEFORE INSERT ON interventions
  FOR EACH ROW
BEGIN
  DECLARE task_wo_id INT;
  
  -- Récupérer le work_order_id de la tâche
  SELECT work_order_id INTO task_wo_id 
  FROM work_order_tasks 
  WHERE id = NEW.task_id;
  
  -- Vérifier la cohérence
  IF task_wo_id != NEW.work_order_id THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Intervention work_order_id must match task work_order_id';
  END IF;
END$$
DELIMITER ;

-- Trigger pour historiser les changements de statut
DELIMITER $$
CREATE TRIGGER IF NOT EXISTS trg_wo_status_history
  AFTER UPDATE ON work_orders
  FOR EACH ROW
BEGIN
  IF OLD.status != NEW.status THEN
    INSERT INTO work_order_status_history 
    (work_order_id, old_status, new_status, changed_at)
    VALUES (NEW.id, OLD.status, NEW.status, NOW());
  END IF;
END$$
DELIMITER ;

-- ===============================================
-- 8. VUES UTILES POUR LES RAPPORTS
-- ===============================================

-- Vue des tâches avec informations complètes
CREATE OR REPLACE VIEW v_work_order_tasks_complete AS
SELECT 
  wot.*,
  wo.title as wo_title,
  wo.status as wo_status,
  wo.customer_id,
  u.name as technician_name,
  c.name as customer_name,
  i.id as intervention_id,
  i.started_at as intervention_started,
  i.ended_at as intervention_ended,
  i.result_status as intervention_result,
  CASE 
    WHEN wot.completed_at IS NOT NULL THEN 
      TIMESTAMPDIFF(MINUTE, wot.started_at, wot.completed_at)
    WHEN wot.started_at IS NOT NULL THEN 
      TIMESTAMPDIFF(MINUTE, wot.started_at, NOW())
    ELSE NULL
  END as duration_minutes
FROM work_order_tasks wot
JOIN work_orders wo ON wot.work_order_id = wo.id
LEFT JOIN users u ON wot.technician_id = u.id
LEFT JOIN customers c ON wo.customer_id = c.id
LEFT JOIN interventions i ON wot.id = i.task_id;

-- Vue des interventions avec informations complètes
CREATE OR REPLACE VIEW v_interventions_complete AS
SELECT 
  i.*,
  wot.title as task_title,
  wot.task_source,
  wot.priority as task_priority,
  wo.title as wo_title,
  wo.status as wo_status,
  wo.customer_id,
  u.name as technician_name,
  c.name as customer_name,
  COUNT(DISTINCT in_.id) as notes_count,
  COUNT(DISTINCT im.id) as media_count,
  TIMESTAMPDIFF(MINUTE, i.started_at, COALESCE(i.ended_at, NOW())) as duration_minutes
FROM interventions i
JOIN work_order_tasks wot ON i.task_id = wot.id
JOIN work_orders wo ON i.work_order_id = wo.id
LEFT JOIN users u ON i.technician_id = u.id
LEFT JOIN customers c ON wo.customer_id = c.id
LEFT JOIN intervention_notes in_ ON i.id = in_.intervention_id
LEFT JOIN intervention_media im ON i.id = im.intervention_id
GROUP BY i.id;

-- ===============================================
-- 9. DONNÉES DE TEST (OPTIONNEL)
-- ===============================================

-- Insertion de quelques tâches de test si aucune n'existe
INSERT IGNORE INTO work_order_tasks 
(work_order_id, title, description, task_source, priority)
SELECT 
  wo.id,
  CASE 
    WHEN wo.id % 3 = 0 THEN 'Vérification générale véhicule'
    WHEN wo.id % 3 = 1 THEN 'Changement huile moteur'
    ELSE 'Contrôle freinage'
  END,
  'Tâche générée automatiquement pour les tests',
  CASE 
    WHEN wo.id % 3 = 0 THEN 'preventive'
    WHEN wo.id % 3 = 1 THEN 'requested'
    ELSE 'suggested'
  END,
  CASE 
    WHEN wo.id % 4 = 0 THEN 'high'
    WHEN wo.id % 4 = 1 THEN 'medium'
    WHEN wo.id % 4 = 2 THEN 'low'
    ELSE 'urgent'
  END
FROM work_orders wo
WHERE wo.id <= 5
  AND NOT EXISTS (
    SELECT 1 FROM work_order_tasks wot WHERE wot.work_order_id = wo.id
  );

-- ===============================================
-- 10. VÉRIFICATIONS FINALES
-- ===============================================

-- Vérifier que les contraintes sont bien en place
SELECT 
  TABLE_NAME,
  CONSTRAINT_NAME,
  CONSTRAINT_TYPE
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
WHERE TABLE_SCHEMA = DATABASE() 
  AND TABLE_NAME IN ('work_order_tasks', 'interventions', 'intervention_notes', 'intervention_media')
ORDER BY TABLE_NAME, CONSTRAINT_TYPE;

-- Statistiques des nouvelles tables
SELECT 
  'work_order_tasks' as table_name,
  COUNT(*) as row_count
FROM work_order_tasks
UNION ALL
SELECT 
  'interventions' as table_name,
  COUNT(*) as row_count
FROM interventions
UNION ALL
SELECT 
  'intervention_notes' as table_name,
  COUNT(*) as row_count
FROM intervention_notes
UNION ALL
SELECT 
  'intervention_media' as table_name,
  COUNT(*) as row_count
FROM intervention_media;

-- Message de confirmation
SELECT 'Sprint 2 Migration Completed Successfully - Interventions & Work Orders Tasks' as status;
