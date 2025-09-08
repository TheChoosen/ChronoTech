-- Tables pour le système de chat ChronoTech
-- Exécuter ce script pour créer les tables nécessaires

-- Table des départements (si elle n'existe pas déjà)
CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(10) NOT NULL UNIQUE,
    color VARCHAR(7) DEFAULT '#007bff',
    description TEXT,
    manager_id INT,
    active BOOLEAN DEFAULT TRUE,
    chat_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table des messages de chat
CREATE TABLE IF NOT EXISTS chat_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    channel VARCHAR(100) NOT NULL,
    message TEXT,
    message_type ENUM('text', 'file', 'image', 'voice', 'pdf') DEFAULT 'text',
    file_id INT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    edited_at TIMESTAMP NULL,
    INDEX idx_channel_timestamp (channel, timestamp),
    INDEX idx_user_id (user_id)
);

-- Table des fichiers partagés dans le chat
CREATE TABLE IF NOT EXISTS chat_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    channel VARCHAR(100) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    file_type VARCHAR(100),
    file_size BIGINT DEFAULT 0,
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_channel (channel),
    INDEX idx_user_id (user_id)
);

-- Table pour suivre les utilisateurs en ligne
CREATE TABLE IF NOT EXISTS user_online_status (
    user_id INT PRIMARY KEY,
    status ENUM('online', 'away', 'busy', 'offline') DEFAULT 'offline',
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    current_channel VARCHAR(100) NULL
);

-- Insérer quelques départements de test si la table est vide
INSERT IGNORE INTO departments (name, code, color, description, active, chat_enabled) VALUES
('Technique', 'TECH', '#007bff', 'Équipe technique et maintenance', 1, 1),
('Commercial', 'COMM', '#28a745', 'Équipe commerciale et ventes', 1, 1),
('Administration', 'ADMIN', '#6f42c1', 'Administration et gestion', 1, 1),
('Support Client', 'SUPP', '#17a2b8', 'Support et service client', 1, 1),
('Comptabilité', 'COMPTA', '#fd7e14', 'Département comptabilité', 1, 0);

-- Ajouter la colonne department_id aux utilisateurs si elle n'existe pas
ALTER TABLE users ADD COLUMN IF NOT EXISTS department_id INT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS status ENUM('online', 'away', 'busy', 'offline') DEFAULT 'offline';

-- Mettre à jour quelques utilisateurs avec des départements
UPDATE users SET department_id = 1, status = 'online' WHERE id = 1;
UPDATE users SET department_id = 2, status = 'online' WHERE id = 2;
UPDATE users SET department_id = 1, status = 'busy' WHERE id = 3;
UPDATE users SET department_id = 3, status = 'online' WHERE id = 4;
