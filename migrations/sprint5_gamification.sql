-- Migration Sprint 5 - Gamification et engagement
-- Tables pour badges, scores, classements et feedback clients

-- Table pour les types de badges disponibles
CREATE TABLE IF NOT EXISTS badge_definitions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    icon VARCHAR(100) NOT NULL,
    color VARCHAR(7) DEFAULT '#28a745',
    category ENUM('performance', 'quality', 'efficiency', 'teamwork', 'milestone') NOT NULL,
    criteria_type ENUM('work_orders_count', 'satisfaction_avg', 'response_time', 'completion_rate', 'special_achievement') NOT NULL,
    criteria_value INT NOT NULL,
    criteria_period ENUM('all_time', 'monthly', 'weekly', 'daily') DEFAULT 'all_time',
    points_awarded INT DEFAULT 10,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_criteria (criteria_type),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour les badges obtenus par les utilisateurs
CREATE TABLE IF NOT EXISTS user_badges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    badge_id INT NOT NULL,
    earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    earned_for_period VARCHAR(50) NULL, -- Ex: "2025-01-W04" pour semaine 4
    progress_value INT NOT NULL, -- Valeur qui a déclenché le badge
    work_order_id INT NULL, -- Work order spécifique qui a déclenché (si applicable)
    is_featured BOOLEAN DEFAULT FALSE, -- Badge mis en avant
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (badge_id) REFERENCES badge_definitions(id) ON DELETE CASCADE,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE SET NULL,
    UNIQUE KEY unique_user_badge_period (user_id, badge_id, earned_for_period),
    INDEX idx_user (user_id),
    INDEX idx_badge (badge_id),
    INDEX idx_earned_at (earned_at),
    INDEX idx_featured (is_featured)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour les scores et points des utilisateurs
CREATE TABLE IF NOT EXISTS user_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    score_type ENUM('daily', 'weekly', 'monthly', 'total') NOT NULL,
    period_key VARCHAR(20) NOT NULL, -- "2025-01-27", "2025-W04", "2025-01", "total"
    points INT DEFAULT 0,
    work_orders_completed INT DEFAULT 0,
    avg_completion_time DECIMAL(6,2) DEFAULT 0.00, -- en heures
    avg_customer_satisfaction DECIMAL(3,2) DEFAULT 0.00, -- sur 5
    quality_score DECIMAL(5,2) DEFAULT 0.00, -- score qualité calculé
    efficiency_bonus INT DEFAULT 0,
    teamwork_bonus INT DEFAULT 0,
    calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_score_period (user_id, score_type, period_key),
    INDEX idx_user (user_id),
    INDEX idx_type_period (score_type, period_key),
    INDEX idx_points (points DESC),
    INDEX idx_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour les classements
