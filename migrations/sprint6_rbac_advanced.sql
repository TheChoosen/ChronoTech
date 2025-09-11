-- SPRINT 6 - RBAC AVANCÉ & API PUBLIQUE DOCUMENTÉE
-- Transparence et sécurité avancées

-- ============================================================================
-- 1. SYSTÈME DE PERMISSIONS DYNAMIQUES
-- ============================================================================

-- Table des permissions disponibles dans le système
CREATE TABLE IF NOT EXISTS system_permissions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(30) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_resource_action (resource, action),
    INDEX idx_name (name)
);

-- Table des rôles avec permissions dynamiques
CREATE TABLE IF NOT EXISTS user_roles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table de liaison rôles-permissions (many-to-many)
CREATE TABLE IF NOT EXISTS role_permissions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INT,
    
    FOREIGN KEY (role_id) REFERENCES user_roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES system_permissions(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL,
    
    UNIQUE KEY unique_role_permission (role_id, permission_id),
    INDEX idx_role_id (role_id),
    INDEX idx_permission_id (permission_id)
);

-- Table des permissions utilisateur spécifiques (overrides)
CREATE TABLE IF NOT EXISTS user_permissions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    permission_id INT NOT NULL,
    is_granted BOOLEAN NOT NULL DEFAULT TRUE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INT,
    expires_at TIMESTAMP NULL,
    reason TEXT,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES system_permissions(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL,
    
    UNIQUE KEY unique_user_permission (user_id, permission_id),
    INDEX idx_user_id (user_id),
    INDEX idx_permission_id (permission_id),
    INDEX idx_expires_at (expires_at)
);

-- ============================================================================
-- 2. SYSTÈME D'AUDIT INTELLIGENT
-- ============================================================================

-- Table d'audit enrichie pour toutes les actions système
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    user_email VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(50),
    old_values JSON,
    new_values JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    session_id VARCHAR(100),
    api_endpoint VARCHAR(255),
    http_method VARCHAR(10),
    response_status INT,
    execution_time_ms INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_resource (resource_type, resource_id),
    INDEX idx_created_at (created_at),
    INDEX idx_ip_address (ip_address),
    INDEX idx_session_id (session_id)
);

-- Table pour les tentatives d'accès non autorisées
CREATE TABLE IF NOT EXISTS security_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    event_type ENUM('unauthorized_access', 'permission_denied', 'suspicious_activity', 'login_failure', 'token_abuse') NOT NULL,
    severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    user_id INT,
    ip_address VARCHAR(45) NOT NULL,
    user_agent TEXT,
    requested_resource VARCHAR(255),
    details JSON,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_by INT,
    resolved_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (resolved_by) REFERENCES users(id) ON DELETE SET NULL,
    
    INDEX idx_event_type (event_type),
    INDEX idx_severity (severity),
    INDEX idx_user_id (user_id),
    INDEX idx_ip_address (ip_address),
    INDEX idx_created_at (created_at),
    INDEX idx_is_resolved (is_resolved)
);

-- ============================================================================
-- 3. API TOKENS POUR INTÉGRATIONS EXTERNES
-- ============================================================================

-- Table des tokens API pour les intégrations partenaires
CREATE TABLE IF NOT EXISTS api_tokens (
    id INT PRIMARY KEY AUTO_INCREMENT,
    token_name VARCHAR(100) NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    partner_name VARCHAR(100) NOT NULL,
    partner_email VARCHAR(255),
    permissions JSON NOT NULL, -- Liste des permissions accordées
    rate_limit_per_hour INT DEFAULT 1000,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    last_used_at TIMESTAMP NULL,
    usage_count INT DEFAULT 0,
    
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT,
    
    INDEX idx_token_hash (token_hash),
    INDEX idx_partner_name (partner_name),
    INDEX idx_is_active (is_active),
    INDEX idx_expires_at (expires_at)
);

-- Table de logs des appels API
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    token_id INT,
    endpoint VARCHAR(255) NOT NULL,
    http_method VARCHAR(10) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    response_status INT NOT NULL,
    response_time_ms INT,
    request_size_bytes INT,
    response_size_bytes INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (token_id) REFERENCES api_tokens(id) ON DELETE SET NULL,
    
    INDEX idx_token_id (token_id),
    INDEX idx_endpoint (endpoint),
    INDEX idx_created_at (created_at),
    INDEX idx_response_status (response_status)
);

