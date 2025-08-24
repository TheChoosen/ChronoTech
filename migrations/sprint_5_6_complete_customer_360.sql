-- Migration Sprint 5-6: Customer 360 Complete
-- Ajout des tables manquantes pour un système client complet

-- =====================================================
-- 1. TIMELINE UNIFIÉE ET COMMUNICATIONS
-- =====================================================

-- Table pour traquer les communications clients (emails, SMS, appels)
CREATE TABLE IF NOT EXISTS customer_communications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    communication_type ENUM('email', 'sms', 'call', 'letter', 'chat') NOT NULL,
    direction ENUM('inbound', 'outbound') NOT NULL,
    channel VARCHAR(50) NOT NULL, -- smtp, twillio, phone_system, etc.
    subject VARCHAR(255),
    content TEXT,
    recipient_address VARCHAR(255), -- email ou numéro téléphone
    status ENUM('pending', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'failed') NOT NULL DEFAULT 'pending',
    sent_at DATETIME,
    delivered_at DATETIME,
    opened_at DATETIME,
    clicked_at DATETIME,
    failed_reason TEXT,
    tracking_id VARCHAR(255), -- ID de tracking externe (Mailgun, Twilio, etc.)
    sent_by INT, -- Utilisateur qui a envoyé
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (sent_by) REFERENCES users(id),
    INDEX (customer_id, communication_type),
    INDEX (status, sent_at),
    INDEX (tracking_id)
);

-- Extension de la table customer_activity pour plus de métadonnées
ALTER TABLE customer_activity 
ADD COLUMN IF NOT EXISTS priority ENUM('low', 'normal', 'high', 'urgent') DEFAULT 'normal',
ADD COLUMN IF NOT EXISTS visibility ENUM('public', 'internal', 'private') DEFAULT 'internal',
ADD COLUMN IF NOT EXISTS tags JSON,
ADD COLUMN IF NOT EXISTS attachments JSON;

-- =====================================================
-- 2. CONSENTEMENTS RGPD/LOI 25 AVANCÉS
-- =====================================================

-- Table principale des consentements
CREATE TABLE IF NOT EXISTS customer_consents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    consent_type ENUM('marketing_email', 'marketing_sms', 'analytics', 'profiling', 'data_sharing', 'service_notifications', 'location_tracking') NOT NULL,
    purpose TEXT NOT NULL, -- Description détaillée de l'utilisation
    is_granted BOOLEAN NOT NULL DEFAULT FALSE,
    source VARCHAR(100) NOT NULL, -- 'web_form', 'import', 'phone', 'in_person', 'api'
    source_details JSON, -- Détails sur la source (IP, user agent, etc.)
    collected_by INT,
    version INT NOT NULL DEFAULT 1,
    granted_at DATETIME,
    revoked_at DATETIME,
    expires_at DATETIME,
    legal_basis ENUM('consent', 'contract', 'legal_obligation', 'vital_interests', 'public_task', 'legitimate_interests') DEFAULT 'consent',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (collected_by) REFERENCES users(id),
    UNIQUE KEY unique_consent (customer_id, consent_type, version),
    INDEX (customer_id, consent_type),
    INDEX (expires_at)
);

-- Historique complet des consentements pour audit
CREATE TABLE IF NOT EXISTS customer_consent_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    consent_id INT,
    customer_id INT NOT NULL,
    consent_type VARCHAR(50) NOT NULL,
    is_granted BOOLEAN NOT NULL,
    source VARCHAR(100) NOT NULL,
    source_details JSON,
    collected_by INT,
    version INT NOT NULL,
    action VARCHAR(20) NOT NULL, -- 'grant', 'revoke', 'expire', 'modify'
    action_timestamp DATETIME NOT NULL,
    legal_basis VARCHAR(50),
    retention_until DATETIME, -- Date de suppression prévue selon RGPD
    FOREIGN KEY (consent_id) REFERENCES customer_consents(id) ON DELETE SET NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX (customer_id, consent_type),
    INDEX (action_timestamp),
    INDEX (retention_until)
);

