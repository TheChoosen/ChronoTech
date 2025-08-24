-- Migration pour créer la table invoices
-- Cette table est référencée dans le code Customer 360 mais n'existe pas encore

CREATE TABLE invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id INT NOT NULL,
    work_order_id INT NULL,
    
    -- Montants
    subtotal_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    
    -- Statut et dates
    status ENUM('draft', 'sent', 'open', 'paid', 'overdue', 'cancelled', 'refunded') NOT NULL DEFAULT 'draft',
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    paid_date DATETIME NULL,
    
    -- Informations client (snapshot au moment de la facture)
    billing_name VARCHAR(255) NOT NULL,
    billing_address TEXT,
    billing_city VARCHAR(100),
    billing_postal_code VARCHAR(20),
    billing_country VARCHAR(100) DEFAULT 'Canada',
    
    -- Détails de paiement
    payment_method ENUM('cash', 'check', 'transfer', 'credit_card', 'debit_card', 'paypal', 'stripe') NULL,
    payment_reference VARCHAR(100) NULL,
    payment_notes TEXT NULL,
    
    -- Informations additionnelles
    notes TEXT NULL,
    terms TEXT NULL,
    discount_percent DECIMAL(5,2) DEFAULT 0.00,
    late_fee_applied DECIMAL(8,2) DEFAULT 0.00,
    
    -- Metadata
    created_by INT NULL,
    updated_by INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Index et contraintes
    INDEX idx_customer_id (customer_id),
    INDEX idx_work_order_id (work_order_id),
    INDEX idx_status (status),
    INDEX idx_invoice_date (invoice_date),
    INDEX idx_due_date (due_date),
    INDEX idx_customer_status (customer_id, status),
    
    -- Contraintes de clés étrangères
    CONSTRAINT fk_invoices_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
    CONSTRAINT fk_invoices_work_order FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE SET NULL
);

-- Table pour les détails de facturation (lignes de facture)
CREATE TABLE invoice_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id INT NOT NULL,
    product_id INT NULL,
    service_id INT NULL,
    
    -- Description et quantité
    description TEXT NOT NULL,
    quantity DECIMAL(10,3) NOT NULL DEFAULT 1.000,
    unit_price DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    line_total DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    
    -- Taxes
    tax_rate DECIMAL(5,2) DEFAULT 0.00,
    tax_amount DECIMAL(12,2) DEFAULT 0.00,
    
    -- Ordre d'affichage
    sort_order INT DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Index et contraintes
    INDEX idx_invoice_id (invoice_id),
    INDEX idx_product_id (product_id),
    INDEX idx_service_id (service_id),
    
    -- Contraintes
    CONSTRAINT fk_invoice_items_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    CONSTRAINT fk_invoice_items_product FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE SET NULL
);

-- Table pour l'historique des paiements
CREATE TABLE invoice_payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id INT NOT NULL,
    
    -- Détails du paiement
    amount DECIMAL(12,2) NOT NULL,
    payment_date DATETIME NOT NULL,
    payment_method ENUM('cash', 'check', 'transfer', 'credit_card', 'debit_card', 'paypal', 'stripe') NOT NULL,
    reference VARCHAR(100) NULL,
    
    -- Statut
    status ENUM('pending', 'confirmed', 'failed', 'refunded') NOT NULL DEFAULT 'pending',
    
    -- Notes
    notes TEXT NULL,
    
    -- Metadata
    created_by INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Index
    INDEX idx_invoice_id (invoice_id),
    INDEX idx_payment_date (payment_date),
    INDEX idx_status (status),
    
    -- Contraintes
    CONSTRAINT fk_invoice_payments_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

