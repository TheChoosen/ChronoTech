-- Script d'optimisation MySQL pour ChronoTech
-- Amélioration des performances et configuration pour sync optimisée

USE bdm;

-- 1. Optimiser les connexions et la configuration
SET GLOBAL max_connections = 200;
SET GLOBAL connect_timeout = 10;
SET GLOBAL wait_timeout = 300;
SET GLOBAL interactive_timeout = 300;

-- 2. Optimiser les paramètres de performance
SET GLOBAL query_cache_type = 1;
SET GLOBAL query_cache_size = 67108864; -- 64MB
SET GLOBAL innodb_buffer_pool_size = 268435456; -- 256MB si possible

-- 3. Optimiser les tables existantes avec des index performants
-- Index sur work_orders pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_work_orders_status_priority ON work_orders(status, priority);
CREATE INDEX IF NOT EXISTS idx_work_orders_customer_status ON work_orders(customer_id, status);
CREATE INDEX IF NOT EXISTS idx_work_orders_technician_status ON work_orders(assigned_technician_id, status);
CREATE INDEX IF NOT EXISTS idx_work_orders_created ON work_orders(created_at DESC);

-- Index sur vehicles pour ML et analytics
CREATE INDEX IF NOT EXISTS idx_vehicles_customer ON vehicles(customer_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_maintenance ON vehicles(maintenance_status, next_maintenance_date);

-- Index sur users pour les requêtes de techniciens
CREATE INDEX IF NOT EXISTS idx_users_role_active ON users(role, is_active);
CREATE INDEX IF NOT EXISTS idx_users_availability ON users(availability_status, role);

-- Index sur customers pour les recherches
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);
CREATE INDEX IF NOT EXISTS idx_customers_department ON customers(department);

-- 4. Optimiser la table vehicle_telemetry pour les requêtes ML
ALTER TABLE vehicle_telemetry 
ADD INDEX idx_vehicle_recorded_desc (vehicle_id, recorded_at DESC),
ADD INDEX idx_recorded_recent (recorded_at DESC);

-- 5. Créer une vue optimisée pour les données ML fréquemment utilisées
CREATE OR REPLACE VIEW v_vehicle_maintenance_ml AS
SELECT 
    v.id,
    v.customer_id,
    v.make,
    v.model,
    v.year,
    v.mileage,
    v.engine_hours,
    v.last_maintenance_date,
    v.next_maintenance_date,
    v.maintenance_status,
    DATEDIFF(NOW(), v.last_maintenance_date) as days_since_maintenance,
    DATEDIFF(v.next_maintenance_date, NOW()) as days_until_maintenance,
    
    -- Dernières données télématiques
    vt.usage_intensity,
    vt.avg_daily_usage,
    vt.temperature_avg,
    vt.vibration_level,
    vt.oil_pressure,
    vt.brake_wear_level,
    vt.tire_wear_level,
    vt.recorded_at as telemetry_date,
    
    -- Info client
    c.name as customer_name,
    c.department
    
FROM vehicles v
LEFT JOIN customers c ON v.customer_id = c.id
LEFT JOIN vehicle_telemetry vt ON v.id = vt.vehicle_id 
    AND vt.recorded_at = (
        SELECT MAX(recorded_at) 
        FROM vehicle_telemetry vt2 
        WHERE vt2.vehicle_id = v.id
    );

