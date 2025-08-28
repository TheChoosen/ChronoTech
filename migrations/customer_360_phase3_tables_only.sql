-- Phase 3 - Customer 360 Database Schema - Tables uniquement
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
    
    INDEX idx_customer_preferences_customer_id (customer_id),
    INDEX idx_customer_preferences_category (preference_category),
    INDEX idx_customer_preferences_key (preference_key),
    UNIQUE KEY uk_customer_preferences_customer_key (customer_id, preference_category, preference_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
