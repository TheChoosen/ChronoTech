-- MIGRATION SPRINT 5-6 - CUSTOMER 360 AVANCÉ
-- Version corrigée pour compatibilité MySQL
-- Exécution: mysql -h host -u user -p database < sprint_5_6_fixed.sql

USE bdm;

-- Désactiver les vérifications de clés étrangères temporairement
SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- TABLE: customer_activity (améliorations)
-- =====================================================

-- Vérifier et ajouter des colonnes à customer_activity
ALTER TABLE customer_activity 
ADD COLUMN priority ENUM('low', 'normal', 'high', 'urgent') DEFAULT 'normal',
ADD COLUMN visibility ENUM('public', 'internal', 'private') DEFAULT 'internal',
ADD COLUMN tags JSON,
ADD COLUMN attachments JSON;

-- =====================================================
-- TABLE: customer_consents (RGPD/Loi 25)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_consents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    consent_type ENUM('marketing_email', 'marketing_sms', 'marketing_phone', 'data_processing', 'data_sharing', 'cookies', 'newsletters', 'surveys', 'promotional', 'analytics') NOT NULL,
    purpose_description TEXT,
    legal_basis ENUM('consent', 'contract', 'legal_obligation', 'vital_interest', 'public_task', 'legitimate_interest') DEFAULT 'consent',
    is_active BOOLEAN DEFAULT TRUE,
    consent_given_at TIMESTAMP NULL,
    consent_withdrawn_at TIMESTAMP NULL,
    version VARCHAR(10) DEFAULT '1.0',
    source ENUM('website', 'email', 'phone', 'in_person', 'paper_form', 'mobile_app', 'api') DEFAULT 'website',
    ip_address VARCHAR(45),
    user_agent TEXT,
    collected_by INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (collected_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY unique_customer_consent (customer_id, consent_type),
    INDEX (customer_id, is_active),
    INDEX (consent_type, is_active),
    INDEX (created_at),
    INDEX (legal_basis)
);

-- =====================================================
-- TABLE: customer_consent_history (audit trail)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_consent_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    consent_id INT NOT NULL,
    action_type ENUM('granted', 'withdrawn', 'updated', 'expired') NOT NULL,
    previous_status BOOLEAN,
    new_status BOOLEAN,
    reason TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    source ENUM('website', 'email', 'phone', 'in_person', 'paper_form', 'mobile_app', 'api', 'system') DEFAULT 'website',
    processed_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (consent_id) REFERENCES customer_consents(id) ON DELETE CASCADE,
    FOREIGN KEY (processed_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX (customer_id, created_at),
    INDEX (consent_id, created_at),
    INDEX (action_type, created_at)
);

-- =====================================================
-- TABLE: customer_documents (gestion documentaire)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    document_type ENUM('contract', 'invoice', 'quote', 'report', 'certificate', 'warranty', 'manual', 'photo', 'video', 'audio', 'presentation', 'spreadsheet', 'other') NOT NULL,
    category ENUM('administrative', 'technical', 'commercial', 'legal', 'financial', 'operational', 'compliance') DEFAULT 'administrative',
    title VARCHAR(255) NOT NULL,
    description TEXT,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT UNSIGNED NOT NULL,
    mime_type VARCHAR(100),
    hash_sha256 VARCHAR(64),
    is_signed BOOLEAN DEFAULT FALSE,
    signed_at TIMESTAMP NULL,
    signature_provider ENUM('internal', 'docusign', 'adobe_sign', 'hellosign', 'pandadoc') NULL,
    signature_data JSON,
    access_level ENUM('public', 'internal', 'restricted', 'private') DEFAULT 'private',
    expires_at TIMESTAMP NULL,
    version VARCHAR(20) DEFAULT '1.0',
    parent_document_id INT NULL,
    created_by INT,
    updated_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_document_id) REFERENCES customer_documents(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX (customer_id, document_type),
    INDEX (document_type, is_signed),
    INDEX (created_at),
    INDEX (hash_sha256),
    INDEX (expires_at)
);