-- 6. Créer une vue pour les statistiques de dashboard optimisées
CREATE OR REPLACE VIEW v_dashboard_stats AS
SELECT 
    -- Compteurs principaux
    (SELECT COUNT(*) FROM work_orders WHERE status = 'pending') as pending_work_orders,
    (SELECT COUNT(*) FROM work_orders WHERE status = 'in_progress') as active_work_orders,
    (SELECT COUNT(*) FROM work_orders WHERE status = 'completed' AND DATE(completed_date) = CURDATE()) as completed_today,
    (SELECT COUNT(*) FROM work_orders WHERE priority = 'urgent' AND status IN ('pending', 'in_progress')) as urgent_work_orders,
    
    -- Stats véhicules
    (SELECT COUNT(*) FROM vehicles) as total_vehicles,
    (SELECT COUNT(*) FROM vehicles WHERE maintenance_status = 'due') as vehicles_maintenance_due,
    (SELECT COUNT(*) FROM vehicles WHERE maintenance_status = 'overdue') as vehicles_maintenance_overdue,
    
    -- Stats techniciens
    (SELECT COUNT(*) FROM users WHERE role = 'technician' AND is_active = 1) as active_technicians,
    (SELECT COUNT(*) FROM users WHERE role = 'technician' AND availability_status = 'available') as available_technicians,
    
    -- Stats clients
    (SELECT COUNT(*) FROM customers) as total_customers,
    (SELECT COUNT(DISTINCT customer_id) FROM work_orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)) as active_customers_30d;

-- 7. Créer des procédures stockées pour les opérations fréquentes
DELIMITER //

CREATE OR REPLACE PROCEDURE GetTechnicianWorkload(IN tech_id INT)
BEGIN
    SELECT 
        COUNT(*) as total_assigned,
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
        COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as active_count,
        COUNT(CASE WHEN priority = 'urgent' THEN 1 END) as urgent_count,
        AVG(estimated_duration) as avg_duration
    FROM work_orders 
    WHERE assigned_technician_id = tech_id 
        AND status IN ('pending', 'in_progress');
END //

CREATE OR REPLACE PROCEDURE GetVehicleMaintenanceStatus(IN vehicle_id INT)
BEGIN
    SELECT 
        v.*,
        DATEDIFF(NOW(), v.last_maintenance_date) as days_since_maintenance,
        DATEDIFF(v.next_maintenance_date, NOW()) as days_until_maintenance,
        CASE 
            WHEN v.next_maintenance_date < NOW() THEN 'overdue'
            WHEN v.next_maintenance_date <= DATE_ADD(NOW(), INTERVAL 7 DAY) THEN 'due'
            ELSE 'ok'
        END as maintenance_urgency,
        vt.usage_intensity,
        vt.brake_wear_level,
        vt.tire_wear_level
    FROM vehicles v
    LEFT JOIN vehicle_telemetry vt ON v.id = vt.vehicle_id 
        AND vt.recorded_at = (SELECT MAX(recorded_at) FROM vehicle_telemetry WHERE vehicle_id = v.id)
    WHERE v.id = vehicle_id;
END //

DELIMITER ;

-- 8. Optimiser les paramètres de table pour de meilleures performances
ALTER TABLE work_orders ENGINE=InnoDB;
ALTER TABLE vehicles ENGINE=InnoDB;
ALTER TABLE customers ENGINE=InnoDB;
ALTER TABLE users ENGINE=InnoDB;
ALTER TABLE vehicle_telemetry ENGINE=InnoDB;

-- 9. Analyser les tables pour optimiser les statistiques
ANALYZE TABLE work_orders, vehicles, customers, users, vehicle_telemetry;

-- 10. Configuration de la réplication et backup (optionnel)
-- SET GLOBAL log_bin = ON;
-- SET GLOBAL expire_logs_days = 7;

COMMIT;

-- Afficher le résumé des optimisations
SELECT 'Optimisations MySQL appliquées avec succès' as status;
SELECT 
    'Tables optimisées' as category,
    COUNT(*) as count 
FROM information_schema.tables 
WHERE table_schema = 'bdm'
UNION ALL
SELECT 
    'Index créés' as category,
    COUNT(*) as count 
FROM information_schema.statistics 
WHERE table_schema = 'bdm'
UNION ALL
SELECT 
    'Vues créées' as category,
    COUNT(*) as count 
FROM information_schema.views 
WHERE table_schema = 'bdm';

SELECT 'Configuration MySQL optimisée pour ChronoTech - Performance améliorée' as message;