CREATE TABLE IF NOT EXISTS leaderboards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    leaderboard_type ENUM('individual_weekly', 'individual_monthly', 'team_weekly', 'team_monthly', 'department_weekly', 'department_monthly') NOT NULL,
    period_key VARCHAR(20) NOT NULL,
    entity_type ENUM('user', 'team', 'department') NOT NULL,
    entity_id INT NOT NULL,
    entity_name VARCHAR(255) NOT NULL,
    rank_position INT NOT NULL,
    total_points INT NOT NULL,
    work_orders_completed INT DEFAULT 0,
    avg_satisfaction DECIMAL(3,2) DEFAULT 0.00,
    badges_earned INT DEFAULT 0,
    improvement_from_last DECIMAL(5,2) DEFAULT 0.00, -- % d'amélioration
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type_period (leaderboard_type, period_key),
    INDEX idx_rank (rank_position),
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_points (total_points DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour le feedback client post-intervention
CREATE TABLE IF NOT EXISTS client_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_id INT NOT NULL,
    customer_id INT NOT NULL,
    technician_id INT NOT NULL,
    feedback_token VARCHAR(255) NOT NULL UNIQUE,
    
    -- Scores de satisfaction (1-5)
    overall_satisfaction INT CHECK (overall_satisfaction BETWEEN 1 AND 5),
    quality_work INT CHECK (quality_work BETWEEN 1 AND 5),
    technician_professionalism INT CHECK (technician_professionalism BETWEEN 1 AND 5),
    response_time_satisfaction INT CHECK (response_time_satisfaction BETWEEN 1 AND 5),
    communication_quality INT CHECK (communication_quality BETWEEN 1 AND 5),
    
    -- NPS Score (0-10)
    nps_score INT CHECK (nps_score BETWEEN 0 AND 10),
    
    -- Commentaires
    positive_feedback TEXT NULL,
    improvement_feedback TEXT NULL,
    additional_comments TEXT NULL,
    
    -- Données de suivi
    would_recommend BOOLEAN NULL,
    would_use_again BOOLEAN NULL,
    
    -- Métadonnées
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    response_time_seconds INT DEFAULT 0, -- Temps pris pour répondre
    
    -- Gestion token
    token_sent_at DATETIME NULL,
    expires_at DATETIME NULL,
    is_expired BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE CASCADE,
    
    INDEX idx_work_order (work_order_id),
    INDEX idx_customer (customer_id),
    INDEX idx_technician (technician_id),
    INDEX idx_token (feedback_token),
    INDEX idx_submitted (submitted_at),
    INDEX idx_nps (nps_score),
    INDEX idx_satisfaction (overall_satisfaction)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour les notifications de gamification
CREATE TABLE IF NOT EXISTS gamification_notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    notification_type ENUM('badge_earned', 'rank_up', 'score_milestone', 'feedback_received') NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSON NULL, -- Données contextuelles
    is_read BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_type (notification_type),
    INDEX idx_read (is_read),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insérer les badges de base
INSERT INTO badge_definitions (name, description, icon, color, category, criteria_type, criteria_value, points_awarded) VALUES
('Rookie', 'Premier work order terminé', 'fa-star', '#17a2b8', 'milestone', 'work_orders_count', 1, 5),
('Débutant Motivé', '10 work orders terminés', 'fa-trophy', '#28a745', 'performance', 'work_orders_count', 10, 10),
('Technicien Confirmé', '50 work orders terminés à temps', 'fa-medal', '#ffc107', 'performance', 'work_orders_count', 50, 25),
('Expert', '100 work orders terminés', 'fa-crown', '#fd7e14', 'performance', 'work_orders_count', 100, 50),
('Maître Technicien', '500 work orders terminés', 'fa-gem', '#6f42c1', 'performance', 'work_orders_count', 500, 100),

('Client Satisfait', 'Moyenne satisfaction > 4.5/5', 'fa-smile', '#20c997', 'quality', 'satisfaction_avg', 45, 20),
('Excellence Client', 'Moyenne satisfaction > 4.8/5', 'fa-heart', '#e83e8c', 'quality', 'satisfaction_avg', 48, 40),

('Rapide comme l\'Éclair', 'Temps moyen < 2 heures', 'fa-bolt', '#007bff', 'efficiency', 'response_time', 120, 15),
('Efficacité Maximum', 'Temps moyen < 1 heure', 'fa-rocket', '#dc3545', 'efficiency', 'response_time', 60, 30),

('Esprit d\'Équipe', '10 work orders en collaboration', 'fa-handshake', '#6c757d', 'teamwork', 'work_orders_count', 10, 15),
('Leader', '25 work orders supervisés', 'fa-users', '#495057', 'teamwork', 'work_orders_count', 25, 25),

-- Badges hebdomadaires
('Champion de la Semaine', 'Plus de work orders de la semaine', 'fa-calendar-week', '#28a745', 'performance', 'work_orders_count', 20, 30),
('MVP Mensuel', 'Meilleur technicien du mois', 'fa-calendar-alt', '#007bff', 'performance', 'work_orders_count', 80, 75);

-- Vue pour les statistiques de gamification
CREATE OR REPLACE VIEW gamification_stats AS
SELECT 
    u.id as user_id,
    u.name as user_name,
    u.department_id,
    COUNT(DISTINCT ub.id) as total_badges,
    COALESCE(us_total.points, 0) as total_points,
    COALESCE(us_weekly.points, 0) as weekly_points,
    COALESCE(us_monthly.points, 0) as monthly_points,
    COUNT(DISTINCT cf.id) as feedback_count,
    AVG(cf.overall_satisfaction) as avg_satisfaction,
    (
        SELECT rank_position 
        FROM leaderboards l 
        WHERE l.entity_type = 'user' 
        AND l.entity_id = u.id 
        AND l.leaderboard_type = 'individual_weekly'
        AND l.period_key = DATE_FORMAT(NOW(), '%Y-W%u')
        LIMIT 1
    ) as current_weekly_rank
FROM users u
LEFT JOIN user_badges ub ON u.id = ub.user_id
LEFT JOIN user_scores us_total ON u.id = us_total.user_id AND us_total.score_type = 'total'
LEFT JOIN user_scores us_weekly ON u.id = us_weekly.user_id AND us_weekly.score_type = 'weekly' 
    AND us_weekly.period_key = DATE_FORMAT(NOW(), '%Y-W%u')
LEFT JOIN user_scores us_monthly ON u.id = us_monthly.user_id AND us_monthly.score_type = 'monthly'
    AND us_monthly.period_key = DATE_FORMAT(NOW(), '%Y-%m')
LEFT JOIN client_feedback cf ON u.id = cf.technician_id AND cf.submitted_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
WHERE u.is_active = TRUE
GROUP BY u.id;

-- Procédure pour calculer les scores utilisateur
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS CalculateUserScores(IN target_user_id INT, IN score_period VARCHAR(20))
BEGIN
    DECLARE period_start DATE;
    DECLARE period_end DATE;
    DECLARE score_type_val VARCHAR(20);
    
    -- Déterminer les dates selon le type de période
    IF score_period = 'daily' THEN
        SET period_start = CURDATE();
        SET period_end = CURDATE();
        SET score_type_val = 'daily';
    ELSEIF score_period = 'weekly' THEN
        SET period_start = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY);
        SET period_end = DATE_ADD(period_start, INTERVAL 6 DAY);
        SET score_type_val = 'weekly';
    ELSEIF score_period = 'monthly' THEN
        SET period_start = DATE_FORMAT(CURDATE(), '%Y-%m-01');
        SET period_end = LAST_DAY(CURDATE());
        SET score_type_val = 'monthly';
    ELSE
        SET period_start = '1900-01-01';
        SET period_end = CURDATE();
        SET score_type_val = 'total';
    END IF;
    
    -- Calculer et insérer/mettre à jour le score
    INSERT INTO user_scores (
        user_id, score_type, period_key, points, work_orders_completed,
        avg_completion_time, avg_customer_satisfaction, quality_score
    )
    SELECT 
        target_user_id,
        score_type_val,
        CASE 
            WHEN score_type_val = 'daily' THEN DATE_FORMAT(CURDATE(), '%Y-%m-%d')
            WHEN score_type_val = 'weekly' THEN DATE_FORMAT(CURDATE(), '%Y-W%u')
            WHEN score_type_val = 'monthly' THEN DATE_FORMAT(CURDATE(), '%Y-%m')
            ELSE 'total'
        END,
        -- Points basés sur work orders + bonus satisfaction
        COUNT(wo.id) * 10 + IFNULL(AVG(cf.overall_satisfaction) * 10, 0),
        COUNT(wo.id),
        AVG(TIMESTAMPDIFF(HOUR, wo.created_at, wo.completed_at)),
        AVG(cf.overall_satisfaction),
        (COUNT(wo.id) * 10) + (AVG(cf.overall_satisfaction) * 20)
    FROM work_orders wo
    LEFT JOIN client_feedback cf ON wo.id = cf.work_order_id
    WHERE wo.assigned_to = target_user_id
    AND wo.status = 'completed'
    AND DATE(wo.completed_at) BETWEEN period_start AND period_end
    ON DUPLICATE KEY UPDATE
        points = VALUES(points),
        work_orders_completed = VALUES(work_orders_completed),
        avg_completion_time = VALUES(avg_completion_time),
        avg_customer_satisfaction = VALUES(avg_customer_satisfaction),
        quality_score = VALUES(quality_score),
        updated_at = CURRENT_TIMESTAMP;
