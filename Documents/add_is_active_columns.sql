-- Script pour ajouter les colonnes is_active manquantes
-- Ces colonnes sont nécessaires pour le bon fonctionnement de l'application

-- Ajouter is_active à la table users
ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL;

-- Ajouter is_active à la table customers
ALTER TABLE customers ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL;

-- Mettre à jour les enregistrements existants pour s'assurer qu'ils sont actifs
UPDATE users SET is_active = TRUE WHERE is_active IS NULL;
UPDATE customers SET is_active = TRUE WHERE is_active IS NULL;

-- Vérifier les résultats
SELECT 'Users with is_active' as table_info, COUNT(*) as count FROM users WHERE is_active = TRUE;
SELECT 'Customers with is_active' as table_info, COUNT(*) as count FROM customers WHERE is_active = TRUE;