-- =====================================================
-- 3. DOCUMENTS ET SIGNATURES AVANCÉS
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    document_type ENUM('contract', 'invoice', 'id_proof', 'insurance', 'warranty', 'service_agreement', 'quote', 'other') NOT NULL,
    category VARCHAR(100), -- Catégorie personnalisée
    title VARCHAR(255) NOT NULL,
    description TEXT,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_size INT NOT NULL,
    mime_type VARCHAR(255) NOT NULL,
    hash_sha256 VARCHAR(64) NOT NULL,
    version INT DEFAULT 1,
    parent_document_id INT, -- Pour les versions de documents
    is_signed BOOLEAN DEFAULT FALSE,
    signed_at DATETIME,
    signature_provider VARCHAR(100), -- 'docusign', 'adobe_sign', 'internal', etc.
    signature_data JSON, -- Métadonnées de signature
    signature_certificate TEXT, -- Certificat de signature
    is_encrypted BOOLEAN DEFAULT FALSE,
    encryption_key_id VARCHAR(255),
    retention_until DATETIME, -- Date de suppression automatique
    access_restrictions JSON, -- Qui peut voir ce document
    created_by INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at DATETIME,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (parent_document_id) REFERENCES customer_documents(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX (customer_id, document_type),
    INDEX (hash_sha256),
    INDEX (retention_until),
    INDEX (expires_at)
);

-- Logs d'accès aux documents pour audit
CREATE TABLE IF NOT EXISTS customer_document_access_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    accessed_by INT,
    access_type ENUM('view', 'download', 'print', 'share', 'delete') NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES customer_documents(id),
    FOREIGN KEY (accessed_by) REFERENCES users(id),
    INDEX (document_id, accessed_at),
    INDEX (accessed_by, accessed_at)
);

-- =====================================================
-- 4. FINANCES CLIENT COMPLÈTES
-- =====================================================

-- Profil financier principal
CREATE TABLE IF NOT EXISTS customer_finances (
    customer_id INT NOT NULL PRIMARY KEY,
    credit_limit DECIMAL(10, 2) DEFAULT 0.00,
    available_credit DECIMAL(10, 2) DEFAULT 0.00,
    payment_terms VARCHAR(50) DEFAULT 'net30', -- net15, net30, net60, cash, etc.
    price_tier VARCHAR(50) DEFAULT 'standard', -- standard, vip, wholesale, etc.
    discount_percent DECIMAL(5, 2) DEFAULT 0.00,
    currency_code CHAR(3) DEFAULT 'CAD',
    tax_exempt BOOLEAN DEFAULT FALSE,
    tax_exempt_reason VARCHAR(255),
    tax_exempt_number VARCHAR(100),
    tax_exempt_expires DATETIME,
    high_risk BOOLEAN DEFAULT FALSE,
    risk_score INT DEFAULT 0, -- Score de risque de 0 à 100
    risk_reason VARCHAR(255),
    credit_check_date DATETIME,
    credit_check_score INT,
    preferred_payment_method VARCHAR(50),
    auto_collection BOOLEAN DEFAULT TRUE,
    collection_priority ENUM('low', 'normal', 'high') DEFAULT 'normal',
    finance_contact_id INT, -- Contact préféré pour finances
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX (risk_score),
    INDEX (payment_terms),
    INDEX (price_tier)
);

-- Méthodes de paiement tokenisées
CREATE TABLE IF NOT EXISTS customer_payment_methods (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    provider ENUM('stripe', 'paypal', 'square', 'bank_transfer', 'check', 'cash', 'other') NOT NULL,
    provider_token VARCHAR(255), -- Token sécurisé du fournisseur
    method_type VARCHAR(50) NOT NULL, -- 'credit_card', 'debit_card', 'bank_account', 'digital_wallet'
    masked_number VARCHAR(50), -- 4 derniers chiffres ou identifiant masqué
    expiry_date VARCHAR(10),
    holder_name VARCHAR(255),
    billing_address_id INT, -- Référence à une adresse
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    verification_status ENUM('pending', 'verified', 'failed') DEFAULT 'pending',
    verification_date DATETIME,
    last_used_at DATETIME,
    failure_count INT DEFAULT 0,
    metadata JSON, -- Données spécifiques au provider
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX (customer_id, is_default),
    INDEX (provider, provider_token),
    INDEX (is_active, verification_status)
);

