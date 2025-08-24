-- Phase 3 - Customer 360 Database Schema
-- Création des tables pour le système Customer 360 avancé

-- Table des activités clients pour la timeline
CREATE TABLE IF NOT EXISTS customer_activities (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    activity_type ENUM('workorder', 'invoice', 'payment', 'quote', 'email', 'sms', 'call', 'document', 'appointment', 'note', 'consent', 'login', 'update') DEFAULT 'note',
    title VARCHAR(255) NOT NULL,
    description TEXT,
    reference_id INT NULL COMMENT 'ID de référence vers la table source (work_order, invoice, etc.)',
    reference_type VARCHAR(50) NULL COMMENT 'Type de référence (work_orders, invoices, etc.)',
    reference_data JSON NULL COMMENT 'Données supplémentaires en JSON',
    actor_id INT NULL COMMENT 'ID de l\'utilisateur qui a créé l\'activité',
    actor_name VARCHAR(255) NULL COMMENT 'Nom de l\'acteur',
    actor_type ENUM('user', 'system', 'customer', 'technician') DEFAULT 'system',
    status ENUM('pending', 'completed', 'cancelled', 'failed') DEFAULT 'completed',
    priority ENUM('low', 'normal', 'high', 'urgent') DEFAULT 'normal',
    tags JSON NULL COMMENT 'Tags associés à l\'activité',
    metadata JSON NULL COMMENT 'Métadonnées supplémentaires',
    is_visible BOOLEAN DEFAULT TRUE COMMENT 'Activité visible dans la timeline',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_activities_customer_id (customer_id),
    INDEX idx_customer_activities_type (activity_type),
    INDEX idx_customer_activities_created (created_at),
    INDEX idx_customer_activities_reference (reference_type, reference_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table des documents clients avancée
CREATE TABLE IF NOT EXISTS customer_documents (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL DEFAULT 0,
    mime_type VARCHAR(100) NOT NULL,
    document_type ENUM('contract', 'invoice', 'quote', 'photo', 'plan', 'certificate', 'warranty', 'identity', 'other') DEFAULT 'other',
    category VARCHAR(100) NULL,
    description TEXT NULL,
    tags JSON NULL,
    is_signed BOOLEAN DEFAULT FALSE,
    is_confidential BOOLEAN DEFAULT FALSE,
    access_level ENUM('public', 'internal', 'confidential', 'restricted') DEFAULT 'internal',
    signed_at TIMESTAMP NULL,
    signed_by VARCHAR(255) NULL,
    signature_data JSON NULL COMMENT 'Données de signature électronique',
    version_number INT DEFAULT 1,
    parent_document_id INT NULL COMMENT 'Document parent pour les versions',
    checksum_sha256 VARCHAR(64) NULL COMMENT 'Empreinte SHA-256 pour vérification',
    download_count INT DEFAULT 0,
    last_accessed_at TIMESTAMP NULL,
    expires_at TIMESTAMP NULL,
    created_by_id INT NULL,
    created_by_name VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_document_id) REFERENCES customer_documents(id) ON DELETE SET NULL,
    INDEX idx_customer_documents_customer_id (customer_id),
    INDEX idx_customer_documents_type (document_type),
    INDEX idx_customer_documents_category (category),
    INDEX idx_customer_documents_created (created_at),
    INDEX idx_customer_documents_access (access_level),
    UNIQUE KEY uk_customer_documents_path (file_path)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table des analytics et métriques clients
CREATE TABLE IF NOT EXISTS customer_analytics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,4) NOT NULL DEFAULT 0,
    metric_type ENUM('revenue', 'frequency', 'recency', 'satisfaction', 'loyalty', 'engagement', 'conversion') DEFAULT 'engagement',
    period_type ENUM('daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'lifetime') DEFAULT 'monthly',
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    metadata JSON NULL COMMENT 'Données supplémentaires pour le calcul',
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE COMMENT 'Version actuelle de la métrique',
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_analytics_customer_id (customer_id),
    INDEX idx_customer_analytics_metric (metric_name),
    INDEX idx_customer_analytics_type (metric_type),
    INDEX idx_customer_analytics_period (period_start, period_end),
    INDEX idx_customer_analytics_current (is_current),
    UNIQUE KEY uk_customer_analytics_metric_period (customer_id, metric_name, period_start, period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table des scores RFM clients
CREATE TABLE IF NOT EXISTS customer_rfm_scores (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    recency_score INT NOT NULL DEFAULT 1 COMMENT 'Score de récence (1-5)',
    frequency_score INT NOT NULL DEFAULT 1 COMMENT 'Score de fréquence (1-5)',
    monetary_score INT NOT NULL DEFAULT 1 COMMENT 'Score monétaire (1-5)',
    rfm_segment VARCHAR(50) NOT NULL DEFAULT 'New Customer',
    segment_description TEXT NULL,
    last_order_date DATE NULL,
    total_orders INT DEFAULT 0,
    total_revenue DECIMAL(12,2) DEFAULT 0.00,
    avg_order_value DECIMAL(10,2) DEFAULT 0.00,
    days_since_last_order INT NULL,
    predicted_clv DECIMAL(12,2) NULL COMMENT 'Customer Lifetime Value prédit',
    risk_score DECIMAL(3,2) DEFAULT 0.00 COMMENT 'Score de risque de churn (0-1)',
    loyalty_tier ENUM('bronze', 'silver', 'gold', 'platinum', 'diamond') NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    next_calculation_due DATE NULL,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_rfm_customer_id (customer_id),
    INDEX idx_customer_rfm_segment (rfm_segment),
    INDEX idx_customer_rfm_scores (recency_score, frequency_score, monetary_score),
    INDEX idx_customer_rfm_loyalty (loyalty_tier),
    UNIQUE KEY uk_customer_rfm_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table des consentements RGPD
CREATE TABLE IF NOT EXISTS customer_consents (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    consent_type ENUM('email_marketing', 'sms_marketing', 'phone_marketing', 'data_processing', 'data_sharing', 'analytics', 'cookies', 'newsletter') NOT NULL,
    is_granted BOOLEAN NOT NULL DEFAULT FALSE,
    granted_at TIMESTAMP NULL,
    revoked_at TIMESTAMP NULL,
    source ENUM('registration', 'update', 'api', 'import', 'manual') DEFAULT 'manual',
    ip_address VARCHAR(45) NULL COMMENT 'Adresse IP lors du consentement',
    user_agent TEXT NULL COMMENT 'User agent lors du consentement',
    legal_basis ENUM('consent', 'contract', 'legal_obligation', 'vital_interests', 'public_task', 'legitimate_interests') DEFAULT 'consent',
    purpose TEXT NULL COMMENT 'Finalité du traitement',
    retention_period INT NULL COMMENT 'Durée de conservation en jours',
    notes TEXT NULL,
    created_by_id INT NULL,
    created_by_name VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_consents_customer_id (customer_id),
    INDEX idx_customer_consents_type (consent_type),
    INDEX idx_customer_consents_granted (is_granted),
    INDEX idx_customer_consents_created (created_at),
    UNIQUE KEY uk_customer_consents_customer_type (customer_id, consent_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table des communications clients
CREATE TABLE IF NOT EXISTS customer_communications (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    communication_type ENUM('email', 'sms', 'phone', 'whatsapp', 'letter', 'in_person') NOT NULL,
    direction ENUM('inbound', 'outbound') NOT NULL,
    subject VARCHAR(255) NULL,
    content TEXT NULL,
    status ENUM('draft', 'sent', 'delivered', 'opened', 'clicked', 'replied', 'bounced', 'failed') DEFAULT 'draft',
    priority ENUM('low', 'normal', 'high', 'urgent') DEFAULT 'normal',
    template_used VARCHAR(100) NULL,
    sender_id INT NULL,
    sender_name VARCHAR(255) NULL,
    recipient_contact VARCHAR(255) NULL COMMENT 'Email, téléphone, etc.',
    delivery_attempted_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,
    opened_at TIMESTAMP NULL,
    clicked_at TIMESTAMP NULL,
    replied_at TIMESTAMP NULL,
    bounce_reason TEXT NULL,
    tracking_id VARCHAR(100) NULL COMMENT 'ID de suivi externe',
    metadata JSON NULL COMMENT 'Données supplémentaires (campaign_id, etc.)',
    cost DECIMAL(8,4) DEFAULT 0.0000 COMMENT 'Coût de la communication',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_communications_customer_id (customer_id),
    INDEX idx_customer_communications_type (communication_type),
    INDEX idx_customer_communications_status (status),
    INDEX idx_customer_communications_created (created_at),
    INDEX idx_customer_communications_tracking (tracking_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table des préférences clients
CREATE TABLE IF NOT EXISTS customer_preferences (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    preference_category VARCHAR(100) NOT NULL COMMENT 'communication, service, billing, etc.',
    preference_key VARCHAR(100) NOT NULL,
    preference_value TEXT NULL,
    preference_type ENUM('string', 'number', 'boolean', 'json', 'date') DEFAULT 'string',
    is_encrypted BOOLEAN DEFAULT FALSE COMMENT 'Valeur chiffrée',
    source ENUM('default', 'customer', 'admin', 'system', 'import') DEFAULT 'customer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_preferences_customer_id (customer_id),
    INDEX idx_customer_preferences_category (preference_category),
    INDEX idx_customer_preferences_key (preference_key),
    UNIQUE KEY uk_customer_preferences_customer_key (customer_id, preference_category, preference_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Vues pour faciliter les requêtes Customer 360

-- Vue des statistiques clients complètes
CREATE OR REPLACE VIEW customer_360_stats AS
SELECT 
    c.id,
    c.name,
    c.email,
    c.customer_type,
    c.created_at as customer_since,
    c.is_active,
    c.status,
    
    -- Statistiques de base
    COALESCE(wo_stats.total_work_orders, 0) as total_work_orders,
    COALESCE(wo_stats.total_revenue, 0) as total_revenue,
    COALESCE(wo_stats.avg_order_value, 0) as avg_order_value,
    wo_stats.last_work_order_date,
    
    -- Véhicules
    COALESCE(v_stats.total_vehicles, 0) as total_vehicles,
    
    -- Documents
    COALESCE(doc_stats.total_documents, 0) as total_documents,
    COALESCE(doc_stats.signed_documents, 0) as signed_documents,
    
    -- Communications
    COALESCE(comm_stats.total_communications, 0) as total_communications,
    COALESCE(comm_stats.last_communication, NULL) as last_communication,
    
    -- RFM Score
    rfm.rfm_segment,
    rfm.loyalty_tier,
    rfm.risk_score,
    
    -- Activité récente
    act_stats.last_activity_date,
    COALESCE(act_stats.activities_last_30days, 0) as activities_last_30days

FROM customers c

-- Work Orders Statistics
LEFT JOIN (
    SELECT 
        customer_id,
        COUNT(*) as total_work_orders,
        SUM(COALESCE(actual_cost, estimated_cost, 0)) as total_revenue,
        AVG(COALESCE(actual_cost, estimated_cost, 0)) as avg_order_value,
        MAX(COALESCE(completion_date, scheduled_date)) as last_work_order_date
    FROM work_orders 
    WHERE status != 'cancelled'
    GROUP BY customer_id
) wo_stats ON c.id = wo_stats.customer_id

-- Vehicles Statistics  
LEFT JOIN (
    SELECT 
        customer_id,
        COUNT(*) as total_vehicles
    FROM vehicles
    GROUP BY customer_id
) v_stats ON c.id = v_stats.customer_id

-- Documents Statistics
LEFT JOIN (
    SELECT 
        customer_id,
        COUNT(*) as total_documents,
        SUM(CASE WHEN is_signed = 1 THEN 1 ELSE 0 END) as signed_documents
    FROM customer_documents
    GROUP BY customer_id
) doc_stats ON c.id = doc_stats.customer_id

-- Communications Statistics
LEFT JOIN (
    SELECT 
        customer_id,
        COUNT(*) as total_communications,
        MAX(created_at) as last_communication
    FROM customer_communications
    GROUP BY customer_id
) comm_stats ON c.id = comm_stats.customer_id

-- RFM Scores
LEFT JOIN customer_rfm_scores rfm ON c.id = rfm.customer_id

-- Activities Statistics
LEFT JOIN (
    SELECT 
        customer_id,
        MAX(created_at) as last_activity_date,
        SUM(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as activities_last_30days
    FROM customer_activities
    WHERE is_visible = 1
    GROUP BY customer_id
) act_stats ON c.id = act_stats.customer_id;

-- Insérer quelques données de test pour les activités
INSERT IGNORE INTO customer_activities (customer_id, activity_type, title, description, actor_type, actor_name, metadata)
SELECT 
    id as customer_id,
    'note' as activity_type,
    CONCAT('Client créé: ', name) as title,
    'Nouveau client ajouté au système ChronoTech' as description,
    'system' as actor_type,
    'ChronoTech System' as actor_name,
    JSON_OBJECT('source', 'system', 'customer_type', customer_type) as metadata
FROM customers 
WHERE id NOT IN (SELECT DISTINCT customer_id FROM customer_activities WHERE activity_type = 'note' AND title LIKE 'Client créé:%');

-- Insérer des activités basées sur les work_orders existants
INSERT IGNORE INTO customer_activities (customer_id, activity_type, title, description, reference_id, reference_type, actor_type, actor_name, created_at, metadata)
SELECT 
    wo.customer_id,
    'workorder' as activity_type,
    CONCAT('Intervention: ', wo.description) as title,
    CONCAT('Bon de travail #', wo.id, ' - ', wo.description, ' (', wo.status, ')') as description,
    wo.id as reference_id,
    'work_orders' as reference_type,
    'system' as actor_type,
    'ChronoTech System' as actor_name,
    wo.created_at as created_at,
    JSON_OBJECT(
        'work_order_id', wo.id,
        'status', wo.status,
        'amount', COALESCE(wo.actual_cost, wo.estimated_cost, 0),
        'priority', wo.priority
    ) as metadata
FROM work_orders wo
WHERE wo.id NOT IN (SELECT DISTINCT reference_id FROM customer_activities WHERE reference_type = 'work_orders' AND reference_id IS NOT NULL);

-- Créer des consentements par défaut pour les clients existants
INSERT IGNORE INTO customer_consents (customer_id, consent_type, is_granted, granted_at, source, legal_basis, purpose)
SELECT 
    id as customer_id,
    'data_processing' as consent_type,
    TRUE as is_granted,
    created_at as granted_at,
    'registration' as source,
    'contract' as legal_basis,
    'Traitement des données dans le cadre de la relation contractuelle' as purpose
FROM customers;

-- Calculer des scores RFM de base pour les clients existants
INSERT IGNORE INTO customer_rfm_scores (
    customer_id, 
    recency_score, 
    frequency_score, 
    monetary_score, 
    rfm_segment,
    last_order_date,
    total_orders,
    total_revenue,
    avg_order_value,
    days_since_last_order,
    loyalty_tier
)
SELECT 
    c.id as customer_id,
    CASE 
        WHEN DATEDIFF(NOW(), COALESCE(MAX(COALESCE(wo.completion_date, wo.scheduled_date)), c.created_at)) <= 30 THEN 5
        WHEN DATEDIFF(NOW(), COALESCE(MAX(COALESCE(wo.completion_date, wo.scheduled_date)), c.created_at)) <= 90 THEN 4
        WHEN DATEDIFF(NOW(), COALESCE(MAX(COALESCE(wo.completion_date, wo.scheduled_date)), c.created_at)) <= 180 THEN 3
        WHEN DATEDIFF(NOW(), COALESCE(MAX(COALESCE(wo.completion_date, wo.scheduled_date)), c.created_at)) <= 365 THEN 2
        ELSE 1
    END as recency_score,
    CASE 
        WHEN COUNT(wo.id) >= 10 THEN 5
        WHEN COUNT(wo.id) >= 5 THEN 4
        WHEN COUNT(wo.id) >= 3 THEN 3
        WHEN COUNT(wo.id) >= 1 THEN 2
        ELSE 1
    END as frequency_score,
    CASE 
        WHEN COALESCE(SUM(COALESCE(wo.actual_cost, wo.estimated_cost, 0)), 0) >= 10000 THEN 5
        WHEN COALESCE(SUM(COALESCE(wo.actual_cost, wo.estimated_cost, 0)), 0) >= 5000 THEN 4
        WHEN COALESCE(SUM(COALESCE(wo.actual_cost, wo.estimated_cost, 0)), 0) >= 1000 THEN 3
        WHEN COALESCE(SUM(COALESCE(wo.actual_cost, wo.estimated_cost, 0)), 0) >= 100 THEN 2
        ELSE 1
    END as monetary_score,
    CASE 
        WHEN COUNT(wo.id) = 0 THEN 'New Customer'
        WHEN COUNT(wo.id) >= 5 AND COALESCE(SUM(COALESCE(wo.actual_cost, wo.estimated_cost, 0)), 0) >= 5000 THEN 'Champions'
        WHEN COUNT(wo.id) >= 3 AND COALESCE(SUM(COALESCE(wo.actual_cost, wo.estimated_cost, 0)), 0) >= 1000 THEN 'Loyal Customers'
        WHEN DATEDIFF(NOW(), COALESCE(MAX(COALESCE(wo.completion_date, wo.scheduled_date)), c.created_at)) <= 90 THEN 'Potential Loyalists'
        WHEN DATEDIFF(NOW(), COALESCE(MAX(COALESCE(wo.completion_date, wo.scheduled_date)), c.created_at)) > 365 THEN 'At Risk'
        ELSE 'Regular Customers'
    END as rfm_segment,
    MAX(COALESCE(wo.completion_date, wo.scheduled_date)) as last_order_date,
    COUNT(wo.id) as total_orders,
    COALESCE(SUM(COALESCE(wo.actual_cost, wo.estimated_cost, 0)), 0) as total_revenue,
    CASE WHEN COUNT(wo.id) > 0 THEN COALESCE(SUM(COALESCE(wo.actual_cost, wo.estimated_cost, 0)), 0) / COUNT(wo.id) ELSE 0 END as avg_order_value,
    DATEDIFF(NOW(), COALESCE(MAX(COALESCE(wo.completion_date, wo.scheduled_date)), c.created_at)) as days_since_last_order,
    CASE 
        WHEN COALESCE(SUM(COALESCE(wo.actual_cost, wo.estimated_cost, 0)), 0) >= 10000 THEN 'platinum'
        WHEN COALESCE(SUM(COALESCE(wo.actual_cost, wo.estimated_cost, 0)), 0) >= 5000 THEN 'gold'
        WHEN COALESCE(SUM(COALESCE(wo.actual_cost, wo.estimated_cost, 0)), 0) >= 1000 THEN 'silver'
        ELSE 'bronze'
    END as loyalty_tier
FROM customers c
LEFT JOIN work_orders wo ON c.id = wo.customer_id AND wo.status != 'cancelled'
GROUP BY c.id;
