-- Sprint 7-8: Customer 360 Advanced & Analytics
-- Migration: Tables avancées pour segmentation, scoring et analyse

-- Table pour les scores RFM et profils clients
CREATE TABLE IF NOT EXISTS customer_analytics (
    customer_id INT NOT NULL PRIMARY KEY,
    recency_score INT DEFAULT 0,          -- 1-5 (plus récent = plus élevé)
    frequency_score INT DEFAULT 0,        -- 1-5 (plus fréquent = plus élevé) 
    monetary_score INT DEFAULT 0,         -- 1-5 (plus de dépenses = plus élevé)
    rfm_segment VARCHAR(20),              -- 'Champions', 'Loyal', 'At Risk', etc.
    ltv_12m DECIMAL(10,2) DEFAULT 0.00,   -- Lifetime Value 12 mois
    ltv_predicted DECIMAL(10,2) DEFAULT 0.00, -- LTV prédictive
    churn_risk_score DECIMAL(5,4) DEFAULT 0.0000, -- 0.0000 à 1.0000
    last_purchase_date DATE,
    total_orders INT DEFAULT 0,
    avg_order_value DECIMAL(10,2) DEFAULT 0.00,
    days_since_last_order INT DEFAULT 0,
    calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX (rfm_segment),
    INDEX (churn_risk_score),
    INDEX (ltv_12m)
);

-- Enrichissement table customers avec champs manquants
ALTER TABLE customers 
ADD COLUMN language_code VARCHAR(10) DEFAULT 'fr-CA',
ADD COLUMN timezone VARCHAR(50) DEFAULT 'America/Montreal',
ADD COLUMN privacy_level ENUM('normal', 'restricted', 'confidential') DEFAULT 'normal',
ADD COLUMN tax_exempt BOOLEAN DEFAULT FALSE,
ADD COLUMN merged_into INT NULL,
ADD COLUMN duplicate_confidence DECIMAL(3,2) DEFAULT 0.00,
ADD COLUMN last_activity_date DATE,
ADD COLUMN source_channel VARCHAR(50),
ADD COLUMN acquisition_cost DECIMAL(10,2) DEFAULT 0.00;

-- Table pour la détection et gestion des doublons
CREATE TABLE IF NOT EXISTS customer_duplicates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id_primary INT NOT NULL,
    customer_id_duplicate INT NOT NULL,
    confidence_score DECIMAL(3,2) NOT NULL, -- 0.00 à 1.00
    match_criteria JSON,                     -- {"email": true, "phone": true, "address_similarity": 0.85}
    status ENUM('detected', 'reviewed', 'merged', 'ignored') DEFAULT 'detected',
    reviewed_by INT,
    reviewed_at DATETIME,
    merged_at DATETIME,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id_primary) REFERENCES customers(id),
    FOREIGN KEY (customer_id_duplicate) REFERENCES customers(id),
    FOREIGN KEY (reviewed_by) REFERENCES users(id),
    INDEX (confidence_score),
    INDEX (status),
    UNIQUE KEY unique_duplicate_pair (customer_id_primary, customer_id_duplicate)
);

-- Table pour les routes et planification logistique
CREATE TABLE IF NOT EXISTS delivery_routes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    route_name VARCHAR(255) NOT NULL,
    route_date DATE NOT NULL,
    technician_id INT,
    vehicle_id INT,
    start_address TEXT,
    start_latitude DECIMAL(10,8),
    start_longitude DECIMAL(11,8),
    end_address TEXT,
    end_latitude DECIMAL(10,8),
    end_longitude DECIMAL(11,8),
    estimated_duration INT,              -- en minutes
    estimated_distance DECIMAL(8,2),     -- en kilomètres
    actual_duration INT,
    actual_distance DECIMAL(8,2),
    total_stops INT DEFAULT 0,
    status ENUM('planned', 'in_progress', 'completed', 'cancelled') DEFAULT 'planned',
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX (route_date, status),
    INDEX (technician_id, route_date)
);

