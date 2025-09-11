-- Création de la table chat_presence manquante (version sûre)
CREATE TABLE IF NOT EXISTS chat_presence (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    status ENUM('online', 'offline', 'away') DEFAULT 'offline',
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    room VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_room (user_id, room)
);

-- Insertion de données par défaut pour les utilisateurs existants
INSERT IGNORE INTO chat_presence (user_id, status, room)
SELECT id, 'offline', 'general' 
FROM users 
WHERE id NOT IN (SELECT DISTINCT user_id FROM chat_presence WHERE room = 'general' OR room IS NULL);