-- Historique des soldes et transactions
CREATE TABLE IF NOT EXISTS customer_balance_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    transaction_type ENUM('invoice', 'payment', 'credit', 'debit', 'adjustment', 'refund', 'chargeback') NOT NULL,
    reference_id INT, -- ID dans la table correspondante (invoices, payments, etc.)
    reference_table VARCHAR(50),
    amount DECIMAL(10, 2) NOT NULL,
    currency_code CHAR(3) DEFAULT 'CAD',
    balance_before DECIMAL(10, 2) NOT NULL,
    balance_after DECIMAL(10, 2) NOT NULL,
    description VARCHAR(255),
    processed_by INT, -- Utilisateur qui a traité
    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (processed_by) REFERENCES users(id),
    INDEX (customer_id, processed_at),
    INDEX (reference_table, reference_id),
    INDEX (transaction_type, processed_at)
);

-- =====================================================
-- 5. AUTOMATIONS ET RÈGLES MÉTIER
-- =====================================================

-- Règles d'automation configurables
CREATE TABLE IF NOT EXISTS automation_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    rule_type ENUM('maintenance', 'renewal', 'dunning', 'inactivity', 'loyalty', 'follow_up', 'upsell', 'custom') NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    priority INT DEFAULT 5, -- 1 = haute priorité, 10 = basse priorité
    conditions JSON NOT NULL, -- Conditions d'exécution
    actions JSON NOT NULL, -- Actions à exécuter
    applies_to ENUM('all', 'segment', 'customer_type', 'vehicle_type') NOT NULL,
    segment_filters JSON, -- Filtres pour définir qui est éligible
    frequency_limit INT DEFAULT 0, -- Limite d'exécutions par client (0 = illimité)
    cooldown_period INT DEFAULT 0, -- Période d'attente entre exécutions (en jours)
    start_date DATETIME,
    end_date DATETIME,
    created_by INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX (rule_type, is_active),
    INDEX (start_date, end_date)
);

-- Instances d'automation par client
CREATE TABLE IF NOT EXISTS customer_automations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    rule_id INT NOT NULL,
    vehicle_id INT, -- Automation spécifique à un véhicule
    trigger_event VARCHAR(100), -- Événement déclencheur
    next_execution DATETIME,
    last_execution DATETIME,
    execution_count INT DEFAULT 0,
    max_executions INT, -- Limite pour cette instance
    status ENUM('pending', 'active', 'completed', 'failed', 'paused', 'cancelled') DEFAULT 'pending',
    context_data JSON, -- Données contextuelles pour cette automation
    failure_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (rule_id) REFERENCES automation_rules(id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    INDEX (next_execution, status),
    INDEX (customer_id, status),
    INDEX (rule_id, last_execution)
);

-- Journal des exécutions d'automations
CREATE TABLE IF NOT EXISTS automation_executions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    automation_id INT NOT NULL,
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    action_type VARCHAR(100) NOT NULL, -- send_email, create_reminder, etc.
    action_details JSON,
    result_status ENUM('success', 'failure', 'partial', 'pending') DEFAULT 'pending',
    result_data JSON,
    execution_time_ms INT, -- Temps d'exécution en millisecondes
    error_message TEXT,
    FOREIGN KEY (automation_id) REFERENCES customer_automations(id),
    INDEX (automation_id, executed_at),
    INDEX (result_status, executed_at)
);

-- =====================================================
-- 6. ADRESSES AVANCÉES AVEC GÉOLOCALISATION
-- =====================================================

