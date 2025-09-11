-- Création des tables pour les modals Kanban du dashboard

-- Table pour le statut des techniciens
CREATE TABLE IF NOT EXISTS technician_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    technician_id INT NOT NULL,
    status ENUM('available', 'busy', 'pause', 'offline') DEFAULT 'offline',
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    location VARCHAR(255),
    updated_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_technician (technician_id),
    FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Table pour l'historique des bons de travail (optionnelle)
CREATE TABLE IF NOT EXISTS work_order_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_id INT NOT NULL,
    changed_by INT,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Ajouter la colonne spécialisation aux utilisateurs si elle n'existe pas
ALTER TABLE users ADD COLUMN specialization VARCHAR(100);
ALTER TABLE users ADD COLUMN avatar_url VARCHAR(255);

-- Index pour améliorer les performances
CREATE INDEX idx_technician_status_status ON technician_status(status);
CREATE INDEX idx_technician_status_last_seen ON technician_status(last_seen);
CREATE INDEX idx_work_order_history_work_order_id ON work_order_history(work_order_id);
CREATE INDEX idx_work_order_history_change_date ON work_order_history(change_date);

-- Insertion de données de test pour les statuts des techniciens
INSERT INTO technician_status (technician_id, status, last_seen) 
SELECT id, 'available', NOW() 
FROM users 
WHERE role = 'technician' 
AND id NOT IN (SELECT technician_id FROM technician_status)
ON DUPLICATE KEY UPDATE last_seen = NOW();

-- Mise à jour des spécialisations par défaut
UPDATE users SET specialization = 'Technicien général' 
WHERE role = 'technician' AND (specialization IS NULL OR specialization = '');