-- =====================================================
-- TABLE: customer_document_access_log (audit d'accès)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_document_access_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    user_id INT,
    access_type ENUM('view', 'download', 'share', 'sign', 'delete', 'update') NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (document_id) REFERENCES customer_documents(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX (document_id, accessed_at),
    INDEX (user_id, accessed_at),
    INDEX (access_type, accessed_at)
);

-- =====================================================
-- TABLE: customer_finances (profil financier)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_finances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    credit_limit DECIMAL(12,2) DEFAULT 0.00,
    credit_used DECIMAL(12,2) DEFAULT 0.00,
    payment_terms INT DEFAULT 30,
    price_tier ENUM('standard', 'premium', 'vip', 'corporate', 'government') DEFAULT 'standard',
    preferred_payment_method ENUM('cash', 'check', 'transfer', 'credit_card', 'debit_card', 'paypal', 'stripe') DEFAULT 'transfer',
    auto_payment BOOLEAN DEFAULT FALSE,
    late_payment_fee DECIMAL(8,2) DEFAULT 0.00,
    discount_percent DECIMAL(5,2) DEFAULT 0.00,
    tax_exempt BOOLEAN DEFAULT FALSE,
    tax_id VARCHAR(50),
    risk_score INT DEFAULT 50,
    last_payment_date TIMESTAMP NULL,
    next_review_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    UNIQUE KEY (customer_id),
    INDEX (price_tier),
    INDEX (risk_score),
    INDEX (next_review_date)
);

-- =====================================================
-- TABLE: customer_payment_methods (méthodes de paiement)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_payment_methods (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    method_type ENUM('credit_card', 'debit_card', 'bank_account', 'paypal', 'stripe', 'square', 'other') NOT NULL,
    provider VARCHAR(100),
    token VARCHAR(255),
    last_four VARCHAR(4),
    expires_at DATE,
    is_default BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    billing_name VARCHAR(255),
    billing_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX (customer_id, is_default),
    INDEX (method_type, is_verified)
);

-- =====================================================
-- TABLE: customer_balance_history (historique des soldes)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_balance_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    event_type ENUM('invoice', 'payment', 'credit', 'debit', 'adjustment', 'fee', 'refund') NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    balance_before DECIMAL(12,2) NOT NULL,
    balance_after DECIMAL(12,2) NOT NULL,
    reference_type ENUM('invoice', 'payment', 'work_order', 'adjustment', 'fee') NULL,
    reference_id INT NULL,
    description TEXT,
    processed_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (processed_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX (customer_id, created_at),
    INDEX (event_type, created_at),
    INDEX (reference_type, reference_id)
);

-- =====================================================
-- TABLE: automation_rules (règles d'automatisation)
-- =====================================================

CREATE TABLE IF NOT EXISTS automation_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    rule_type ENUM('email', 'sms', 'task', 'notification', 'workflow', 'reminder', 'escalation', 'report') NOT NULL,
    trigger_event ENUM('customer_created', 'vehicle_added', 'work_order_created', 'work_order_completed', 'invoice_created', 'invoice_overdue', 'payment_received', 'appointment_scheduled', 'document_signed', 'consent_expired') NOT NULL,
    conditions JSON,
    actions JSON,
    applies_to ENUM('all', 'customer', 'vehicle', 'work_order', 'specific') DEFAULT 'all',
    is_active BOOLEAN DEFAULT TRUE,
    priority INT DEFAULT 0,
    max_executions INT DEFAULT 0,
    cooldown_hours INT DEFAULT 24,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX (rule_type, is_active),
    INDEX (trigger_event, is_active),
    INDEX (applies_to, is_active)
);

-- =====================================================
-- TABLE: customer_automations (automations par client)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_automations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    rule_id INT NOT NULL,
    vehicle_id INT NULL,
    status ENUM('active', 'paused', 'completed', 'failed', 'cancelled') DEFAULT 'active',
    next_execution TIMESTAMP NULL,
    last_execution TIMESTAMP NULL,
    execution_count INT DEFAULT 0,
    max_executions INT DEFAULT 0,
    context_data JSON,
    results_log JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (rule_id) REFERENCES automation_rules(id) ON DELETE CASCADE,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
    INDEX (customer_id, status),
    INDEX (rule_id, status),
    INDEX (next_execution),
    INDEX (status, next_execution)
);

-- =====================================================
-- TABLE: customer_addresses (adresses étendues avec géolocalisation)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_addresses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    address_type ENUM('billing', 'shipping', 'service', 'mailing', 'emergency', 'work', 'home', 'other') NOT NULL,
    label VARCHAR(100),
    address_line_1 VARCHAR(255) NOT NULL,
    address_line_2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state_province VARCHAR(100),
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(3) DEFAULT 'FR',
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    geocoded_at TIMESTAMP NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    delivery_instructions TEXT,
    access_code VARCHAR(50),
    contact_name VARCHAR(255),
    contact_phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX (customer_id, address_type),
    INDEX (postal_code),
    INDEX (latitude, longitude),
    INDEX (is_primary, is_verified)
);

