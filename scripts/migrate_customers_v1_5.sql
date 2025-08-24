-- Migration script for Customer 360 v1.5 - Sprint 1-2
-- Date: August 22, 2025
-- Description: Ajout des champs profil & segmentation, adresses enrichies, timeline unifiée

-- Backup existing customers table structure
CREATE TABLE customers_backup_v1_5 AS SELECT * FROM customers LIMIT 0;

-- Add new fields to customers table for Phase 1
ALTER TABLE customers 
ADD COLUMN language_code CHAR(5) DEFAULT 'fr-CA' COMMENT 'Code langue ISO (fr-CA, en-US, etc.)',
ADD COLUMN timezone VARCHAR(64) DEFAULT 'America/Montreal' COMMENT 'Fuseau horaire du client',
ADD COLUMN segments JSON COMMENT 'Tags/segments client en format JSON',
ADD COLUMN privacy_level ENUM('normal', 'restreint', 'confidentiel') DEFAULT 'normal' COMMENT 'Niveau de confidentialité',
ADD COLUMN preferred_contact_channel ENUM('email', 'sms', 'phone', 'none') DEFAULT 'email' COMMENT 'Canal de communication préféré',
ADD COLUMN tax_exempt BOOLEAN DEFAULT FALSE COMMENT 'Client exempté de taxes';

-- Create customer_activity table for unified timeline
CREATE TABLE customer_activity (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    activity_type ENUM('workorder', 'invoice', 'payment', 'quote', 'email', 'sms', 'call', 'document', 'appointment', 'note', 'consent', 'vehicle_added', 'system') NOT NULL,
    reference_id INT COMMENT 'ID dans la table référencée',
    reference_table VARCHAR(50) COMMENT 'Nom de la table référencée',
    title VARCHAR(255) NOT NULL COMMENT 'Titre court de l\'activité',
    description TEXT COMMENT 'Description détaillée',
    metadata JSON COMMENT 'Données additionnelles en JSON',
    actor_id INT COMMENT 'ID de l\'utilisateur qui a effectué l\'action',
    actor_type ENUM('user', 'system', 'customer') DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_timeline (customer_id, created_at DESC),
    INDEX idx_activity_type (activity_type),
    INDEX idx_reference (reference_table, reference_id)
) ENGINE=InnoDB COMMENT='Timeline unifiée des activités client';

-- Enhance customer_addresses table (if exists, otherwise create)
CREATE TABLE IF NOT EXISTS customer_addresses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    label VARCHAR(100) NOT NULL COMMENT 'Libellé de l\'adresse',
    street VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    province VARCHAR(50) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(50) DEFAULT 'Canada',
    type ENUM('billing', 'shipping', 'service') DEFAULT 'billing' COMMENT 'Type d\'adresse',
    lat DECIMAL(10,8) COMMENT 'Latitude pour géolocalisation',
    lng DECIMAL(11,8) COMMENT 'Longitude pour géolocalisation',
    delivery_window_start TIME COMMENT 'Début fenêtre de livraison',
    delivery_window_end TIME COMMENT 'Fin fenêtre de livraison',
    instructions TEXT COMMENT 'Instructions spéciales de livraison',
    service_zone VARCHAR(50) COMMENT 'Zone de service',
    is_primary BOOLEAN DEFAULT FALSE COMMENT 'Adresse principale',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_addresses (customer_id),
    INDEX idx_address_type (type),
    INDEX idx_service_zone (service_zone)
) ENGINE=InnoDB COMMENT='Adresses enrichies des clients';

-- Enhance customer_contacts table (if exists, otherwise create)
CREATE TABLE IF NOT EXISTS customer_contacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    role ENUM('owner', 'billing', 'service', 'driver', 'buyer', 'accountant', 'reception', 'workshop', 'decision_maker') DEFAULT 'owner',
    email VARCHAR(255),
    phone VARCHAR(50),
    opt_in_email BOOLEAN DEFAULT TRUE COMMENT 'Consentement emails',
    opt_in_sms BOOLEAN DEFAULT FALSE COMMENT 'Consentement SMS',
    language_code CHAR(5) DEFAULT 'fr-CA' COMMENT 'Langue préférée du contact',
    preferred_contact_hours VARCHAR(100) COMMENT 'Heures de contact préférées',
    is_primary BOOLEAN DEFAULT FALSE COMMENT 'Contact principal',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_contacts (customer_id),
    INDEX idx_contact_role (role),
    INDEX idx_contact_email (email)
) ENGINE=InnoDB COMMENT='Contacts enrichis des clients';