-- ============================================================================
-- 4. DONNÉES INITIALES - PERMISSIONS SYSTÈME
-- ============================================================================

-- Permissions pour Work Orders
INSERT IGNORE INTO system_permissions (name, resource, action, description) VALUES
('work_orders.view_own', 'work_orders', 'view', 'Voir ses propres bons de travail'),
('work_orders.view_all', 'work_orders', 'view', 'Voir tous les bons de travail'),
('work_orders.create', 'work_orders', 'create', 'Créer des bons de travail'),
('work_orders.edit_own', 'work_orders', 'edit', 'Modifier ses propres bons de travail'),
('work_orders.edit_all', 'work_orders', 'edit', 'Modifier tous les bons de travail'),
('work_orders.delete', 'work_orders', 'delete', 'Supprimer des bons de travail'),
('work_orders.assign', 'work_orders', 'assign', 'Assigner des bons de travail'),
('work_orders.close', 'work_orders', 'close', 'Clôturer des bons de travail'),

-- Permissions pour Customers
('customers.view', 'customers', 'view', 'Voir les clients'),
('customers.create', 'customers', 'create', 'Créer des clients'),
('customers.edit', 'customers', 'edit', 'Modifier des clients'),
('customers.delete', 'customers', 'delete', 'Supprimer des clients'),
('customers.export', 'customers', 'export', 'Exporter les données clients'),

-- Permissions pour Reports
('reports.view', 'reports', 'view', 'Voir les rapports'),
('reports.create', 'reports', 'create', 'Créer des rapports'),
('reports.export', 'reports', 'export', 'Exporter des rapports'),

-- Permissions pour Analytics
('analytics.dashboard', 'analytics', 'view', 'Accéder au tableau de bord analytique'),
('analytics.advanced', 'analytics', 'advanced', 'Accéder aux analyses avancées'),

-- Permissions pour Users Management
('users.view', 'users', 'view', 'Voir les utilisateurs'),
('users.create', 'users', 'create', 'Créer des utilisateurs'),
('users.edit', 'users', 'edit', 'Modifier des utilisateurs'),
('users.delete', 'users', 'delete', 'Supprimer des utilisateurs'),
('users.manage_permissions', 'users', 'permissions', 'Gérer les permissions utilisateur'),

-- Permissions pour System Administration
('system.audit_logs', 'system', 'audit', 'Accéder aux logs d''audit'),
('system.api_management', 'system', 'api', 'Gérer les tokens API'),
('system.security_events', 'system', 'security', 'Voir les événements de sécurité');

-- ============================================================================
-- 5. RÔLES SYSTÈME PRÉDÉFINIS
-- ============================================================================

INSERT IGNORE INTO user_roles (name, display_name, description, is_system_role) VALUES
('admin', 'Administrateur', 'Accès complet au système', TRUE),
('manager', 'Gestionnaire', 'Gestion des équipes et rapports', TRUE),
('supervisor', 'Superviseur', 'Supervision des opérations', TRUE),
('technician', 'Technicien', 'Accès limité aux propres interventions', TRUE),
('partner_api', 'Partenaire API', 'Accès API pour intégrations externes', TRUE),
('viewer', 'Consultation', 'Accès en lecture seule', TRUE);

-- ============================================================================
-- 6. ASSIGNATION DES PERMISSIONS AUX RÔLES
-- ============================================================================

-- Rôle Admin (toutes les permissions)
INSERT IGNORE INTO role_permissions (role_id, permission_id, granted_by)
SELECT 
    (SELECT id FROM user_roles WHERE name = 'admin'),
    p.id,
    1 -- ID de l'admin système
FROM system_permissions p;

-- Rôle Manager 
INSERT IGNORE INTO role_permissions (role_id, permission_id, granted_by)
SELECT 
    (SELECT id FROM user_roles WHERE name = 'manager'),
    p.id,
    1