-- =====================================================
-- TABLE: customer_programs (programmes de fidélité)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_programs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    program_type ENUM('loyalty', 'subscription', 'maintenance', 'warranty', 'vip', 'corporate', 'referral') NOT NULL,
    program_name VARCHAR(100) NOT NULL,
    status ENUM('active', 'inactive', 'suspended', 'expired', 'pending') DEFAULT 'active',
    tier_level ENUM('bronze', 'silver', 'gold', 'platinum', 'diamond') DEFAULT 'bronze',
    points_balance INT DEFAULT 0,
    points_lifetime INT DEFAULT 0,
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    last_activity_at TIMESTAMP NULL,
    benefits JSON,
    restrictions JSON,
    notes TEXT,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX (customer_id, program_type),
    INDEX (program_type, status),
    INDEX (tier_level, status),
    INDEX (expires_at)
);

-- =====================================================
-- TABLE: customer_loyalty_transactions (transactions fidélité)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_loyalty_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    program_id INT NOT NULL,
    transaction_type ENUM('earned', 'redeemed', 'expired', 'adjusted', 'bonus', 'penalty') NOT NULL,
    points INT NOT NULL,
    balance_before INT NOT NULL,
    balance_after INT NOT NULL,
    reference_type ENUM('work_order', 'invoice', 'referral', 'review', 'signup', 'manual') NULL,
    reference_id INT NULL,
    description TEXT,
    processed_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (program_id) REFERENCES customer_programs(id) ON DELETE CASCADE,
    FOREIGN KEY (processed_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX (customer_id, created_at),
    INDEX (program_id, created_at),
    INDEX (transaction_type, created_at)
);

-- =====================================================
-- TABLE: customer_segments (segmentation client)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_segments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    segment_type ENUM('demographic', 'behavioral', 'geographic', 'psychographic', 'value', 'lifecycle', 'custom') NOT NULL,
    criteria JSON,
    color VARCHAR(7) DEFAULT '#007bff',
    is_active BOOLEAN DEFAULT TRUE,
    auto_update BOOLEAN DEFAULT FALSE,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX (segment_type, is_active),
    INDEX (name)
);

-- =====================================================
-- TABLE: customer_segment_memberships (appartenance aux segments)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_segment_memberships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    segment_id INT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (segment_id) REFERENCES customer_segments(id) ON DELETE CASCADE,
    UNIQUE KEY unique_membership (customer_id, segment_id),
    INDEX (customer_id),
    INDEX (segment_id),
    INDEX (expires_at)
);

-- =====================================================
-- TABLE: customer_tags (tags personnalisés)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    tag VARCHAR(50) NOT NULL,
    color VARCHAR(7) DEFAULT '#6c757d',
    added_by INT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (added_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY unique_customer_tag (customer_id, tag),
    INDEX (tag),
    INDEX (customer_id)
);

-- =====================================================
-- TABLE: vehicle_warranties (garanties véhicules)
-- =====================================================

CREATE TABLE IF NOT EXISTS vehicle_warranties (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id INT NOT NULL,
    warranty_type ENUM('manufacturer', 'extended', 'powertrain', 'emission', 'corrosion', 'paint', 'tire', 'battery', 'hybrid', 'custom') NOT NULL,
    provider VARCHAR(100),
    policy_number VARCHAR(100),
    coverage_description TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    mileage_limit INT,
    deductible DECIMAL(8,2) DEFAULT 0.00,
    coverage_amount DECIMAL(12,2),
    is_active BOOLEAN DEFAULT TRUE,
    terms_conditions TEXT,
    contact_info JSON,
    
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
    INDEX (vehicle_id, warranty_type),
    INDEX (end_date, is_active),
    INDEX (policy_number)
);

-- =====================================================
-- TABLE: vehicle_maintenance_schedules (calendriers maintenance)
-- =====================================================

CREATE TABLE IF NOT EXISTS vehicle_maintenance_schedules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id INT NOT NULL,
    service_type VARCHAR(100) NOT NULL,
    interval_type ENUM('mileage', 'time', 'both') NOT NULL,
    interval_value INT NOT NULL,
    interval_unit ENUM('km', 'miles', 'days', 'weeks', 'months', 'years') NOT NULL,
    last_service_date DATE,
    last_service_mileage INT,
    next_service_date DATE,
    next_service_mileage INT,
    is_critical BOOLEAN DEFAULT FALSE,
    auto_schedule BOOLEAN DEFAULT TRUE,
    notes TEXT,
    
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
    INDEX (vehicle_id, service_type),
    INDEX (next_service_date),
    INDEX (next_service_mileage),
    INDEX (is_critical, auto_schedule)
);

