-- Migration Sprint 4 - Analyse prédictive et proactive
-- Tables pour maintenance prévisionnelle, heatmap et eco-scoring

-- Table pour les prédictions de maintenance véhicules
CREATE TABLE IF NOT EXISTS vehicle_maintenance_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id INT NOT NULL,
    prediction_type ENUM('maintenance', 'breakdown', 'service', 'inspection') NOT NULL,
    predicted_date DATE NOT NULL,
    confidence_score DECIMAL(5,2) NOT NULL, -- 0.00 to 100.00
    urgency_level ENUM('low', 'medium', 'high', 'critical') NOT NULL,
    predicted_cost DECIMAL(10,2) NULL,
    maintenance_category VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    data_sources JSON NOT NULL, -- sources utilisées pour la prédiction
    algorithm_used VARCHAR(50) DEFAULT 'rule_based',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_dismissed BOOLEAN DEFAULT FALSE,
    dismissed_by INT NULL,
    dismissed_at DATETIME NULL,
    dismissed_reason TEXT NULL,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
    FOREIGN KEY (dismissed_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_vehicle (vehicle_id),
    INDEX idx_predicted_date (predicted_date),
    INDEX idx_urgency (urgency_level),
    INDEX idx_created_at (created_at),
    INDEX idx_confidence (confidence_score),
    INDEX idx_dismissed (is_dismissed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour les zones d'intervention géographiques (heatmap)
CREATE TABLE IF NOT EXISTS intervention_zones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    zone_name VARCHAR(255) NOT NULL,
    center_latitude DECIMAL(10, 8) NOT NULL,
    center_longitude DECIMAL(11, 8) NOT NULL,
    radius_km DECIMAL(6,2) NOT NULL DEFAULT 5.00,
    color_hex VARCHAR(7) DEFAULT '#ff6b6b',
    intervention_count INT DEFAULT 0,
    avg_response_time_minutes INT DEFAULT 0,
    total_cost DECIMAL(12,2) DEFAULT 0.00,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_location (center_latitude, center_longitude),
    INDEX idx_intervention_count (intervention_count),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour les métriques d'eco-scoring des work orders
CREATE TABLE IF NOT EXISTS work_order_eco_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_id INT NOT NULL,
    eco_score INT NOT NULL, -- Score de 0 à 100
    carbon_footprint_kg DECIMAL(8,2) DEFAULT 0.00,
    energy_consumption_kwh DECIMAL(8,2) DEFAULT 0.00,
    waste_generated_kg DECIMAL(8,2) DEFAULT 0.00,
    recycled_materials_kg DECIMAL(8,2) DEFAULT 0.00,
    travel_distance_km DECIMAL(8,2) DEFAULT 0.00,
    eco_friendly_materials_used BOOLEAN DEFAULT FALSE,
    green_practices_applied JSON NULL, -- Liste des pratiques éco appliquées
    calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    UNIQUE KEY unique_work_order_eco (work_order_id),
    INDEX idx_eco_score (eco_score),
    INDEX idx_carbon_footprint (carbon_footprint_kg),
    INDEX idx_calculated_at (calculated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour l'historique des interventions par zone
CREATE TABLE IF NOT EXISTS zone_intervention_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    zone_id INT NOT NULL,
    work_order_id INT NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    intervention_date DATETIME NOT NULL,
    duration_minutes INT NOT NULL,
    cost DECIMAL(10,2) NOT NULL,
    technician_id INT NOT NULL,
    customer_satisfaction INT NULL, -- 1-5 stars
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (zone_id) REFERENCES intervention_zones(id) ON DELETE CASCADE,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_zone (zone_id),
    INDEX idx_work_order (work_order_id),
    INDEX idx_intervention_date (intervention_date),
    INDEX idx_location (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour les alertes prédictives
CREATE TABLE IF NOT EXISTS predictive_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_type ENUM('maintenance_due', 'breakdown_risk', 'cost_anomaly', 'efficiency_drop') NOT NULL,
    entity_type ENUM('vehicle', 'work_order', 'zone', 'technician') NOT NULL,
    entity_id INT NOT NULL,
    severity ENUM('info', 'warning', 'error', 'critical') NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    suggested_action TEXT NULL,
    data_snapshot JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at DATETIME NULL,
    acknowledged_by INT NULL,
    resolved_at DATETIME NULL,
    resolved_by INT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (acknowledged_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (resolved_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_alert_type (alert_type),
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_severity (severity),
    INDEX idx_active (is_active),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table pour les patterns d'intervention (machine learning)
CREATE TABLE IF NOT EXISTS intervention_patterns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pattern_name VARCHAR(255) NOT NULL,
    pattern_type ENUM('seasonal', 'geographic', 'temporal', 'equipment') NOT NULL,
    confidence_level DECIMAL(5,2) NOT NULL,
    pattern_data JSON NOT NULL,
    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_validated DATETIME DEFAULT CURRENT_TIMESTAMP,
    validation_count INT DEFAULT 1,
    is_validated BOOLEAN DEFAULT FALSE,
    INDEX idx_pattern_type (pattern_type),
    INDEX idx_confidence (confidence_level),
    INDEX idx_validated (is_validated)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Ajouter des colonnes aux work_orders pour le tracking géographique
ALTER TABLE work_orders 
ADD COLUMN IF NOT EXISTS latitude DECIMAL(10, 8) NULL AFTER description,
ADD COLUMN IF NOT EXISTS longitude DECIMAL(11, 8) NULL AFTER latitude,
ADD COLUMN IF NOT EXISTS zone_id INT NULL AFTER longitude,
ADD COLUMN IF NOT EXISTS eco_score_calculated BOOLEAN DEFAULT FALSE AFTER zone_id;

-- Index géographiques
CREATE INDEX idx_wo_location ON work_orders (latitude, longitude);
CREATE INDEX idx_wo_zone ON work_orders (zone_id);

-- Vue pour le dashboard de maintenance prédictive
CREATE OR REPLACE VIEW predictive_maintenance_dashboard AS
SELECT 
    v.id as vehicle_id,
    v.license_plate,
    v.make,
    v.model,
    v.year,
    vmp.prediction_type,
    vmp.predicted_date,
    vmp.urgency_level,
    vmp.confidence_score,
    vmp.predicted_cost,
    vmp.description as prediction_description,
    DATEDIFF(vmp.predicted_date, CURDATE()) as days_until_prediction,
    (SELECT COUNT(*) FROM work_orders wo WHERE wo.vehicle_id = v.id AND wo.status = 'completed' AND wo.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)) as recent_interventions
FROM vehicles v
INNER JOIN vehicle_maintenance_predictions vmp ON v.id = vmp.vehicle_id
WHERE vmp.is_dismissed = FALSE
ORDER BY vmp.urgency_level DESC, vmp.predicted_date ASC;

-- Vue pour la heatmap des interventions
CREATE OR REPLACE VIEW intervention_heatmap_data AS
SELECT 
    iz.id as zone_id,
    iz.zone_name,
    iz.center_latitude,
    iz.center_longitude,
    iz.radius_km,
    iz.color_hex,
    COUNT(zih.id) as total_interventions,
    AVG(zih.duration_minutes) as avg_duration,
    SUM(zih.cost) as total_cost,
    AVG(zih.customer_satisfaction) as avg_satisfaction,
    MAX(zih.intervention_date) as last_intervention
FROM intervention_zones iz
LEFT JOIN zone_intervention_history zih ON iz.id = zih.zone_id
WHERE iz.is_active = TRUE
GROUP BY iz.id
ORDER BY total_interventions DESC;

-- Vue pour les statistiques eco-score
CREATE OR REPLACE VIEW eco_score_statistics AS
SELECT 
    woes.eco_score,
    COUNT(*) as work_order_count,
    AVG(woes.carbon_footprint_kg) as avg_carbon_footprint,
    AVG(woes.energy_consumption_kwh) as avg_energy_consumption,
    AVG(woes.travel_distance_km) as avg_travel_distance,
    SUM(woes.recycled_materials_kg) as total_recycled_materials,
    COUNT(CASE WHEN woes.eco_friendly_materials_used = TRUE THEN 1 END) as eco_friendly_count
FROM work_order_eco_scores woes
WHERE woes.calculated_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
GROUP BY woes.eco_score
ORDER BY woes.eco_score DESC;

COMMIT;