-- Table pour les arrêts de route (interventions/livraisons)
CREATE TABLE IF NOT EXISTS route_stops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    route_id INT NOT NULL,
    customer_id INT NOT NULL,
    stop_order INT NOT NULL,
    address_id INT,
    stop_type ENUM('service', 'delivery', 'pickup', 'consultation') NOT NULL,
    reference_id INT,                    -- ID du bon de travail, livraison, etc.
    reference_table VARCHAR(50),         -- 'work_orders', 'deliveries', etc.
    estimated_arrival TIME,
    estimated_duration INT,              -- en minutes
    actual_arrival DATETIME,
    actual_departure DATETIME,
    status ENUM('pending', 'arrived', 'in_progress', 'completed', 'failed', 'cancelled') DEFAULT 'pending',
    notes TEXT,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (route_id) REFERENCES delivery_routes(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (address_id) REFERENCES customer_addresses(id),
    INDEX (route_id, stop_order),
    INDEX (customer_id),
    INDEX (status)
);

-- Table pour les recommandations et scoring personnalisé
CREATE TABLE IF NOT EXISTS customer_recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    recommendation_type ENUM('product', 'service', 'upsell', 'cross_sell', 'retention') NOT NULL,
    item_type VARCHAR(50),               -- 'product', 'service_package', etc.
    item_id INT,
    score DECIMAL(5,4) NOT NULL,         -- Score de recommandation 0.0000 à 1.0000
    reasoning JSON,                      -- Raisons de la recommandation
    is_active BOOLEAN DEFAULT TRUE,
    presented_at DATETIME,
    clicked_at DATETIME,
    converted_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX (customer_id, is_active),
    INDEX (recommendation_type, score DESC),
    INDEX (expires_at)
);

-- Table pour les KPI et métriques par client
CREATE TABLE IF NOT EXISTS customer_kpis (
    customer_id INT NOT NULL PRIMARY KEY,
    total_revenue_ytd DECIMAL(12,2) DEFAULT 0.00,
    total_revenue_12m DECIMAL(12,2) DEFAULT 0.00,
    total_revenue_lifetime DECIMAL(12,2) DEFAULT 0.00,
    avg_monthly_revenue DECIMAL(10,2) DEFAULT 0.00,
    total_orders_ytd INT DEFAULT 0,
    total_orders_12m INT DEFAULT 0,
    total_orders_lifetime INT DEFAULT 0,
    avg_order_value DECIMAL(10,2) DEFAULT 0.00,
    days_since_first_order INT DEFAULT 0,
    days_since_last_order INT DEFAULT 0,
    customer_tenure_days INT DEFAULT 0,
    profit_margin_avg DECIMAL(5,2) DEFAULT 0.00,
    payment_delay_avg DECIMAL(5,2) DEFAULT 0.00,    -- Jours de retard moyen
    satisfaction_score DECIMAL(3,2),                 -- Score NPS ou CSAT
    complaint_count_12m INT DEFAULT 0,
    referral_count INT DEFAULT 0,
    acquisition_cost DECIMAL(10,2) DEFAULT 0.00,
    calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Table pour les compatibilités véhicule-accessoire
CREATE TABLE IF NOT EXISTS vehicle_compatibility (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_make VARCHAR(100) NOT NULL,
    vehicle_model VARCHAR(100) NOT NULL,
    year_from INT,
    year_to INT,
    product_id INT NOT NULL,
    compatibility_type ENUM('direct', 'with_adapter', 'custom_install') DEFAULT 'direct',
    installation_time_minutes INT,
    installation_difficulty ENUM('easy', 'medium', 'hard', 'professional_only') DEFAULT 'medium',
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX (vehicle_make, vehicle_model),
    INDEX (product_id)
);

-- Table pour les performances technicien par compétence
CREATE TABLE IF NOT EXISTS technician_competencies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    technician_id INT NOT NULL,
    competency_type VARCHAR(100) NOT NULL,           -- 'engine_repair', 'electronics', 'bodywork', etc.
    skill_level ENUM('beginner', 'intermediate', 'advanced', 'expert') NOT NULL,
    certification_date DATE,
    expiry_date DATE,
    certified_by VARCHAR(255),
    hours_practiced INT DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 0.00,         -- Pourcentage de succès
    avg_completion_time INT DEFAULT 0,               -- Minutes moyennes pour ce type d'intervention
    customer_rating_avg DECIMAL(3,2) DEFAULT 0.00,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX (technician_id, competency_type),
    INDEX (skill_level),
    UNIQUE KEY unique_tech_competency (technician_id, competency_type)
);

