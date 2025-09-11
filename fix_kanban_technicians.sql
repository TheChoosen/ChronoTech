-- Script de correction pour le Kanban des techniciens
-- Ce script ajoute la colonne updated_by manquante et corrige les valeurs ENUM

-- 1. Ajouter la colonne updated_by manquante (si elle n'existe pas)
-- Vérifier si la colonne existe déjà
SET @exist := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'bdm' AND table_name = 'technician_status' AND column_name = 'updated_by');
SET @sqlstmt := IF(@exist = 0, 'ALTER TABLE technician_status ADD COLUMN updated_by INT DEFAULT NULL', 'SELECT "Colonne updated_by existe déjà" as info');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;

-- 2. Modifier l'ENUM pour inclure toutes les valeurs utilisées dans l'API
ALTER TABLE technician_status 
MODIFY COLUMN status ENUM('online','offline','busy','available','break','pause') DEFAULT 'offline';

-- 3. Vérifier et nettoyer les données existantes
UPDATE technician_status 
SET status = 'break' 
WHERE status = 'pause';

-- 4. Mettre à jour les last_seen pour tous les techniciens actifs
UPDATE technician_status ts
JOIN users u ON ts.technician_id = u.id
SET ts.last_seen = NOW()
WHERE u.is_active = 1 AND u.role = 'technician';

-- 5. Créer ou mettre à jour les statuts manquants pour tous les techniciens
INSERT IGNORE INTO technician_status (technician_id, status, last_seen, location)
SELECT 
    u.id,
    COALESCE(u.availability_status, 'available') as status,
    NOW() as last_seen,
    CONCAT('Zone ', COALESCE(u.zone, 'Générale')) as location
FROM users u
WHERE u.role = 'technician' AND u.is_active = 1;

-- 6. Afficher un résumé des techniciens et leurs statuts
SELECT 
    'Résumé des techniciens par statut:' as info,
    ts.status,
    COUNT(*) as count
FROM technician_status ts
JOIN users u ON ts.technician_id = u.id
WHERE u.is_active = 1
GROUP BY ts.status
ORDER BY count DESC;

SELECT 'Correction du Kanban techniciens terminée avec succès!' as result;