-- Extension de la table d'adresses existante (si elle existe)
-- Sinon création complète
CREATE TABLE IF NOT EXISTS customer_addresses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    type ENUM('billing', 'shipping', 'service', 'warehouse', 'emergency') NOT NULL,
    label VARCHAR(100), -- Nom convivial de l'adresse
    is_primary BOOLEAN DEFAULT FALSE,
    street VARCHAR(255) NOT NULL,
    street2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    province VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country CHAR(2) DEFAULT 'CA',
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    geo_accuracy VARCHAR(20), -- Précision du géocodage
    geo_provider VARCHAR(50), -- Fournisseur de géocodage
    delivery_window_start TIME,
    delivery_window_end TIME,
    delivery_days SET('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'),
    delivery_instructions TEXT,
    access_instructions TEXT,
    parking_instructions TEXT,
    service_zone VARCHAR(50),
    delivery_zone VARCHAR(50),
    special_requirements TEXT,
    contact_name VARCHAR(255), -- Contact sur site
    contact_phone VARCHAR(50),
    is_residential BOOLEAN DEFAULT TRUE,
    building_type ENUM('house', 'apartment', 'office', 'warehouse', 'shop', 'other'),
    floor_number VARCHAR(10),
    buzzer_code VARCHAR(20),
    security_code VARCHAR(50),
    landmark_nearby TEXT,
    validated_at DATETIME, -- Dernière validation de l'adresse
    validation_source VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX (customer_id, type),
    INDEX (latitude, longitude),
    INDEX (service_zone),
    INDEX (postal_code, city)
);

-- =====================================================
-- 7. VÉHICULES/ACTIFS ÉTENDUS
-- =====================================================

-- Extension de la table véhicules existante
-- Garanties et plans d'entretien
CREATE TABLE IF NOT EXISTS vehicle_warranties (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id INT NOT NULL,
    warranty_type ENUM('manufacturer', 'extended', 'service_contract', 'insurance') NOT NULL,
    provider VARCHAR(255) NOT NULL,
    policy_number VARCHAR(100),
    coverage_details TEXT,
    start_date DATE NOT NULL,
    end_date DATE,
    end_mileage INT, -- Kilométrage limite
    deductible DECIMAL(8, 2),
    coverage_amount DECIMAL(10, 2),
    is_active BOOLEAN DEFAULT TRUE,
    contact_info JSON, -- Informations de contact du fournisseur
    claim_instructions TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    INDEX (vehicle_id, is_active),
    INDEX (end_date, end_mileage)
);

-- Plans d'entretien
CREATE TABLE IF NOT EXISTS vehicle_maintenance_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id INT NOT NULL,
    plan_name VARCHAR(255) NOT NULL,
    plan_type ENUM('manufacturer', 'dealer', 'custom') NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    total_services INT,
    completed_services INT DEFAULT 0,
    next_service_due_km INT,
    next_service_due_date DATE,
    cost_per_service DECIMAL(8, 2),
    total_cost DECIMAL(10, 2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    INDEX (vehicle_id, is_active),
    INDEX (next_service_due_date, next_service_due_km)
);

-- Historique d'échanges et reprises
CREATE TABLE IF NOT EXISTS vehicle_trade_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id INT NOT NULL,
    trade_type ENUM('trade_in', 'trade_out', 'exchange', 'repossession', 'sale') NOT NULL,
    trade_date DATE NOT NULL,
    trade_partner VARCHAR(255), -- Nom du client/dealer avec qui l'échange a eu lieu
    trade_value DECIMAL(10, 2),
    trade_description TEXT,
    documentation JSON, -- Références aux documents liés
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    INDEX (vehicle_id, trade_date),
    INDEX (trade_type, trade_date)
);

-- Accessoires et compatibilités
CREATE TABLE IF NOT EXISTS vehicle_accessories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id INT NOT NULL,
    accessory_name VARCHAR(255) NOT NULL,
    accessory_type VARCHAR(100), -- roof_rack, towing, electronics, etc.
    manufacturer VARCHAR(255),
    part_number VARCHAR(100),
    installation_date DATE,
    installation_cost DECIMAL(8, 2),
    warranty_end_date DATE,
    is_removable BOOLEAN DEFAULT TRUE,
    removal_date DATE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    INDEX (vehicle_id, accessory_type),
    INDEX (installation_date, removal_date)
);

