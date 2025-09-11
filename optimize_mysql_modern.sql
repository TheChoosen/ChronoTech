-- Script d'optimisation MySQL pour ChronoTech (Version MySQL 8.0+)
-- Amélioration des performances sans les paramètres obsolètes

USE bdm;

-- 1. Optimiser les connexions uniquement avec les paramètres supportés
SET GLOBAL max_connections = 200;
SET GLOBAL connect_timeout = 10;
SET GLOBAL wait_timeout = 300;
SET GLOBAL interactive_timeout = 300;

-- 2. Créer des index performants sur les tables existantes
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

-- 3. Optimiser la table vehicle_telemetry pour les requêtes ML
ALTER TABLE vehicle_telemetry 
ADD INDEX IF NOT EXISTS idx_vehicle_recorded_desc (vehicle_id, recorded_at DESC);

ALTER TABLE vehicle_telemetry 
ADD INDEX IF NOT EXISTS idx_recorded_recent (recorded_at DESC);

-- 4. Créer une vue optimisée pour les données ML fréquemment utilisées
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

-- 5. Créer une vue pour les statistiques de dashboard optimisées
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

-- 6. Analyser les tables pour optimiser les statistiques
ANALYZE TABLE work_orders, vehicles, customers, users, vehicle_telemetry;

COMMIT;

-- Afficher le résumé des optimisations
SELECT 'Optimisations MySQL 8.0+ appliquées avec succès' as status;
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