-- Table pour les récompenses et programme de fidélité
CREATE TABLE IF NOT EXISTS loyalty_rewards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    reward_type ENUM('points', 'discount', 'free_service', 'upgrade', 'gift') NOT NULL,
    points_earned INT DEFAULT 0,
    points_redeemed INT DEFAULT 0,
    discount_percentage DECIMAL(5,2),
    discount_amount DECIMAL(10,2),
    reward_description TEXT,
    reference_order_id INT,
    earned_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    redeemed_date DATETIME,
    expires_at DATETIME,
    status ENUM('earned', 'redeemed', 'expired', 'cancelled') DEFAULT 'earned',
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX (customer_id, status),
    INDEX (earned_date),
    INDEX (expires_at)
);

-- Vue pour le dashboard Client 360 avancé
CREATE OR REPLACE VIEW customer_360_summary AS
SELECT 
    c.id,
    c.name,
    c.company,
    c.email,
    c.phone,
    c.language_code,
    c.timezone,
    c.privacy_level,
    c.created_at,
    c.last_activity_date,
    -- Analytics
    ca.rfm_segment,
    ca.ltv_12m,
    ca.churn_risk_score,
    ca.last_purchase_date,
    -- KPIs
    ck.total_revenue_lifetime,
    ck.total_orders_lifetime,
    ck.avg_order_value,
    ck.customer_tenure_days,
    ck.satisfaction_score,
    -- Compteurs
    (SELECT COUNT(*) FROM vehicles WHERE customer_id = c.id) as vehicle_count,
    (SELECT COUNT(*) FROM customer_documents WHERE customer_id = c.id) as document_count,
    (SELECT COUNT(*) FROM work_orders wo JOIN vehicles v ON wo.vehicle_id = v.id WHERE v.customer_id = c.id AND wo.status = 'open') as open_work_orders,
    (SELECT SUM(amount) FROM invoices WHERE customer_id = c.id AND status = 'open') as outstanding_amount,
    -- Dernière activité
    (SELECT MAX(created_at) FROM customer_activity WHERE customer_id = c.id) as last_activity_datetime
FROM customers c
LEFT JOIN customer_analytics ca ON c.id = ca.customer_id
LEFT JOIN customer_kpis ck ON c.id = ck.customer_id
WHERE c.is_active = TRUE;

-- Ajout d'index pour les performances
CREATE INDEX idx_customer_type_date ON customer_activity (customer_id, activity_type, created_at);
CREATE INDEX idx_customer_type ON customer_documents (customer_id, document_type);
CREATE INDEX idx_customer_geo ON customer_addresses (customer_id, latitude, longitude);