-- =====================================================
-- TABLE: customer_audit_log (journal d'audit)
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    action_type ENUM('create', 'update', 'delete', 'merge', 'export', 'import', 'login', 'consent_change', 'document_access', 'financial_change') NOT NULL,
    action_data JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    performed_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (performed_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX (customer_id, created_at),
    INDEX (action_type, created_at),
    INDEX (performed_by, created_at)
);

-- =====================================================
-- VUES POUR REPORTING ET ANALYTICS
-- =====================================================

-- Vue: Résumé Client 360
CREATE OR REPLACE VIEW customer_360_summary AS
SELECT 
    c.id,
    c.name,
    c.email,
    c.phone,
    c.company,
    c.status,
    c.created_at as customer_since,
    
    -- Véhicules
    COUNT(DISTINCT v.id) as total_vehicles,
    
    -- Interventions
    COUNT(DISTINCT wo.id) as total_work_orders,
    SUM(CASE WHEN wo.status = 'open' THEN 1 ELSE 0 END) as open_work_orders,
    MAX(wo.scheduled_date) as last_service_date,
    
    -- Finances
    COALESCE(cf.credit_limit, 0) as credit_limit,
    COALESCE(cf.risk_score, 50) as risk_score,
    
    -- Programmes
    COUNT(DISTINCT cp.id) as active_programs,
    COALESCE(SUM(cp.points_balance), 0) as total_points,
    
    -- Consentements
    COUNT(DISTINCT cc.id) as active_consents,
    
    -- Documents
    COUNT(DISTINCT cd.id) as total_documents,
    SUM(CASE WHEN cd.is_signed = 1 THEN 1 ELSE 0 END) as signed_documents,
    
    -- Activité récente
    MAX(ca.created_at) as last_activity_date
    
FROM customers c
LEFT JOIN vehicles v ON c.id = v.customer_id
LEFT JOIN work_orders wo ON v.id = wo.vehicle_id
LEFT JOIN customer_finances cf ON c.id = cf.customer_id
LEFT JOIN customer_programs cp ON c.id = cp.customer_id AND cp.status = 'active'
LEFT JOIN customer_consents cc ON c.id = cc.customer_id AND cc.is_active = 1
LEFT JOIN customer_documents cd ON c.id = cd.customer_id
LEFT JOIN customer_activity ca ON c.id = ca.customer_id
WHERE c.status != 'deleted'
GROUP BY c.id, c.name, c.email, c.phone, c.company, c.status, c.created_at, cf.credit_limit, cf.risk_score;

-- =====================================================
-- TRIGGERS POUR AUTOMATISATION
-- =====================================================

-- Trigger: Log automatique lors de modifications client
DELIMITER $$
CREATE TRIGGER customer_audit_trigger 
AFTER UPDATE ON customers
FOR EACH ROW
BEGIN
    INSERT INTO customer_audit_log (customer_id, action_type, action_data, performed_by, created_at)
    VALUES (NEW.id, 'update', JSON_OBJECT(
        'old_values', JSON_OBJECT('name', OLD.name, 'email', OLD.email, 'phone', OLD.phone, 'status', OLD.status),
        'new_values', JSON_OBJECT('name', NEW.name, 'email', NEW.email, 'phone', NEW.phone, 'status', NEW.status)
    ), @current_user_id, NOW());
END$$
DELIMITER ;

-- Trigger: Mise à jour automatique de l'activité client
DELIMITER $$
CREATE TRIGGER customer_activity_on_work_order 
AFTER INSERT ON work_orders
FOR EACH ROW
BEGIN
    INSERT INTO customer_activity (customer_id, activity_type, title, description, related_id, related_table, created_at)
    VALUES (
        (SELECT customer_id FROM vehicles WHERE id = NEW.vehicle_id),
        'work_order',
        CONCAT('Nouvelle intervention: ', COALESCE(NEW.title, 'Sans titre')),
        CONCAT('Statut: ', NEW.status, ', Priorité: ', COALESCE(NEW.priority, 'normal')),
        NEW.id,
        'work_orders',
        NOW()
    );
END$$
DELIMITER ;

-- =====================================================
-- PROCÉDURES STOCKÉES UTILITAIRES
-- =====================================================

-- Procédure: Calcul du score de risque client
DELIMITER $$
CREATE PROCEDURE CalculateCustomerRiskScore(IN customer_id INT)
BEGIN
    DECLARE risk_score INT DEFAULT 50;
    DECLARE overdue_amount DECIMAL(12,2) DEFAULT 0;
    DECLARE days_overdue INT DEFAULT 0;
    DECLARE payment_history_score INT DEFAULT 85;
    
    -- Calculer le montant en retard
    SELECT COALESCE(SUM(total_amount), 0) INTO overdue_amount
    FROM invoices 
    WHERE customer_id = customer_id 
    AND status IN ('open', 'sent') 
    AND due_date < CURDATE();
    
    -- Calculer les jours de retard maximum
    SELECT COALESCE(MAX(DATEDIFF(CURDATE(), due_date)), 0) INTO days_overdue
    FROM invoices 
    WHERE customer_id = customer_id 
    AND status IN ('open', 'sent') 
    AND due_date < CURDATE();
    
    -- Calcul du score de risque
    SET risk_score = LEAST(100, GREATEST(0, 
        (days_overdue * 2) + 
        (overdue_amount / 1000 * 10)
    ));
    
    -- Mettre à jour le score dans customer_finances
    INSERT INTO customer_finances (customer_id, risk_score, updated_at)
    VALUES (customer_id, risk_score, NOW())
    ON DUPLICATE KEY UPDATE 
    risk_score = VALUES(risk_score),
    updated_at = NOW();
    
    SELECT risk_score;
END$$
DELIMITER ;

-- Procédure: Nettoyage des données obsolètes
DELIMITER $$
CREATE PROCEDURE CleanupObsoleteData()
BEGIN
    -- Supprimer les logs d'audit de plus de 2 ans
    DELETE FROM customer_audit_log 
    WHERE created_at < DATE_SUB(NOW(), INTERVAL 2 YEAR);
    
    -- Supprimer les logs d'accès documents de plus de 1 an
    DELETE FROM customer_document_access_log 
    WHERE accessed_at < DATE_SUB(NOW(), INTERVAL 1 YEAR);
    
    -- Archiver les automations complétées de plus de 6 mois
    UPDATE customer_automations 
    SET status = 'archived' 
    WHERE status = 'completed' 
    AND updated_at < DATE_SUB(NOW(), INTERVAL 6 MONTH);
    
    SELECT 'Nettoyage terminé' as result;
END$$
DELIMITER ;

-- =====================================================
-- INSERTION DE DONNÉES DE RÉFÉRENCE
-- =====================================================

-- Segments par défaut
INSERT IGNORE INTO customer_segments (name, description, segment_type, criteria, color, is_active) VALUES
('Nouveaux Clients', 'Clients créés dans les 30 derniers jours', 'lifecycle', '{"days_since_creation": "<=30"}', '#28a745', 1),
('Clients VIP', 'Clients avec plus de 10 véhicules ou CA > 50k€', 'value', '{"vehicles_count": ">10", "annual_revenue": ">50000"}', '#ffc107', 1),
('Clients Inactifs', 'Aucune activité depuis 6 mois', 'behavioral', '{"days_since_last_activity": ">180"}', '#dc3545', 1),
('Entreprises', 'Clients avec nom d\'entreprise', 'demographic', '{"has_company": true}', '#007bff', 1),
('Particuliers', 'Clients particuliers', 'demographic', '{"has_company": false}', '#6f42c1', 1);

-- Règles d'automatisation par défaut
INSERT IGNORE INTO automation_rules (name, description, rule_type, trigger_event, conditions, actions, applies_to, is_active) VALUES
('Bienvenue Nouveau Client', 'Email de bienvenue automatique', 'email', 'customer_created', '{"delay_hours": 1}', '{"template": "welcome_email", "send_to": "customer"}', 'customer', 1),
('Rappel Facture Échue', 'Rappel automatique 7 jours après échéance', 'email', 'invoice_overdue', '{"days_overdue": 7}', '{"template": "payment_reminder", "send_to": "customer"}', 'customer', 1),
('Notification Paiement Reçu', 'Confirmation de réception de paiement', 'email', 'payment_received', '{}', '{"template": "payment_confirmation", "send_to": "customer"}', 'customer', 1);

-- Réactiver les vérifications de clés étrangères
SET FOREIGN_KEY_CHECKS = 1;

-- Message de fin
SELECT 'Migration Sprint 5-6 terminée avec succès!' as status;
