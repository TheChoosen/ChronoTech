-- Migration pour les fonctionnalités CRUD Customer 360
-- Véhicules, Contacts et Adresses de livraison

-- Table des véhicules clients
CREATE TABLE IF NOT EXISTS customer_vehicles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    make VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    year INT,
    license_plate VARCHAR(20),
    vin VARCHAR(50),
    color VARCHAR(50),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_vehicles_customer_id (customer_id)
);

-- Table des contacts clients
CREATE TABLE IF NOT EXISTS customer_contacts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    role VARCHAR(100),
    is_primary BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_contacts_customer_id (customer_id),
    INDEX idx_customer_contacts_primary (customer_id, is_primary)
);

-- Table des adresses de livraison
CREATE TABLE IF NOT EXISTS customer_addresses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    name VARCHAR(100),
    street TEXT NOT NULL,
    postal_code VARCHAR(10) NOT NULL,
    city VARCHAR(100) NOT NULL,
    country VARCHAR(100) DEFAULT 'France',
    is_default BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_addresses_customer_id (customer_id),
    INDEX idx_customer_addresses_default (customer_id, is_default)
);

-- Données de test pour les véhicules
INSERT IGNORE INTO customer_vehicles (customer_id, make, model, year, license_plate, vin, color, notes) VALUES
(1, 'Peugeot', '308', 2020, 'AB-123-CD', 'VF3XXXXXXXXXX1234', 'Blanc', 'Véhicule principal'),
(1, 'Renault', 'Clio', 2018, 'EF-456-GH', 'VF1XXXXXXXXXX5678', 'Bleu', 'Véhicule secondaire'),
(2, 'Volkswagen', 'Golf', 2019, 'IJ-789-KL', 'WVW2XXXXXXXXX9012', 'Gris', 'Véhicule de société');

-- Données de test pour les contacts
INSERT IGNORE INTO customer_contacts (customer_id, first_name, last_name, phone, email, role, is_primary, notes) VALUES
(1, 'Marie', 'Dupont', '01.23.45.67.89', 'marie.dupont@email.com', 'responsable', true, 'Contact principal famille'),
(1, 'Pierre', 'Dupont', '01.23.45.67.90', 'pierre.dupont@email.com', 'technique', false, 'Contact technique'),
(2, 'Jean', 'Martin', '01.34.56.78.90', 'j.martin@societe.com', 'responsable', true, 'Directeur technique'),
(2, 'Sophie', 'Leblanc', '01.34.56.78.91', 's.leblanc@societe.com', 'comptable', false, 'Service comptabilité');

-- Données de test pour les adresses
INSERT IGNORE INTO customer_addresses (customer_id, name, street, postal_code, city, country, is_default, notes) VALUES
(1, 'Domicile', '123 Rue de la Paix', '75001', 'Paris', 'France', true, 'Sonnette au nom de Dupont'),
(1, 'Résidence secondaire', '456 Avenue de la Mer', '06000', 'Nice', 'France', false, 'Accès par le parking'),
(2, 'Siège social', '789 Boulevard de l\'Industrie', '69000', 'Lyon', 'France', true, 'Livraisons quai de chargement'),
(2, 'Entrepôt', '321 Rue du Commerce', '69100', 'Villeurbanne', 'France', false, 'Horaires 8h-17h uniquement');
