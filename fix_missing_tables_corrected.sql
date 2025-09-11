-- Script de création des tables manquantes (version corrigée)
-- Compatible avec MySQL 5.7+

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

-- Mise à jour de la structure de chat_presence 
-- Vérifier et ajouter les colonnes manquantes
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'chat_presence' 
     AND column_name = 'context_type' 
     AND table_schema = DATABASE()) > 0,
    'SELECT ''Column context_type already exists'' as msg',
    'ALTER TABLE chat_presence ADD COLUMN context_type VARCHAR(50)'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'chat_presence' 
     AND column_name = 'context_id' 
     AND table_schema = DATABASE()) > 0,
    'SELECT ''Column context_id already exists'' as msg',
    'ALTER TABLE chat_presence ADD COLUMN context_id INT'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Ajouter l'index si il n'existe pas
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE table_name = 'chat_presence' 
     AND index_name = 'idx_context_presence' 
     AND table_schema = DATABASE()) > 0,
    'SELECT ''Index idx_context_presence already exists'' as msg',
    'ALTER TABLE chat_presence ADD INDEX idx_context_presence (context_type, context_id)'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Vérification des tables principales
SELECT 'work_orders' as table_name, COUNT(*) as exists_check FROM INFORMATION_SCHEMA.TABLES WHERE table_name = 'work_orders' AND table_schema = DATABASE();
SELECT 'interventions' as table_name, COUNT(*) as exists_check FROM INFORMATION_SCHEMA.TABLES WHERE table_name = 'interventions' AND table_schema = DATABASE();
SELECT 'users' as table_name, COUNT(*) as exists_check FROM INFORMATION_SCHEMA.TABLES WHERE table_name = 'users' AND table_schema = DATABASE();
SELECT 'technicians' as table_name, COUNT(*) as exists_check FROM INFORMATION_SCHEMA.TABLES WHERE table_name = 'technicians' AND table_schema = DATABASE();
SELECT 'chat_messages' as table_name, COUNT(*) as exists_check FROM INFORMATION_SCHEMA.TABLES WHERE table_name = 'chat_messages' AND table_schema = DATABASE();
SELECT 'chat_presence' as table_name, COUNT(*) as exists_check FROM INFORMATION_SCHEMA.TABLES WHERE table_name = 'chat_presence' AND table_schema = DATABASE();
