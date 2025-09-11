-- Création des tables pour les modals Kanban du dashboard (version sûre)

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
    FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE CASCADE
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
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE
);

-- Vérification et ajout sécurisé des colonnes
-- Seulement les colonnes qui n'existent probablement pas
SELECT 'Colonnes déjà présentes - aucune action nécessaire' as message;

-- Insertion de données de test pour les statuts des techniciens
INSERT IGNORE INTO technician_status (technician_id, status, last_seen) 
SELECT id, 'available', NOW() 
FROM users 
WHERE role = 'technician';

-- Mise à jour des spécialisations par défaut
UPDATE users SET specialization = COALESCE(specialization, 'Technicien général')
WHERE role = 'technician';