FROM system_permissions p
WHERE p.name IN (
    'work_orders.view_all', 'work_orders.create', 'work_orders.edit_all', 'work_orders.assign', 'work_orders.close',
    'customers.view', 'customers.create', 'customers.edit', 'customers.export',
    'reports.view', 'reports.create', 'reports.export',
    'analytics.dashboard', 'analytics.advanced',
    'users.view', 'users.create', 'users.edit'
);

-- Rôle Supervisor
INSERT IGNORE INTO role_permissions (role_id, permission_id, granted_by)
SELECT 
    (SELECT id FROM user_roles WHERE name = 'supervisor'),
    p.id,
    1
FROM system_permissions p
WHERE p.name IN (
    'work_orders.view_all', 'work_orders.edit_all', 'work_orders.assign',
    'customers.view', 'customers.edit',
    'reports.view', 'reports.create',
    'analytics.dashboard'
);

-- Rôle Technicien (accès limité - User Story principale)
INSERT IGNORE INTO role_permissions (role_id, permission_id, granted_by)
SELECT 
    (SELECT id FROM user_roles WHERE name = 'technician'),
    p.id,
    1
FROM system_permissions p
WHERE p.name IN (
    'work_orders.view_own', 'work_orders.edit_own',
    'customers.view'
);

-- Rôle Partner API
INSERT IGNORE INTO role_permissions (role_id, permission_id, granted_by)
SELECT 
    (SELECT id FROM user_roles WHERE name = 'partner_api'),
    p.id,
    1
FROM system_permissions p
WHERE p.name IN (
    'work_orders.view_all', 'work_orders.create',
    'customers.view', 'customers.create'
);

-- Rôle Viewer
INSERT IGNORE INTO role_permissions (role_id, permission_id, granted_by)
SELECT 
    (SELECT id FROM user_roles WHERE name = 'viewer'),
    p.id,
    1
FROM system_permissions p
WHERE p.name IN (
    'work_orders.view_own',
    'customers.view',
    'reports.view'
);

-- ============================================================================
-- 7. VUES POUR FACILITER LES REQUÊTES RBAC
-- ============================================================================

-- Vue pour obtenir toutes les permissions d'un utilisateur
CREATE OR REPLACE VIEW user_effective_permissions AS
SELECT 
    u.id as user_id,
    u.email,
    u.role as current_role,
    p.name as permission_name,
    p.resource,
    p.action,
    'role' as source,
    ur.name as role_name
FROM users u
JOIN user_roles ur ON u.role = ur.name
JOIN role_permissions rp ON ur.id = rp.role_id
JOIN system_permissions p ON rp.permission_id = p.id

UNION ALL

SELECT 
    u.id as user_id,
    u.email,
    u.role as current_role,
    p.name as permission_name,
    p.resource,
    p.action,
    CASE WHEN up.is_granted THEN 'user_granted' ELSE 'user_denied' END as source,
    NULL as role_name
FROM users u
JOIN user_permissions up ON u.id = up.user_id
JOIN system_permissions p ON up.permission_id = p.id
WHERE (up.expires_at IS NULL OR up.expires_at > NOW());

-- Vue pour les statistiques d'audit
CREATE OR REPLACE VIEW audit_statistics AS
SELECT 
    DATE(created_at) as audit_date,
    action,
    resource_type,
    COUNT(*) as action_count,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT ip_address) as unique_ips
FROM audit_logs
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(created_at), action, resource_type;

-- ============================================================================
-- 8. TRIGGERS POUR AUDIT AUTOMATIQUE
-- ============================================================================

-- Trigger pour auditer les modifications d'utilisateurs
DELIMITER $$

CREATE TRIGGER audit_users_update
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (
        user_id, user_email, action, resource_type, resource_id,
        old_values, new_values, created_at
    ) VALUES (
        NEW.id,
        NEW.email,
        'update',
        'users',
        NEW.id,
        JSON_OBJECT(
            'name', OLD.name,
            'email', OLD.email,
            'role', OLD.role,
            'is_active', OLD.is_active
        ),
        JSON_OBJECT(
            'name', NEW.name,
            'email', NEW.email,
            'role', NEW.role,
            'is_active', NEW.is_active
        ),
        NOW()
    );
END$$

