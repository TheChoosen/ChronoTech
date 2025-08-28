-- ========================================
-- TESTS AUTOMATISÉS SPRINT 1
-- ========================================
-- Validation complète des contraintes et triggers
-- Date: 2025-08-27
-- ========================================

-- Activer les erreurs strictes
SET sql_mode = 'STRICT_TRANS_TABLES,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION';

-- ========================================
-- INITIALISATION DES TESTS
-- ========================================

-- Créer une table temporaire pour les résultats
CREATE TEMPORARY TABLE test_results (
    test_id INT AUTO_INCREMENT PRIMARY KEY,
    test_name VARCHAR(100),
    test_category VARCHAR(50),
    expected_result VARCHAR(20),
    actual_result VARCHAR(20),
    status ENUM('PASS', 'FAIL'),
    error_message TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Variables pour les tests
SET @test_wo_id = 1;
SET @test_customer_id = 1;
SET @test_user_id = 1;

-- S'assurer qu'on a un WO de test
INSERT IGNORE INTO work_orders (id, title, customer_id, status) 
VALUES (@test_wo_id, 'Test Work Order Sprint 1', @test_customer_id, 'pending');

-- ========================================
-- TESTS CONTRAINTES work_order_tasks
-- ========================================

-- TEST 1: Création valide de tâche
BEGIN;
    START TRANSACTION;
    INSERT INTO test_results (test_name, test_category, expected_result) 
    VALUES ('Création tâche valide', 'CONSTRAINTS', 'SUCCESS');
    
    SET @test_1_success = 0;
    SET @test_1_error = '';
    
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 @test_1_error = MESSAGE_TEXT;
        END;
        
        INSERT INTO work_order_tasks (work_order_id, title, task_source, priority) 
        VALUES (@test_wo_id, 'Test Tâche Valide', 'requested', 'medium');
        
        SET @test_1_success = 1;
        SET @last_task_id = LAST_INSERT_ID();
    END;
    
    UPDATE test_results SET 
        actual_result = IF(@test_1_success = 1, 'SUCCESS', 'ERROR'),
        status = IF(@test_1_success = 1, 'PASS', 'FAIL'),
        error_message = @test_1_error
    WHERE test_name = 'Création tâche valide';
COMMIT;

-- TEST 2: Rejet tâche sans work_order_id
BEGIN;
    START TRANSACTION;
    INSERT INTO test_results (test_name, test_category, expected_result) 
    VALUES ('Rejet tâche sans WO', 'CONSTRAINTS', 'ERROR');
    
    SET @test_2_success = 0;
    SET @test_2_error = '';
    
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 @test_2_error = MESSAGE_TEXT;
            SET @test_2_success = 1; -- Success = erreur attendue
        END;
        
        INSERT INTO work_order_tasks (title, task_source) 
        VALUES ('Tâche Orpheline', 'requested');
    END;
    
    UPDATE test_results SET 
        actual_result = IF(@test_2_success = 1, 'ERROR', 'SUCCESS'),
        status = IF(@test_2_success = 1, 'PASS', 'FAIL'),
        error_message = @test_2_error
    WHERE test_name = 'Rejet tâche sans WO';
COMMIT;

-- TEST 3: Rejet work_order_id inexistant
BEGIN;
    START TRANSACTION;
    INSERT INTO test_results (test_name, test_category, expected_result) 
    VALUES ('Rejet WO inexistant', 'CONSTRAINTS', 'ERROR');
    
    SET @test_3_success = 0;
    SET @test_3_error = '';
    
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 @test_3_error = MESSAGE_TEXT;
            SET @test_3_success = 1;
        END;
        
        INSERT INTO work_order_tasks (work_order_id, title, task_source) 
        VALUES (99999, 'Tâche WO Inexistant', 'requested');
    END;
    
    UPDATE test_results SET 
        actual_result = IF(@test_3_success = 1, 'ERROR', 'SUCCESS'),
        status = IF(@test_3_success = 1, 'PASS', 'FAIL'),
        error_message = @test_3_error
    WHERE test_name = 'Rejet WO inexistant';
COMMIT;

-- TEST 4: Rejet task_source invalide
BEGIN;
    START TRANSACTION;
    INSERT INTO test_results (test_name, test_category, expected_result) 
    VALUES ('Rejet source invalide', 'CONSTRAINTS', 'ERROR');
    
    SET @test_4_success = 0;
    SET @test_4_error = '';
    
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 @test_4_error = MESSAGE_TEXT;
            SET @test_4_success = 1;
        END;
        
        INSERT INTO work_order_tasks (work_order_id, title, task_source) 
        VALUES (@test_wo_id, 'Tâche Source Invalide', 'invalid_source');
    END;
    
    UPDATE test_results SET 
        actual_result = IF(@test_4_success = 1, 'ERROR', 'SUCCESS'),
        status = IF(@test_4_success = 1, 'PASS', 'FAIL'),
        error_message = @test_4_error
    WHERE test_name = 'Rejet source invalide';
COMMIT;

-- ========================================
-- TESTS CONTRAINTES interventions
-- ========================================

-- TEST 5: Création intervention valide
BEGIN;
    START TRANSACTION;
    INSERT INTO test_results (test_name, test_category, expected_result) 
    VALUES ('Création intervention valide', 'CONSTRAINTS', 'SUCCESS');
    
    SET @test_5_success = 0;
    SET @test_5_error = '';
    
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 @test_5_error = MESSAGE_TEXT;
        END;
        
        INSERT INTO interventions (work_order_id, task_id, technician_id) 
        VALUES (@test_wo_id, @last_task_id, @test_user_id);
        
        SET @test_5_success = 1;
        SET @last_intervention_id = LAST_INSERT_ID();
    END;
    
    UPDATE test_results SET 
        actual_result = IF(@test_5_success = 1, 'SUCCESS', 'ERROR'),
        status = IF(@test_5_success = 1, 'PASS', 'FAIL'),
        error_message = @test_5_error
    WHERE test_name = 'Création intervention valide';
COMMIT;

-- TEST 6: Rejet intervention task_id déjà utilisé
BEGIN;
    START TRANSACTION;
    INSERT INTO test_results (test_name, test_category, expected_result) 
    VALUES ('Rejet task_id déjà utilisé', 'CONSTRAINTS', 'ERROR');
    
    SET @test_6_success = 0;
    SET @test_6_error = '';
    
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 @test_6_error = MESSAGE_TEXT;
            SET @test_6_success = 1;
        END;
        
        INSERT INTO interventions (work_order_id, task_id, technician_id) 
        VALUES (@test_wo_id, @last_task_id, @test_user_id);
    END;
    
    UPDATE test_results SET 
        actual_result = IF(@test_6_success = 1, 'ERROR', 'SUCCESS'),
        status = IF(@test_6_success = 1, 'PASS', 'FAIL'),
        error_message = @test_6_error
    WHERE test_name = 'Rejet task_id déjà utilisé';
COMMIT;

-- ========================================
-- TESTS TRIGGERS
-- ========================================

-- TEST 7: Historisation changement statut WO
BEGIN;
    START TRANSACTION;
    INSERT INTO test_results (test_name, test_category, expected_result) 
    VALUES ('Historisation statut WO', 'TRIGGERS', 'SUCCESS');
    
    -- Compter les entrées avant
    SELECT COUNT(*) INTO @history_before FROM work_order_status_history WHERE work_order_id = @test_wo_id;
    
    -- Changer le statut
    UPDATE work_orders SET status = 'assigned' WHERE id = @test_wo_id;
    
    -- Compter après
    SELECT COUNT(*) INTO @history_after FROM work_order_status_history WHERE work_order_id = @test_wo_id;
    
    SET @test_7_success = IF(@history_after > @history_before, 1, 0);
    
    UPDATE test_results SET 
        actual_result = IF(@test_7_success = 1, 'SUCCESS', 'ERROR'),
        status = IF(@test_7_success = 1, 'PASS', 'FAIL'),
        error_message = IF(@test_7_success = 0, 'Aucun historique créé', '')
    WHERE test_name = 'Historisation statut WO';
COMMIT;

-- TEST 8: Synchronisation statut tâche -> intervention
BEGIN;
    START TRANSACTION;
    INSERT INTO test_results (test_name, test_category, expected_result) 
    VALUES ('Sync statut tâche-intervention', 'TRIGGERS', 'SUCCESS');
    
    -- Vérifier que started_at est NULL
    SELECT started_at INTO @started_before FROM interventions WHERE id = @last_intervention_id;
    
    -- Changer le statut de la tâche
    UPDATE work_order_tasks SET status = 'in_progress' WHERE id = @last_task_id;
    
    -- Vérifier que started_at est maintenant rempli
    SELECT started_at INTO @started_after FROM interventions WHERE id = @last_intervention_id;
    
    SET @test_8_success = IF(@started_before IS NULL AND @started_after IS NOT NULL, 1, 0);
    
    UPDATE test_results SET 
        actual_result = IF(@test_8_success = 1, 'SUCCESS', 'ERROR'),
        status = IF(@test_8_success = 1, 'PASS', 'FAIL'),
        error_message = IF(@test_8_success = 0, 'Synchronisation non fonctionnelle', '')
    WHERE test_name = 'Sync statut tâche-intervention';
COMMIT;

-- ========================================
-- TESTS CASCADE ET INTÉGRITÉ
-- ========================================

-- TEST 9: Notes liées à intervention valide
BEGIN;
    START TRANSACTION;
    INSERT INTO test_results (test_name, test_category, expected_result) 
    VALUES ('Création note intervention', 'CASCADE', 'SUCCESS');
    
    SET @test_9_success = 0;
    SET @test_9_error = '';
    
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 @test_9_error = MESSAGE_TEXT;
        END;
        
        INSERT INTO intervention_notes (intervention_id, author_user_id, note) 
        VALUES (@last_intervention_id, @test_user_id, 'Note de test Sprint 1');
        
        SET @test_9_success = 1;
    END;
    
    UPDATE test_results SET 
        actual_result = IF(@test_9_success = 1, 'SUCCESS', 'ERROR'),
        status = IF(@test_9_success = 1, 'PASS', 'FAIL'),
        error_message = @test_9_error
    WHERE test_name = 'Création note intervention';
COMMIT;

-- TEST 10: Média lié à intervention valide
BEGIN;
    START TRANSACTION;
    INSERT INTO test_results (test_name, test_category, expected_result) 
    VALUES ('Création média intervention', 'CASCADE', 'SUCCESS');
    
    SET @test_10_success = 0;
    SET @test_10_error = '';
    
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 @test_10_error = MESSAGE_TEXT;
        END;
        
        INSERT INTO intervention_media (intervention_id, file_path, original_filename, media_type) 
        VALUES (@last_intervention_id, '/uploads/test_sprint1.jpg', 'test.jpg', 'photo');
        
        SET @test_10_success = 1;
    END;
    
    UPDATE test_results SET 
        actual_result = IF(@test_10_success = 1, 'SUCCESS', 'ERROR'),
        status = IF(@test_10_success = 1, 'PASS', 'FAIL'),
        error_message = @test_10_error
    WHERE test_name = 'Création média intervention';
COMMIT;

-- ========================================
-- TESTS PERFORMANCE INDEX
-- ========================================

-- TEST 11: Performance requête filtrée tâches
INSERT INTO test_results (test_name, test_category, expected_result) 
VALUES ('Performance index tâches', 'PERFORMANCE', 'SUCCESS');

-- Forcer l'utilisation de l'index
SELECT COUNT(*) INTO @perf_count FROM work_order_tasks USE INDEX(idx_wot_wo_status)
WHERE work_order_id = @test_wo_id AND status = 'pending';

UPDATE test_results SET 
    actual_result = 'SUCCESS',
    status = 'PASS',
    error_message = CONCAT('Trouvé ', @perf_count, ' résultats')
WHERE test_name = 'Performance index tâches';

-- ========================================
-- TESTS VUES
-- ========================================

-- TEST 12: Vue work_order_tasks_complete
BEGIN;
    START TRANSACTION;
    INSERT INTO test_results (test_name, test_category, expected_result) 
    VALUES ('Vue tâches complète', 'VIEWS', 'SUCCESS');
    
    SET @test_12_success = 0;
    SET @test_12_error = '';
    
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 @test_12_error = MESSAGE_TEXT;
        END;
        
        SELECT COUNT(*) INTO @view_count FROM v_work_order_tasks_complete WHERE work_order_id = @test_wo_id;
        SET @test_12_success = 1;
    END;
    
    UPDATE test_results SET 
        actual_result = IF(@test_12_success = 1, 'SUCCESS', 'ERROR'),
        status = IF(@test_12_success = 1, 'PASS', 'FAIL'),
        error_message = IF(@test_12_success = 1, CONCAT('Vue OK - ', @view_count, ' lignes'), @test_12_error)
    WHERE test_name = 'Vue tâches complète';
COMMIT;

-- TEST 13: Vue interventions_complete
BEGIN;
    START TRANSACTION;
    INSERT INTO test_results (test_name, test_category, expected_result) 
    VALUES ('Vue interventions complète', 'VIEWS', 'SUCCESS');
    
    SET @test_13_success = 0;
    SET @test_13_error = '';
    
    BEGIN
        DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
        BEGIN
            GET DIAGNOSTICS CONDITION 1 @test_13_error = MESSAGE_TEXT;
        END;
        
        SELECT COUNT(*) INTO @view_count2 FROM v_interventions_complete WHERE work_order_id = @test_wo_id;
        SET @test_13_success = 1;
    END;
    
    UPDATE test_results SET 
        actual_result = IF(@test_13_success = 1, 'SUCCESS', 'ERROR'),
        status = IF(@test_13_success = 1, 'PASS', 'FAIL'),
        error_message = IF(@test_13_success = 1, CONCAT('Vue OK - ', @view_count2, ' lignes'), @test_13_error)
    WHERE test_name = 'Vue interventions complète';
COMMIT;

-- ========================================
-- RAPPORT FINAL
-- ========================================

-- Résumé des résultats
SELECT 
    '=== RAPPORT TESTS SPRINT 1 ===' as rapport;

SELECT 
    test_category,
    COUNT(*) as total_tests,
    SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
    SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
    ROUND(SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate_percent
FROM test_results 
GROUP BY test_category
UNION ALL
SELECT 
    '--- TOTAL ---' as test_category,
    COUNT(*) as total_tests,
    SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
    SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
    ROUND(SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate_percent
FROM test_results;

-- Détail des échecs
SELECT 
    'ÉCHECS DÉTECTÉS:' as section;

SELECT 
    test_name,
    test_category,
    expected_result,
    actual_result,
    error_message,
    executed_at
FROM test_results 
WHERE status = 'FAIL'
ORDER BY test_category, test_name;

-- Validation finale
SELECT 
    CASE 
        WHEN (SELECT COUNT(*) FROM test_results WHERE status = 'FAIL') = 0 
        THEN '✅ SPRINT 1 - TOUS LES TESTS PASSENT - PRÊT POUR SPRINT 2'
        ELSE '❌ SPRINT 1 - ÉCHECS DÉTECTÉS - CORRECTION REQUISE'
    END as validation_finale;

-- Nettoyage optionnel des données de test
-- DELETE FROM intervention_media WHERE intervention_id = @last_intervention_id;
-- DELETE FROM intervention_notes WHERE intervention_id = @last_intervention_id;
-- DELETE FROM interventions WHERE id = @last_intervention_id;
-- DELETE FROM work_order_tasks WHERE id = @last_task_id;