-- Vues pour simplifier les requêtes communes
CREATE VIEW invoice_summary AS
SELECT 
    i.id,
    i.invoice_number,
    i.customer_id,
    c.nom as customer_name,
    c.prenom as customer_firstname,
    c.company as customer_company,
    i.total_amount,
    i.status,
    i.invoice_date,
    i.due_date,
    i.paid_date,
    COALESCE(SUM(ip.amount), 0) as paid_amount,
    (i.total_amount - COALESCE(SUM(ip.amount), 0)) as balance_due,
    CASE 
        WHEN i.status = 'paid' THEN 'Payée'
        WHEN i.due_date < CURDATE() AND i.status IN ('sent', 'open') THEN 'En retard'
        WHEN i.status = 'sent' OR i.status = 'open' THEN 'En attente'
        ELSE i.status
    END as status_display,
    DATEDIFF(CURDATE(), i.due_date) as days_overdue
FROM invoices i
LEFT JOIN customers c ON i.customer_id = c.id
LEFT JOIN invoice_payments ip ON i.id = ip.invoice_id AND ip.status = 'confirmed'
GROUP BY i.id, i.invoice_number, i.customer_id, c.nom, c.prenom, c.company, 
         i.total_amount, i.status, i.invoice_date, i.due_date, i.paid_date;

-- Trigger pour mettre à jour automatiquement le statut des factures
DELIMITER ;;

CREATE TRIGGER update_invoice_status_after_payment
AFTER INSERT ON invoice_payments
FOR EACH ROW
BEGIN
    DECLARE total_paid DECIMAL(12,2);
    DECLARE invoice_total DECIMAL(12,2);
    
    -- Calculer le total payé pour cette facture
    SELECT COALESCE(SUM(amount), 0) INTO total_paid
    FROM invoice_payments 
    WHERE invoice_id = NEW.invoice_id AND status = 'confirmed';
    
    -- Récupérer le montant total de la facture
    SELECT total_amount INTO invoice_total
    FROM invoices 
    WHERE id = NEW.invoice_id;
    
    -- Mettre à jour le statut selon le montant payé
    IF total_paid >= invoice_total THEN
        UPDATE invoices 
        SET status = 'paid', 
            paid_date = COALESCE(paid_date, NEW.payment_date)
        WHERE id = NEW.invoice_id;
    ELSE
        UPDATE invoices 
        SET status = 'open'
        WHERE id = NEW.invoice_id AND status != 'open';
    END IF;
END;;

DELIMITER ;

-- Index supplémentaires pour les performances
CREATE INDEX idx_invoices_customer_date ON invoices(customer_id, invoice_date);
CREATE INDEX idx_invoices_status_due_date ON invoices(status, due_date);
CREATE INDEX idx_invoice_payments_date_status ON invoice_payments(payment_date, status);

-- Données de test pour vérifier le fonctionnement
INSERT INTO invoices (
    invoice_number, customer_id, subtotal_amount, tax_amount, total_amount,
    status, invoice_date, due_date, billing_name, billing_address, billing_city
) VALUES 
('INV-2025-001', 1, 1000.00, 150.00, 1150.00, 'open', '2025-08-01', '2025-08-31', 'Client Test', '123 Rue Test', 'Montreal'),
('INV-2025-002', 1, 500.00, 75.00, 575.00, 'paid', '2025-07-15', '2025-08-14', 'Client Test', '123 Rue Test', 'Montreal'),
('INV-2025-003', 2, 750.00, 112.50, 862.50, 'sent', '2025-08-15', '2025-09-14', 'Autre Client', '456 Avenue Test', 'Quebec')
ON DUPLICATE KEY UPDATE id=id;

-- Insérer quelques lignes de facturation de test
INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, line_total) VALUES
(1, 'Service de maintenance', 1.000, 500.00, 500.00),
(1, 'Pièces de rechange', 2.000, 250.00, 500.00),
(2, 'Consultation technique', 2.000, 250.00, 500.00),
(3, 'Réparation d\'urgence', 1.000, 750.00, 750.00)
ON DUPLICATE KEY UPDATE id=id;

-- Insérer un paiement de test
INSERT INTO invoice_payments (invoice_id, amount, payment_date, payment_method, status) VALUES
(2, 575.00, '2025-08-14 10:30:00', 'transfer', 'confirmed')
ON DUPLICATE KEY UPDATE id=id;
