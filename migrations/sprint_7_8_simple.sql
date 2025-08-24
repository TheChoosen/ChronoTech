-- Sprint 7-8: Customer 360 Advanced & Analytics
-- Migration simplifiée

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

SELECT 'Migration Sprint 7-8 terminée avec succès!' as message;