-- =====================================================
-- 8. PROGRAMMES ET RELATIONS CLIENT
-- =====================================================

-- Abonnements et forfaits
CREATE TABLE IF NOT EXISTS customer_subscriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    subscription_type VARCHAR(100) NOT NULL, -- maintenance, premium_support, etc.
    plan_name VARCHAR(255) NOT NULL,
    billing_frequency ENUM('monthly', 'quarterly', 'semi_annual', 'annual') NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency_code CHAR(3) DEFAULT 'CAD',
    start_date DATE NOT NULL,
    end_date DATE,
    next_billing_date DATE,
    auto_renew BOOLEAN DEFAULT TRUE,
    status ENUM('active', 'cancelled', 'suspended', 'expired') DEFAULT 'active',
    cancellation_reason TEXT,
    benefits JSON, -- Liste des avantages inclus
    usage_limits JSON, -- Limites d'utilisation si applicable
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX (customer_id, status),
    INDEX (next_billing_date, status)
);

-- Programme de fidélité et points
CREATE TABLE IF NOT EXISTS customer_loyalty (
    customer_id INT NOT NULL PRIMARY KEY,
    program_tier ENUM('bronze', 'silver', 'gold', 'platinum', 'vip') DEFAULT 'bronze',
    points_balance INT DEFAULT 0,
    points_lifetime_earned INT DEFAULT 0,
    points_lifetime_redeemed INT DEFAULT 0,
    tier_start_date DATE,
    tier_expires_date DATE,
    referral_code VARCHAR(20),
    referrals_count INT DEFAULT 0,
    special_offers_eligible BOOLEAN DEFAULT TRUE,
    vip_services_access BOOLEAN DEFAULT FALSE,
    dedicated_rep_id INT, -- Représentant dédié pour VIP
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (dedicated_rep_id) REFERENCES users(id),
    INDEX (program_tier, points_balance)
);

-- Historique des points de fidélité
CREATE TABLE IF NOT EXISTS customer_loyalty_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    transaction_type ENUM('earned', 'redeemed', 'expired', 'adjusted', 'bonus') NOT NULL,
    points_amount INT NOT NULL,
    reference_type VARCHAR(50), -- invoice, referral, bonus, etc.
    reference_id INT,
    description VARCHAR(255),
    balance_after INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX (customer_id, created_at),
    INDEX (reference_type, reference_id)
);

-- Relations avec partenaires
CREATE TABLE IF NOT EXISTS customer_partner_relationships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    partner_type ENUM('insurance', 'financing', 'dealer', 'fleet_manager', 'referrer') NOT NULL,
    partner_name VARCHAR(255) NOT NULL,
    relationship_type VARCHAR(100), -- agent, broker, manager, etc.
    contact_person VARCHAR(255),
    contact_info JSON,
    commission_rate DECIMAL(5, 2),
    commission_type ENUM('percentage', 'fixed', 'tiered'),
    is_active BOOLEAN DEFAULT TRUE,
    start_date DATE,
    end_date DATE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX (customer_id, partner_type),
    INDEX (partner_type, is_active)
);

-- =====================================================
-- 9. SÉCURITÉ ET CONFORMITÉ AVANCÉES
-- =====================================================

-- Droits d'accès granulaires aux données client
CREATE TABLE IF NOT EXISTS customer_access_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    user_id INT NOT NULL,
    permission_type ENUM('read', 'write', 'admin', 'finance', 'documents', 'communications') NOT NULL,
    granted_by INT NOT NULL,
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    is_active BOOLEAN DEFAULT TRUE,
    conditions JSON, -- Conditions supplémentaires d'accès
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (granted_by) REFERENCES users(id),
    UNIQUE KEY unique_permission (customer_id, user_id, permission_type),
    INDEX (user_id, permission_type, is_active),
    INDEX (expires_at)
);

