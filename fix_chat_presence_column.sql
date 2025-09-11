-- Mise à jour de la table chat_presence pour ajouter la colonne manquante
ALTER TABLE chat_presence 
ADD COLUMN IF NOT EXISTS is_active TINYINT(1) DEFAULT 1;

-- Mise à jour des enregistrements existants
UPDATE chat_presence SET is_active = 1 WHERE status = 'online';
UPDATE chat_presence SET is_active = 0 WHERE status IN ('offline', 'away');