END //
DELIMITER ;

-- Procédure pour vérifier et attribuer les nouveaux badges
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS CheckAndAwardBadges(IN target_user_id INT)
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE badge_id INT;
    DECLARE badge_criteria_type VARCHAR(50);
    DECLARE badge_criteria_value INT;
    DECLARE badge_name VARCHAR(255);
    DECLARE user_value INT DEFAULT 0;
    
    DECLARE badge_cursor CURSOR FOR
        SELECT bd.id, bd.name, bd.criteria_type, bd.criteria_value
        FROM badge_definitions bd
        WHERE bd.is_active = TRUE
        AND bd.id NOT IN (
            SELECT ub.badge_id 
            FROM user_badges ub 
            WHERE ub.user_id = target_user_id
        );
    
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    OPEN badge_cursor;
    
    read_loop: LOOP
        FETCH badge_cursor INTO badge_id, badge_name, badge_criteria_type, badge_criteria_value;
        IF done THEN
            LEAVE read_loop;
        END IF;
        
        -- Calculer la valeur actuelle de l'utilisateur selon le critère
        SET user_value = 0;
        
        IF badge_criteria_type = 'work_orders_count' THEN
            SELECT COUNT(*) INTO user_value
            FROM work_orders wo
            WHERE wo.assigned_to = target_user_id 
            AND wo.status = 'completed';
            
        ELSEIF badge_criteria_type = 'satisfaction_avg' THEN
            SELECT ROUND(AVG(cf.overall_satisfaction) * 10) INTO user_value
            FROM client_feedback cf
            WHERE cf.technician_id = target_user_id;
            
        ELSEIF badge_criteria_type = 'response_time' THEN
            SELECT AVG(TIMESTAMPDIFF(MINUTE, wo.created_at, wo.started_at)) INTO user_value
            FROM work_orders wo
            WHERE wo.assigned_to = target_user_id 
            AND wo.status = 'completed'
            AND wo.started_at IS NOT NULL;
        END IF;
        
        -- Attribuer le badge si critère atteint
        IF user_value >= badge_criteria_value THEN
            INSERT INTO user_badges (user_id, badge_id, progress_value, earned_for_period)
            VALUES (target_user_id, badge_id, user_value, DATE_FORMAT(NOW(), '%Y-W%u'));
            
            -- Créer une notification
            INSERT INTO gamification_notifications (user_id, notification_type, title, message, data)
            VALUES (
                target_user_id,
                'badge_earned',
                CONCAT('Nouveau badge: ', badge_name),
                CONCAT('Félicitations ! Vous avez obtenu le badge "', badge_name, '"'),
                JSON_OBJECT('badge_id', badge_id, 'user_value', user_value)
            );
        END IF;
        
    END LOOP;
    
    CLOSE badge_cursor;
END //
DELIMITER ;

-- Données de test
INSERT IGNORE INTO client_feedback 
(work_order_id, customer_id, technician_id, feedback_token, overall_satisfaction, quality_work, 
 technician_professionalism, response_time_satisfaction, communication_quality, nps_score,
 positive_feedback, would_recommend, would_use_again, submitted_at, expires_at) VALUES
(1, 1, 1, 'feedback_token_123', 5, 5, 5, 4, 5, 9, 
 'Excellent travail, très professionnel !', TRUE, TRUE, NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY)),
(2, 2, 1, 'feedback_token_456', 4, 4, 5, 3, 4, 7,
 'Bon travail dans l\'ensemble', TRUE, TRUE, NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY)),
(3, 1, 2, 'feedback_token_789', 5, 5, 5, 5, 5, 10,
 'Service parfait, je recommande !', TRUE, TRUE, NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY));

SELECT 'Sprint 5 - Tables de gamification créées avec succès' as result;

COMMIT;