-- Procédure stockée pour calculer le score RFM
DELIMITER //
CREATE OR REPLACE PROCEDURE CalculateCustomerRFM(IN target_customer_id INT)
BEGIN
    DECLARE recency_days INT;
    DECLARE frequency_count INT;
    DECLARE monetary_total DECIMAL(10,2);
    DECLARE recency_score INT;
    DECLARE frequency_score INT;
    DECLARE monetary_score INT;
    DECLARE rfm_segment VARCHAR(20);
    
    -- Calcul Recency (jours depuis dernière commande)
    SELECT COALESCE(DATEDIFF(NOW(), MAX(order_date)), 9999)
    INTO recency_days
    FROM invoices 
    WHERE customer_id = target_customer_id AND status = 'paid';
    
    -- Calcul Frequency (nombre de commandes 12 derniers mois)
    SELECT COUNT(*)
    INTO frequency_count
    FROM invoices 
    WHERE customer_id = target_customer_id 
    AND status = 'paid' 
    AND order_date >= DATE_SUB(NOW(), INTERVAL 12 MONTH);
    
    -- Calcul Monetary (montant total 12 derniers mois)
    SELECT COALESCE(SUM(total_amount), 0)
    INTO monetary_total
    FROM invoices 
    WHERE customer_id = target_customer_id 
    AND status = 'paid' 
    AND order_date >= DATE_SUB(NOW(), INTERVAL 12 MONTH);
    
    -- Attribution des scores (1-5)
    SET recency_score = CASE 
        WHEN recency_days <= 30 THEN 5
        WHEN recency_days <= 60 THEN 4
        WHEN recency_days <= 90 THEN 3
        WHEN recency_days <= 180 THEN 2
        ELSE 1
    END;
    
    SET frequency_score = CASE 
        WHEN frequency_count >= 12 THEN 5
        WHEN frequency_count >= 6 THEN 4
        WHEN frequency_count >= 3 THEN 3
        WHEN frequency_count >= 1 THEN 2
        ELSE 1
    END;
    
    SET monetary_score = CASE 
        WHEN monetary_total >= 10000 THEN 5
        WHEN monetary_total >= 5000 THEN 4
        WHEN monetary_total >= 2000 THEN 3
        WHEN monetary_total >= 500 THEN 2
        ELSE 1
    END;
    
    -- Détermination du segment RFM
    SET rfm_segment = CASE 
        WHEN recency_score >= 4 AND frequency_score >= 4 AND monetary_score >= 4 THEN 'Champions'
        WHEN recency_score >= 3 AND frequency_score >= 3 AND monetary_score >= 3 THEN 'Loyal'
        WHEN recency_score >= 4 AND frequency_score <= 2 THEN 'New_Customer'
        WHEN recency_score <= 2 AND frequency_score >= 3 AND monetary_score >= 3 THEN 'At_Risk'
        WHEN recency_score <= 2 AND frequency_score <= 2 THEN 'Lost'
        WHEN recency_score >= 3 AND frequency_score <= 2 AND monetary_score <= 2 THEN 'Potential'
        ELSE 'Regular'
    END;
    
    -- Mise à jour ou insertion dans customer_analytics
    INSERT INTO customer_analytics (
        customer_id, recency_score, frequency_score, monetary_score, 
        rfm_segment, last_purchase_date, total_orders, 
        avg_order_value, days_since_last_order, calculated_at
    ) VALUES (
        target_customer_id, recency_score, frequency_score, monetary_score,
        rfm_segment, 
        (SELECT MAX(order_date) FROM invoices WHERE customer_id = target_customer_id AND status = 'paid'),
        frequency_count,
        CASE WHEN frequency_count > 0 THEN monetary_total / frequency_count ELSE 0 END,
        recency_days,
        NOW()
    ) ON DUPLICATE KEY UPDATE
        recency_score = VALUES(recency_score),
        frequency_score = VALUES(frequency_score),
        monetary_score = VALUES(monetary_score),
        rfm_segment = VALUES(rfm_segment),
        last_purchase_date = VALUES(last_purchase_date),
        total_orders = VALUES(total_orders),
        avg_order_value = VALUES(avg_order_value),
        days_since_last_order = VALUES(days_since_last_order),
        calculated_at = VALUES(calculated_at);
        
END//
DELIMITER ;

-- Triggers pour maintenir les KPI à jour
DELIMITER //
CREATE OR REPLACE TRIGGER update_customer_kpis_after_invoice
AFTER INSERT ON invoices
FOR EACH ROW
BEGIN
    IF NEW.status = 'paid' THEN
        INSERT INTO customer_kpis (customer_id)
        VALUES (NEW.customer_id)
        ON DUPLICATE KEY UPDATE customer_id = customer_id;
        
        CALL CalculateCustomerRFM(NEW.customer_id);
    END IF;
END//
DELIMITER ;

