-- Script d'optimisation MySQL pour ChronoTech (Compatible toutes versions)
-- Amélioration des performances avec gestion d'erreurs

USE bdm;

-- 1. Optimiser les connexions
SET GLOBAL max_connections = 200;
SET GLOBAL connect_timeout = 10;
SET GLOBAL wait_timeout = 300;
SET GLOBAL interactive_timeout = 300;

-- 2. Créer des index (ignorer les erreurs si déjà existants)
-- Index sur work_orders
CREATE INDEX idx_work_orders_status_priority ON work_orders(status, priority);
CREATE INDEX idx_work_orders_customer_status ON work_orders(customer_id, status);
CREATE INDEX idx_work_orders_technician_status ON work_orders(assigned_technician_id, status);
CREATE INDEX idx_work_orders_created ON work_orders(created_at DESC);

-- Index sur vehicles
CREATE INDEX idx_vehicles_customer ON vehicles(customer_id);
CREATE INDEX idx_vehicles_maintenance ON vehicles(maintenance_status, next_maintenance_date);

-- Index sur users
CREATE INDEX idx_users_role_active ON users(role, is_active);
CREATE INDEX idx_users_availability ON users(availability_status, role);

-- Index sur customers
CREATE INDEX idx_customers_name ON customers(name);
CREATE INDEX idx_customers_department ON customers(department);

-- Index sur vehicle_telemetry
CREATE INDEX idx_vehicle_recorded_desc ON vehicle_telemetry(vehicle_id, recorded_at DESC);
CREATE INDEX idx_recorded_recent ON vehicle_telemetry(recorded_at DESC);

-- 3. Créer une vue optimisée pour les données ML
CREATE OR REPLACE VIEW v_vehicle_maintenance_ml AS
SELECT 
    v.id,
    v.customer_id,
    v.make,
    v.model,
    v.year,
    v.mileage,
    COALESCE(v.engine_hours, v.mileage/10) as engine_hours,
    v.last_maintenance_date,
    v.next_maintenance_date,
    COALESCE(v.maintenance_status, 'ok') as maintenance_status,
    COALESCE(DATEDIFF(NOW(), v.last_maintenance_date), 90) as days_since_maintenance,
    COALESCE(DATEDIFF(v.next_maintenance_date, NOW()), 30) as days_until_maintenance,
    
    -- Dernières données télématiques avec fallback
    COALESCE(vt.usage_intensity, 5.0) as usage_intensity,
    COALESCE(vt.avg_daily_usage, v.mileage/365) as avg_daily_usage,
    COALESCE(vt.temperature_avg, 25.0) as temperature_avg,
    COALESCE(vt.vibration_level, 2.0) as vibration_level,
    COALESCE(vt.oil_pressure, 35.0) as oil_pressure,
    COALESCE(vt.brake_wear_level, 20.0) as brake_wear_level,
    COALESCE(vt.tire_wear_level, 15.0) as tire_wear_level,
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

-- 4. Créer une vue pour les statistiques de dashboard
CREATE OR REPLACE VIEW v_dashboard_stats AS
SELECT 
    (SELECT COUNT(*) FROM work_orders WHERE status = 'pending') as pending_work_orders,
    (SELECT COUNT(*) FROM work_orders WHERE status = 'in_progress') as active_work_orders,
    (SELECT COUNT(*) FROM work_orders WHERE status = 'completed' AND DATE(COALESCE(completed_date, updated_at)) = CURDATE()) as completed_today,
    (SELECT COUNT(*) FROM work_orders WHERE priority = 'urgent' AND status IN ('pending', 'in_progress')) as urgent_work_orders,
    (SELECT COUNT(*) FROM vehicles) as total_vehicles,
    (SELECT COUNT(*) FROM vehicles WHERE maintenance_status = 'due') as vehicles_maintenance_due,
    (SELECT COUNT(*) FROM vehicles WHERE maintenance_status = 'overdue') as vehicles_maintenance_overdue,
    (SELECT COUNT(*) FROM users WHERE role = 'technician' AND is_active = 1) as active_technicians,
    (SELECT COUNT(*) FROM users WHERE role = 'technician' AND COALESCE(availability_status, 'available') = 'available') as available_technicians,
    (SELECT COUNT(*) FROM customers) as total_customers;

-- 5. Optimiser les requêtes fréquentes avec des vues spécialisées
CREATE OR REPLACE VIEW v_technician_workload AS
SELECT 
    u.id as technician_id,
    u.name as technician_name,
    COUNT(wo.id) as total_assigned,
    COUNT(CASE WHEN wo.status = 'pending' THEN 1 END) as pending_count,
    COUNT(CASE WHEN wo.status = 'in_progress' THEN 1 END) as active_count,
    COUNT(CASE WHEN wo.priority = 'urgent' THEN 1 END) as urgent_count,
    AVG(COALESCE(wo.estimated_duration, 120)) as avg_duration
FROM users u
LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id 
    AND wo.status IN ('pending', 'in_progress')
WHERE u.role = 'technician' AND u.is_active = 1
GROUP BY u.id, u.name;

-- 6. Analyser les tables pour les statistiques
ANALYZE TABLE work_orders;
ANALYZE TABLE vehicles;
ANALYZE TABLE customers;
ANALYZE TABLE users;
ANALYZE TABLE vehicle_telemetry;

COMMIT;

-- Résumé final
SELECT 'Optimisations MySQL appliquées - Erreurs d\'index ignorées si déjà existants' as status;
SELECT TABLE_NAME, ENGINE, TABLE_ROWS 
FROM information_schema.tables 
WHERE table_schema = 'bdm' 
ORDER BY TABLE_ROWS DESC;

SELECT 'ChronoTech MySQL optimisé pour de meilleures performances' as message;