-- Create customer_consents table for GDPR/Loi 25 compliance
CREATE TABLE customer_consents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    consent_type ENUM('marketing_email', 'marketing_sms', 'analytics', 'profiling', 'data_sharing', 'service_notifications') NOT NULL,
    is_granted BOOLEAN NOT NULL DEFAULT FALSE,
    source VARCHAR(100) NOT NULL COMMENT 'Source du consentement (web_form, import, phone, in_person)',
    ip_address VARCHAR(45) COMMENT 'Adresse IP lors du consentement',
    collected_by INT COMMENT 'Utilisateur qui a collecté le consentement',
    version INT NOT NULL DEFAULT 1 COMMENT 'Version du consentement',
    granted_at DATETIME COMMENT 'Date d\'octroi du consentement',
    revoked_at DATETIME COMMENT 'Date de révocation du consentement',
    expires_at DATETIME COMMENT 'Date d\'expiration du consentement',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (collected_by) REFERENCES users(id) ON SET NULL,
    INDEX idx_customer_consents (customer_id, consent_type),
    INDEX idx_consent_status (is_granted, expires_at),
    UNIQUE KEY unique_customer_consent_version (customer_id, consent_type, version)
) ENGINE=InnoDB COMMENT='Consentements clients pour conformité RGPD/Loi 25';

-- Create customer_consent_history for audit trail
CREATE TABLE customer_consent_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    consent_id INT NOT NULL,
    customer_id INT NOT NULL,
    consent_type VARCHAR(50) NOT NULL,
    is_granted BOOLEAN NOT NULL,
    source VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45),
    collected_by INT,
    version INT NOT NULL,
    action VARCHAR(20) NOT NULL COMMENT 'Action effectuée (grant, revoke, expire)',
    action_timestamp DATETIME NOT NULL,
    INDEX idx_consent_history (customer_id, action_timestamp),
    INDEX idx_consent_audit (consent_id)
) ENGINE=InnoDB COMMENT='Historique des consentements pour audit';

-- Create indexes for performance
CREATE INDEX idx_customers_language ON customers(language_code);
CREATE INDEX idx_customers_timezone ON customers(timezone);
CREATE INDEX idx_customers_privacy ON customers(privacy_level);
CREATE INDEX idx_customers_contact_channel ON customers(preferred_contact_channel);

-- Add some initial data migration
UPDATE customers SET 
    language_code = CASE 
        WHEN city IN ('Toronto', 'Vancouver', 'Calgary', 'Ottawa') THEN 'en-CA'
        ELSE 'fr-CA'
    END,
    timezone = CASE 
        WHEN city IN ('Vancouver') THEN 'America/Vancouver'
        WHEN city IN ('Calgary', 'Edmonton') THEN 'America/Edmonton' 
        WHEN city IN ('Toronto', 'Ottawa') THEN 'America/Toronto'
        ELSE 'America/Montreal'
    END,
    segments = JSON_ARRAY('nouveau') -- Segment par défaut pour tous les clients existants
WHERE language_code IS NULL OR language_code = '';

-- Migrate existing addresses if they exist in the customers table
INSERT INTO customer_addresses (customer_id, label, street, city, province, postal_code, country, type, is_primary)
SELECT 
    id,
    'Adresse principale',
    COALESCE(address, ''),
    COALESCE(city, ''),
    COALESCE(province, ''),
    COALESCE(postal_code, ''),
    COALESCE(country, 'Canada'),
    'billing',
    TRUE
FROM customers 
WHERE address IS NOT NULL AND address != ''
ON DUPLICATE KEY UPDATE street = VALUES(street);

-- Create initial activity entries for existing work orders
INSERT INTO customer_activity (customer_id, activity_type, reference_id, reference_table, title, description, actor_type, created_at)
SELECT 
    wo.customer_id,
    'workorder',
    wo.id,
    'work_orders',
    CONCAT('Bon de travail #', wo.claim_number),
    CONCAT('Status: ', wo.status, ' - ', COALESCE(wo.description, '')),
    'system',
    wo.created_at
FROM work_orders wo
WHERE wo.customer_id IS NOT NULL
ON DUPLICATE KEY UPDATE title = VALUES(title);

-- Add comment to track migration
ALTER TABLE customers ADD COLUMN migration_v1_5_date DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Date de migration vers v1.5';

COMMIT;