-- Journal d'audit complet
CREATE TABLE IF NOT EXISTS customer_audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    record_id INT,
    action ENUM('create', 'read', 'update', 'delete', 'export', 'print') NOT NULL,
    field_changes JSON, -- Détail des champs modifiés
    old_values JSON,
    new_values JSON,
    user_id INT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    session_id VARCHAR(255),
    compliance_flags JSON, -- Marqueurs de conformité RGPD/Loi 25
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX (customer_id, action, created_at),
    INDEX (table_name, action, created_at),
    INDEX (user_id, created_at)
);

-- Demandes d'export/suppression RGPD
CREATE TABLE IF NOT EXISTS customer_data_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    request_type ENUM('export', 'delete', 'rectification', 'portability', 'restriction') NOT NULL,
    status ENUM('pending', 'processing', 'completed', 'rejected') DEFAULT 'pending',
    requested_by VARCHAR(255), -- Email/nom du demandeur
    verification_method VARCHAR(100),
    verification_completed_at DATETIME,
    processed_by INT,
    completed_at DATETIME,
    expiry_date DATETIME, -- Date limite de traitement légal
    export_file_path VARCHAR(512),
    export_format ENUM('json', 'csv', 'pdf', 'xml'),
    notes TEXT,
    legal_basis TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (processed_by) REFERENCES users(id),
    INDEX (customer_id, request_type),
    INDEX (status, expiry_date)
);

-- =====================================================
-- 10. KPIs ET ANALYSE CLIENT
-- =====================================================

-- Cache des métriques client pour performance
CREATE TABLE IF NOT EXISTS customer_metrics_cache (
    customer_id INT NOT NULL PRIMARY KEY,
    lifetime_value DECIMAL(12, 2) DEFAULT 0,
    total_spent DECIMAL(12, 2) DEFAULT 0,
    average_order_value DECIMAL(10, 2) DEFAULT 0,
    order_frequency DECIMAL(8, 4) DEFAULT 0, -- Commandes par mois
    last_order_date DATE,
    days_since_last_order INT DEFAULT 0,
    churn_risk_score INT DEFAULT 0, -- 0-100
    satisfaction_score DECIMAL(3, 2), -- NPS/CSAT moyen
    payment_behavior_score INT DEFAULT 50, -- Score de comportement de paiement
    referral_value DECIMAL(10, 2) DEFAULT 0,
    service_frequency DECIMAL(8, 4) DEFAULT 0, -- Services par mois
    complaint_count INT DEFAULT 0,
    compliment_count INT DEFAULT 0,
    cache_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    INDEX (lifetime_value),
    INDEX (churn_risk_score),
    INDEX (cache_updated_at)
);

-- Segments client automatiques basés sur RFM
CREATE TABLE IF NOT EXISTS customer_segments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    segment_type ENUM('manual', 'rfm', 'behavioral', 'demographic', 'predictive') NOT NULL,
    criteria JSON NOT NULL, -- Critères de qualification
    color VARCHAR(7), -- Couleur hex pour l'affichage
    priority INT DEFAULT 5,
    is_active BOOLEAN DEFAULT TRUE,
    auto_assign BOOLEAN DEFAULT FALSE, -- Assignation automatique
    created_by INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX (segment_type, is_active)
);

-- Appartenance aux segments
CREATE TABLE IF NOT EXISTS customer_segment_memberships (
    customer_id INT NOT NULL,
    segment_id INT NOT NULL,
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    assigned_by INT, -- NULL si automatique
    confidence_score DECIMAL(3, 2), -- Pour les segments automatiques
    expires_at DATETIME,
    PRIMARY KEY (customer_id, segment_id),
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (segment_id) REFERENCES customer_segments(id),
    FOREIGN KEY (assigned_by) REFERENCES users(id),
    INDEX (segment_id, assigned_at),
    INDEX (expires_at)
);

-- =====================================================
-- AMÉLIORATION DES TABLES EXISTANTES
-- =====================================================

