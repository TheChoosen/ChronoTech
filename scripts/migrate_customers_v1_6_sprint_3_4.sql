-- Migration script for Customer 360 v1.6 - Sprint 3-4
-- Date: August 22, 2025
-- Description: Module finances client + Documents & signature + Méthodes de paiement tokenisées

-- =====================================================
-- PHASE 2 (S3-S6) — Finance & Conformité
-- =====================================================

-- 1. Table pour profil financier client
CREATE TABLE customer_finances (
    customer_id INT NOT NULL PRIMARY KEY,
    credit_limit DECIMAL(12, 2) DEFAULT 0.00 COMMENT 'Limite de crédit autorisée',
    available_credit DECIMAL(12, 2) DEFAULT 0.00 COMMENT 'Crédit disponible',
    payment_terms VARCHAR(50) DEFAULT 'net30' COMMENT 'Conditions de paiement (net30, net15, etc.)',
    price_tier VARCHAR(50) DEFAULT 'standard' COMMENT 'Niveau de prix (standard, vip, wholesale, etc.)',
    discount_percent DECIMAL(5, 2) DEFAULT 0.00 COMMENT 'Pourcentage de rabais contractuel',
    tax_exempt BOOLEAN DEFAULT FALSE COMMENT 'Exemption de taxes',
    tax_exempt_reason VARCHAR(255) COMMENT 'Raison de l\'exemption de taxes',
    tax_exempt_number VARCHAR(100) COMMENT 'Numéro d\'exemption fiscale',
    high_risk BOOLEAN DEFAULT FALSE COMMENT 'Client à risque',
    risk_reason VARCHAR(255) COMMENT 'Raison du statut à risque',
    hold_status ENUM('none', 'review', 'credit_hold', 'blocked') DEFAULT 'none' COMMENT 'Statut de blocage',
    hold_reason VARCHAR(255) COMMENT 'Raison du blocage',
    currency_code CHAR(3) DEFAULT 'CAD' COMMENT 'Devise préférée',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_credit_limit (credit_limit),
    INDEX idx_price_tier (price_tier),
    INDEX idx_hold_status (hold_status)
) ENGINE=InnoDB COMMENT='Profil financier et conditions de crédit par client';

-- 2. Table pour méthodes de paiement tokenisées
CREATE TABLE customer_payment_methods (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    provider ENUM('stripe', 'paypal', 'square', 'moneris', 'other') NOT NULL COMMENT 'Fournisseur de paiement',
    token VARCHAR(255) NOT NULL COMMENT 'Token sécurisé du fournisseur',
    method_type VARCHAR(50) NOT NULL COMMENT 'Type (credit_card, debit_card, bank_account, etc.)',
    masked_number VARCHAR(50) COMMENT 'Numéro masqué pour affichage (****1234)',
    expiry_date VARCHAR(10) COMMENT 'Date d\'expiration (MM/YY)',
    holder_name VARCHAR(255) COMMENT 'Nom du titulaire',
    brand VARCHAR(50) COMMENT 'Marque de la carte (Visa, Mastercard, etc.)',
    last_four VARCHAR(4) COMMENT 'Quatre derniers chiffres',
    is_default BOOLEAN DEFAULT FALSE COMMENT 'Méthode de paiement par défaut',
    is_active BOOLEAN DEFAULT TRUE COMMENT 'Méthode active',
    metadata JSON COMMENT 'Données additionnelles du fournisseur',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_payment (customer_id, is_default),
    INDEX idx_payment_provider (provider),
    INDEX idx_payment_active (is_active)
) ENGINE=InnoDB COMMENT='Méthodes de paiement tokenisées par client';