-- Trigger pour auditer les modifications de work orders
CREATE TRIGGER audit_work_orders_update
AFTER UPDATE ON work_orders
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (
        user_id, action, resource_type, resource_id,
        old_values, new_values, created_at
    ) VALUES (
        NEW.assigned_technician_id,
        'update',
        'work_orders',
        NEW.id,
        JSON_OBJECT(
            'status', OLD.status,
            'priority', OLD.priority,
            'assigned_technician_id', OLD.assigned_technician_id
        ),
        JSON_OBJECT(
            'status', NEW.status,
            'priority', NEW.priority,
            'assigned_technician_id', NEW.assigned_technician_id
        ),
        NOW()
    );
END$$

DELIMITER ;

-- ============================================================================
-- 9. FONCTION POUR VÉRIFIER LES PERMISSIONS
-- ============================================================================

DELIMITER $$

CREATE FUNCTION user_has_permission(
    p_user_id INT,
    p_permission_name VARCHAR(100)
) RETURNS BOOLEAN
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE permission_count INT DEFAULT 0;
    
    -- Vérifier si l'utilisateur a la permission via son rôle
    SELECT COUNT(*) INTO permission_count
    FROM users u
    JOIN user_roles ur ON u.role = ur.name
    JOIN role_permissions rp ON ur.id = rp.role_id
    JOIN system_permissions sp ON rp.permission_id = sp.id
    WHERE u.id = p_user_id 
    AND sp.name = p_permission_name
    AND u.is_active = TRUE;
    
    -- Si trouvé dans le rôle, vérifier s'il n'est pas révoqué spécifiquement
    IF permission_count > 0 THEN
        SELECT COUNT(*) INTO permission_count
        FROM user_permissions up
        JOIN system_permissions sp ON up.permission_id = sp.id
        WHERE up.user_id = p_user_id
        AND sp.name = p_permission_name
        AND up.is_granted = FALSE
        AND (up.expires_at IS NULL OR up.expires_at > NOW());
        
        -- Si révoqué spécifiquement, retourner FALSE
        IF permission_count > 0 THEN
            RETURN FALSE;
        END IF;
        
        RETURN TRUE;
    END IF;
    
    -- Vérifier les permissions accordées spécifiquement à l'utilisateur
    SELECT COUNT(*) INTO permission_count
    FROM user_permissions up
    JOIN system_permissions sp ON up.permission_id = sp.id
    WHERE up.user_id = p_user_id
    AND sp.name = p_permission_name
    AND up.is_granted = TRUE
    AND (up.expires_at IS NULL OR up.expires_at > NOW());
    
    RETURN permission_count > 0;
END$$

DELIMITER ;

-- ============================================================================
-- 10. INDEX POUR PERFORMANCE
-- ============================================================================

-- Index composé pour les requêtes fréquentes de permissions
CREATE INDEX idx_user_permission_check ON users(id, role, is_active);
CREATE INDEX idx_role_permission_lookup ON role_permissions(role_id, permission_id);
CREATE INDEX idx_audit_user_resource ON audit_logs(user_id, resource_type, created_at);
CREATE INDEX idx_security_events_analysis ON security_events(event_type, severity, created_at);

-- ============================================================================
-- 11. MISE À JOUR DES UTILISATEURS EXISTANTS
-- ============================================================================

-- Assigner les nouveaux rôles aux utilisateurs existants selon leur rôle actuel
UPDATE users SET role = 'admin' WHERE role IN ('admin', 'administrator');
UPDATE users SET role = 'manager' WHERE role IN ('manager', 'gestionnaire');
UPDATE users SET role = 'supervisor' WHERE role IN ('supervisor', 'superviseur');
UPDATE users SET role = 'technician' WHERE role IN ('technician', 'technicien', 'field_tech');
UPDATE users SET role = 'viewer' WHERE role NOT IN ('admin', 'manager', 'supervisor', 'technician');

-- Message de confirmation
SELECT 'Sprint 6 - RBAC Avancé & API - Schema créé avec succès!' as status,
       (SELECT COUNT(*) FROM system_permissions) as total_permissions,
       (SELECT COUNT(*) FROM user_roles) as total_roles,
       (SELECT COUNT(*) FROM role_permissions) as total_role_permissions;
