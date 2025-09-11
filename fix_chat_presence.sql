-- Création de la table chat_presence manquante
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

-- Index pour les performances
CREATE INDEX idx_chat_presence_user_id ON chat_presence(user_id);
CREATE INDEX idx_chat_presence_status ON chat_presence(status);
CREATE INDEX idx_chat_presence_last_seen ON chat_presence(last_seen);

-- Insertion de données par défaut pour les utilisateurs existants
INSERT IGNORE INTO chat_presence (user_id, status, room)
SELECT id, 'offline', 'general' 
FROM users 
WHERE id NOT IN (SELECT user_id FROM chat_presence WHERE room = 'general');