-- 3. Table pour historique des soldes (snapshots AR)
CREATE TABLE customer_balance_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    event_type ENUM('invoice_created', 'invoice_paid', 'payment_received', 'credit_applied', 'debit_applied', 'adjustment', 'write_off') NOT NULL,
    reference_id INT COMMENT 'ID de la facture, paiement, etc.',
    reference_table VARCHAR(50) COMMENT 'Table de référence',
    reference_number VARCHAR(100) COMMENT 'Numéro de référence (facture, etc.)',
    amount DECIMAL(12, 2) NOT NULL COMMENT 'Montant de la transaction',
    balance_before DECIMAL(12, 2) NOT NULL COMMENT 'Solde avant transaction',
    balance_after DECIMAL(12, 2) NOT NULL COMMENT 'Solde après transaction',
    currency_code CHAR(3) DEFAULT 'CAD',
    description VARCHAR(255) COMMENT 'Description de la transaction',
    processed_by INT COMMENT 'Utilisateur qui a traité',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (processed_by) REFERENCES users(id) ON SET NULL,
    INDEX idx_customer_balance (customer_id, created_at DESC),
    INDEX idx_balance_type (event_type),
    INDEX idx_balance_reference (reference_table, reference_id)
) ENGINE=InnoDB COMMENT='Historique des soldes et transactions client';

-- 4. Table pour derniers paiements (vue rapide)
CREATE TABLE customer_payment_summary (
    customer_id INT NOT NULL PRIMARY KEY,
    last_payment_date DATETIME COMMENT 'Date du dernier paiement',
    last_payment_amount DECIMAL(12, 2) DEFAULT 0.00 COMMENT 'Montant du dernier paiement',
    last_payment_method VARCHAR(50) COMMENT 'Méthode du dernier paiement',
    total_paid_ytd DECIMAL(12, 2) DEFAULT 0.00 COMMENT 'Total payé cette année',
    total_paid_lifetime DECIMAL(12, 2) DEFAULT 0.00 COMMENT 'Total payé à vie',
    average_payment_days INT DEFAULT 0 COMMENT 'Délai moyen de paiement en jours',
    payment_score INT DEFAULT 100 COMMENT 'Score de paiement (0-100)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_last_payment (last_payment_date),
    INDEX idx_payment_score (payment_score)
) ENGINE=InnoDB COMMENT='Résumé des paiements par client';

-- =====================================================
-- DOCUMENTS & SIGNATURE (Conformité)
-- =====================================================

-- 5. Table pour documents client
CREATE TABLE customer_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    document_type ENUM('contract', 'fi_agreement', 'service_agreement', 'invoice', 'receipt', 'id_proof', 'insurance', 'warranty', 'delivery_proof', 'signature', 'photo', 'other') NOT NULL,
    category VARCHAR(50) COMMENT 'Catégorie libre (contrat_vente, garantie_prolongee, etc.)',
    title VARCHAR(255) NOT NULL COMMENT 'Titre du document',
    filename VARCHAR(255) NOT NULL COMMENT 'Nom original du fichier',
    file_path VARCHAR(512) NOT NULL COMMENT 'Chemin de stockage relatif',
    storage_uri VARCHAR(512) COMMENT 'URI complet (pour stockage cloud)',
    file_size INT NOT NULL COMMENT 'Taille en octets',
    mime_type VARCHAR(255) NOT NULL COMMENT 'Type MIME',
    hash_sha256 VARCHAR(64) NOT NULL COMMENT 'Hash SHA-256 pour intégrité',
    hash_md5 VARCHAR(32) COMMENT 'Hash MD5 pour compatibilité',
    is_signed BOOLEAN DEFAULT FALSE COMMENT 'Document signé',
    signed_at DATETIME COMMENT 'Date de signature',
    signed_by VARCHAR(255) COMMENT 'Nom du signataire',
    signature_provider VARCHAR(100) COMMENT 'Fournisseur de signature (docusign, adobe, internal)',
    signature_reference VARCHAR(255) COMMENT 'Référence externe de signature',
    signature_data JSON COMMENT 'Données de signature (coordonnées, etc.)',
    is_confidential BOOLEAN DEFAULT FALSE COMMENT 'Document confidentiel',
    access_level ENUM('public', 'customer', 'staff', 'admin') DEFAULT 'staff' COMMENT 'Niveau d\'accès',
    created_by INT COMMENT 'Utilisateur qui a ajouté le document',
    expires_at DATETIME COMMENT 'Date d\'expiration du document',
    tags JSON COMMENT 'Tags pour classification',
    version INT DEFAULT 1 COMMENT 'Version du document',
    parent_document_id INT COMMENT 'Document parent (pour versions)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON SET NULL,
    FOREIGN KEY (parent_document_id) REFERENCES customer_documents(id) ON SET NULL,
    INDEX idx_customer_documents (customer_id, document_type),
    INDEX idx_document_signed (is_signed, signed_at),
    INDEX idx_document_hash (hash_sha256),
    INDEX idx_document_expires (expires_at),
    INDEX idx_document_access (access_level)
) ENGINE=InnoDB COMMENT='Documents et preuves client avec signature électronique';