-- Fonction pour détecter les doublons potentiels
DELIMITER //
CREATE OR REPLACE PROCEDURE DetectCustomerDuplicates()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE customer_id_1 INT;
    DECLARE customer_id_2 INT;
    DECLARE email_1 VARCHAR(255);
    DECLARE phone_1 VARCHAR(20);
    DECLARE name_1 VARCHAR(255);
    DECLARE email_2 VARCHAR(255);
    DECLARE phone_2 VARCHAR(20);
    DECLARE name_2 VARCHAR(255);
    DECLARE confidence DECIMAL(3,2);
    DECLARE match_criteria JSON;
    
    DECLARE customer_cursor CURSOR FOR 
        SELECT c1.id, c1.email, c1.phone, c1.name,
               c2.id, c2.email, c2.phone, c2.name
        FROM customers c1
        JOIN customers c2 ON c1.id < c2.id
        WHERE c1.is_active = TRUE AND c2.is_active = TRUE
        AND (
            (c1.email = c2.email AND c1.email IS NOT NULL AND c1.email != '') OR
            (c1.phone = c2.phone AND c1.phone IS NOT NULL AND c1.phone != '') OR
            (SOUNDEX(c1.name) = SOUNDEX(c2.name) AND LENGTH(c1.name) > 3)
        );
    
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    -- Nettoyer les anciennes détections
    DELETE FROM customer_duplicates WHERE status = 'detected' AND created_at < DATE_SUB(NOW(), INTERVAL 7 DAY);
    
    OPEN customer_cursor;
    
    duplicate_loop: LOOP
        FETCH customer_cursor INTO customer_id_1, email_1, phone_1, name_1, customer_id_2, email_2, phone_2, name_2;
        
        IF done THEN
            LEAVE duplicate_loop;
        END IF;
        
        SET confidence = 0.00;
        SET match_criteria = JSON_OBJECT();
        
        -- Calcul du score de confiance
        IF email_1 = email_2 AND email_1 IS NOT NULL AND email_1 != '' THEN
            SET confidence = confidence + 0.50;
            SET match_criteria = JSON_SET(match_criteria, '$.email', TRUE);
        END IF;
        
        IF phone_1 = phone_2 AND phone_1 IS NOT NULL AND phone_1 != '' THEN
            SET confidence = confidence + 0.30;
            SET match_criteria = JSON_SET(match_criteria, '$.phone', TRUE);
        END IF;
        
        IF SOUNDEX(name_1) = SOUNDEX(name_2) THEN
            SET confidence = confidence + 0.20;
            SET match_criteria = JSON_SET(match_criteria, '$.name_similarity', TRUE);
        END IF;
        
        -- Enregistrer seulement si confiance >= 0.60
        IF confidence >= 0.60 THEN
            INSERT IGNORE INTO customer_duplicates (
                customer_id_primary, customer_id_duplicate, confidence_score, match_criteria
            ) VALUES (
                customer_id_1, customer_id_2, confidence, match_criteria
            );
        END IF;
        
    END LOOP;
    
    CLOSE customer_cursor;
    
    SELECT CONCAT('Détection terminée. ', ROW_COUNT(), ' doublons potentiels trouvés.') as result;
    
END//
DELIMITER ;

-- Event scheduler pour calculer les RFM scores automatiquement
SET GLOBAL event_scheduler = ON;

CREATE EVENT IF NOT EXISTS calculate_rfm_daily
ON SCHEDULE EVERY 1 DAY
STARTS '2025-08-23 02:00:00'
DO
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE customer_id_var INT;
    DECLARE customer_cursor CURSOR FOR 
        SELECT id FROM customers WHERE is_active = TRUE;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    OPEN customer_cursor;
    
    rfm_loop: LOOP
        FETCH customer_cursor INTO customer_id_var;
        
        IF done THEN
            LEAVE rfm_loop;
        END IF;
        
        CALL CalculateCustomerRFM(customer_id_var);
        
    END LOOP;
    
    CLOSE customer_cursor;
END;