-- Extension de la table customers existante
ALTER TABLE customers 
ADD COLUMN IF NOT EXISTS language_code CHAR(5) DEFAULT 'fr-CA',
ADD COLUMN IF NOT EXISTS timezone VARCHAR(64) DEFAULT 'America/Montreal',
ADD COLUMN IF NOT EXISTS preferred_communication_channel ENUM('email', 'sms', 'phone', 'mail', 'none') DEFAULT 'email',
ADD COLUMN IF NOT EXISTS communication_frequency ENUM('immediate', 'daily', 'weekly', 'monthly') DEFAULT 'immediate',
ADD COLUMN IF NOT EXISTS privacy_level ENUM('public', 'normal', 'restricted', 'confidential') DEFAULT 'normal',
ADD COLUMN IF NOT EXISTS data_retention_preference ENUM('minimum', 'standard', 'extended') DEFAULT 'standard',
ADD COLUMN IF NOT EXISTS marketing_opted_in BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS marketing_opted_in_date DATETIME,
ADD COLUMN IF NOT EXISTS last_activity_date DATETIME,
ADD COLUMN IF NOT EXISTS referral_source VARCHAR(255),
ADD COLUMN IF NOT EXISTS customer_since DATE,
ADD COLUMN IF NOT EXISTS tags JSON,
ADD COLUMN IF NOT EXISTS custom_fields JSON;

-- Index pour optimiser les performances
CREATE INDEX IF NOT EXISTS idx_customers_language_timezone ON customers(language_code, timezone);
CREATE INDEX IF NOT EXISTS idx_customers_communication ON customers(preferred_communication_channel, marketing_opted_in);
CREATE INDEX IF NOT EXISTS idx_customers_activity ON customers(last_activity_date, customer_since);

-- =====================================================
-- DONNÉES DE RÉFÉRENCE
-- =====================================================

-- Insérer quelques règles d'automation de base
INSERT IGNORE INTO automation_rules (name, rule_type, description, conditions, actions, applies_to, created_at) VALUES
('Rappel entretien véhicule', 'maintenance', 'Rappel automatique d\'entretien basé sur la date ou le kilométrage', 
 '{"triggers": [{"type": "vehicle_mileage", "operator": ">=", "value": 5000, "since": "last_service"}]}',
 '[{"action": "send_email", "template": "maintenance_reminder", "delay_days": 0}]',
 'all', NOW()),
 
('Relance facture impayée', 'dunning', 'Série de relances pour factures en retard',
 '{"triggers": [{"type": "invoice_overdue", "operator": ">=", "value": 7, "unit": "days"}]}',
 '[{"action": "send_email", "template": "payment_reminder", "delay_days": 0}, {"action": "create_task", "assignee": "account_manager", "delay_days": 14}]',
 'all', NOW()),
 
('Client inactif 6 mois', 'inactivity', 'Réactivation des clients inactifs',
 '{"triggers": [{"type": "last_order", "operator": ">=", "value": 180, "unit": "days"}]}',
 '[{"action": "send_email", "template": "winback_campaign", "delay_days": 0}]',
 'all', NOW());

-- Segments client de base
INSERT IGNORE INTO customer_segments (name, description, segment_type, criteria, color, auto_assign, created_at) VALUES
('VIP', 'Clients à haute valeur', 'manual', '{"lifetime_value": {"min": 10000}}', '#FFD700', FALSE, NOW()),
('Nouveaux clients', 'Clients de moins de 6 mois', 'behavioral', '{"customer_since": {"max_days": 180}}', '#4CAF50', TRUE, NOW()),
('À risque', 'Clients à risque de départ', 'predictive', '{"churn_risk_score": {"min": 70}}', '#F44336', TRUE, NOW()),
('Fidèles', 'Clients réguliers et fidèles', 'rfm', '{"recency": {"max": 90}, "frequency": {"min": 5}, "monetary": {"min": 5000}}', '#2196F3', TRUE, NOW());

-- Messages d'initialisation
SELECT 'Migration Sprint 5-6 terminée. Tables créées/mises à jour pour Customer 360 complet.' as message;