-- 6. Table pour audit d'accès aux documents
CREATE TABLE customer_document_access_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    customer_id INT NOT NULL,
    accessed_by INT COMMENT 'Utilisateur qui a accédé',
    access_type ENUM('view', 'download', 'share', 'print', 'delete') NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    success BOOLEAN DEFAULT TRUE,
    failure_reason VARCHAR(255),
    accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES customer_documents(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (accessed_by) REFERENCES users(id) ON SET NULL,
    INDEX idx_document_access (document_id, accessed_at),
    INDEX idx_customer_access (customer_id, accessed_at),
    INDEX idx_user_access (accessed_by, accessed_at)
) ENGINE=InnoDB COMMENT='Log d\'accès aux documents pour audit';

-- =====================================================
-- TRIGGERS POUR AUTOMATION
-- =====================================================

-- Trigger pour mettre à jour available_credit automatiquement
DELIMITER $$
CREATE TRIGGER update_available_credit 
AFTER UPDATE ON customer_finances
FOR EACH ROW
BEGIN
    -- Si credit_limit change, recalculer available_credit
    IF NEW.credit_limit != OLD.credit_limit THEN
        SET NEW.available_credit = NEW.credit_limit - IFNULL((
            SELECT SUM(total_amount) 
            FROM invoices 
            WHERE customer_id = NEW.customer_id 
            AND status IN ('open', 'overdue')
        ), 0);
    END IF;
END$$
DELIMITER ;

-- Trigger pour créer une activité lors d'ajout de document
DELIMITER $$
CREATE TRIGGER log_document_activity 
AFTER INSERT ON customer_documents
FOR EACH ROW
BEGIN
    INSERT INTO customer_activity (
        customer_id, 
        activity_type, 
        reference_id, 
        reference_table, 
        title, 
        description, 
        actor_id, 
        actor_type, 
        created_at
    ) VALUES (
        NEW.customer_id,
        'document',
        NEW.id,
        'customer_documents',
        CONCAT('Document ajouté: ', NEW.title),
        CONCAT('Type: ', NEW.document_type, ' - Fichier: ', NEW.filename),
        NEW.created_by,
        'user',
        NOW()
    );
END$$
DELIMITER ;

-- Trigger pour créer une activité lors de signature
DELIMITER $$
CREATE TRIGGER log_signature_activity 
AFTER UPDATE ON customer_documents
FOR EACH ROW
BEGIN
    IF NEW.is_signed = TRUE AND OLD.is_signed = FALSE THEN
        INSERT INTO customer_activity (
            customer_id, 
            activity_type, 
            reference_id, 
            reference_table, 
            title, 
            description, 
            actor_type, 
            created_at
        ) VALUES (
            NEW.customer_id,
            'document',
            NEW.id,
            'customer_documents',
            CONCAT('Document signé: ', NEW.title),
            CONCAT('Signé par: ', IFNULL(NEW.signed_by, 'N/A'), ' - Fournisseur: ', IFNULL(NEW.signature_provider, 'internal')),
            'system',
            NOW()
        );
    END IF;
END$$
DELIMITER ;

-- =====================================================
-- DONNÉES INITIALES ET MIGRATION
-- =====================================================

-- Créer profils financiers par défaut pour clients existants
INSERT INTO customer_finances (customer_id, credit_limit, available_credit, payment_terms, price_tier)
SELECT 
    id,
    CASE 
        WHEN type = 'enterprise' THEN 10000.00
        WHEN type = 'government' THEN 25000.00
        ELSE 2500.00
    END as credit_limit,
    CASE 
        WHEN type = 'enterprise' THEN 10000.00
        WHEN type = 'government' THEN 25000.00
        ELSE 2500.00
    END as available_credit,
    CASE 
        WHEN type = 'government' THEN 'net45'
        WHEN type = 'enterprise' THEN 'net30'
        ELSE 'net15'
    END as payment_terms,
    CASE 
        WHEN type = 'government' THEN 'government'
        WHEN type = 'enterprise' THEN 'wholesale'
        ELSE 'standard'
    END as price_tier
