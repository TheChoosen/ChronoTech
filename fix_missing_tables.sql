
-- Script de création des tables manquantes
-- Détectées dans les logs d'erreur

-- Table chat_messages pour le système de chat contextuel
CREATE TABLE IF NOT EXISTS chat_messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    context_type VARCHAR(50) NOT NULL,
    context_id INT NOT NULL,
    message TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_context (context_type, context_id),
    INDEX idx_user (user_id),
    INDEX idx_created (created_at)
);

-- Mise à jour de la structure de chat_presence si nécessaire
ALTER TABLE chat_presence 
ADD COLUMN IF NOT EXISTS context_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS context_id INT,
ADD INDEX IF NOT EXISTS idx_context_presence (context_type, context_id);

-- Vérifier si d'autres tables sont manquantes
SHOW TABLES LIKE 'work_orders';
SHOW TABLES LIKE 'interventions';
SHOW TABLES LIKE 'users';
SHOW TABLES LIKE 'technicians';