FROM customers
WHERE id NOT IN (SELECT customer_id FROM customer_finances);

-- Créer résumés de paiement par défaut
INSERT INTO customer_payment_summary (customer_id, payment_score)
SELECT id, 100
FROM customers
WHERE id NOT IN (SELECT customer_id FROM customer_payment_summary);

-- =====================================================
-- VUES UTILES POUR REPORTING
-- =====================================================

-- Vue pour résumé financier client
CREATE VIEW v_customer_financial_summary AS
SELECT 
    c.id,
    c.name,
    c.type,
    cf.credit_limit,
    cf.available_credit,
    cf.payment_terms,
    cf.price_tier,
    cf.discount_percent,
    cf.hold_status,
    cps.last_payment_date,
    cps.last_payment_amount,
    cps.payment_score,
    cps.average_payment_days,
    IFNULL(outstanding.total_outstanding, 0) as current_balance,
    IFNULL(overdue.total_overdue, 0) as overdue_balance
FROM customers c
LEFT JOIN customer_finances cf ON c.id = cf.customer_id
LEFT JOIN customer_payment_summary cps ON c.id = cps.customer_id
LEFT JOIN (
    SELECT customer_id, SUM(total_amount) as total_outstanding
    FROM invoices 
    WHERE status = 'open'
    GROUP BY customer_id
) outstanding ON c.id = outstanding.customer_id
LEFT JOIN (
    SELECT customer_id, SUM(total_amount) as total_overdue
    FROM invoices 
    WHERE status = 'overdue'
    GROUP BY customer_id
) overdue ON c.id = overdue.customer_id;

-- Vue pour documents récents par client
CREATE VIEW v_customer_recent_documents AS
SELECT 
    cd.*,
    c.name as customer_name,
    u.name as created_by_name
FROM customer_documents cd
JOIN customers c ON cd.customer_id = c.id
LEFT JOIN users u ON cd.created_by = u.id
WHERE cd.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
ORDER BY cd.created_at DESC;

-- =====================================================
-- INDEX POUR PERFORMANCE
-- =====================================================

-- Index composites pour requêtes fréquentes
CREATE INDEX idx_customer_docs_type_date ON customer_documents(customer_id, document_type, created_at DESC);
CREATE INDEX idx_payment_methods_customer_default ON customer_payment_methods(customer_id, is_default, is_active);
CREATE INDEX idx_balance_customer_date ON customer_balance_history(customer_id, created_at DESC);

-- Index pour recherche de documents
CREATE INDEX idx_documents_fulltext ON customer_documents(title, filename);

-- =====================================================
-- FONCTIONS UTILES
-- =====================================================

-- Fonction pour calculer le score de crédit client
DELIMITER $$
CREATE FUNCTION calculate_customer_credit_score(customer_id_param INT) 
RETURNS INT
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE score INT DEFAULT 100;
    DECLARE avg_days INT DEFAULT 0;
    DECLARE overdue_count INT DEFAULT 0;
    
    -- Récupérer délai moyen de paiement
    SELECT IFNULL(average_payment_days, 0) INTO avg_days
    FROM customer_payment_summary 
    WHERE customer_id = customer_id_param;
    
    -- Compter factures en retard
    SELECT COUNT(*) INTO overdue_count
    FROM invoices 
    WHERE customer_id = customer_id_param 
    AND status = 'overdue';
    
    -- Ajuster le score
    SET score = score - (avg_days * 0.5); -- -0.5 point par jour de retard moyen
    SET score = score - (overdue_count * 10); -- -10 points par facture en retard
    
    -- Minimum 0, maximum 100
    IF score < 0 THEN SET score = 0; END IF;
    IF score > 100 THEN SET score = 100; END IF;
    
    RETURN score;
END$$
DELIMITER ;

-- Commenter la migration
ALTER TABLE customers ADD COLUMN migration_v1_6_date DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Date de migration vers v1.6 Sprint 3-4';

COMMIT;
