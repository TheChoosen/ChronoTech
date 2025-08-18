-- Migration: ajouter colonnes manquantes à la table customers
-- Date: 2025-08-14

-- Ajoute les colonnes utilisées par le formulaire customers.add
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS siret VARCHAR(64),
    ADD COLUMN IF NOT EXISTS status VARCHAR(32),
    ADD COLUMN IF NOT EXISTS postal_code VARCHAR(20),
    ADD COLUMN IF NOT EXISTS city VARCHAR(100),
    ADD COLUMN IF NOT EXISTS country VARCHAR(100),
    ADD COLUMN IF NOT EXISTS billing_address TEXT,
    ADD COLUMN IF NOT EXISTS payment_terms VARCHAR(64),
    ADD COLUMN IF NOT EXISTS notes TEXT,
    ADD COLUMN IF NOT EXISTS tax_number VARCHAR(64),
    ADD COLUMN IF NOT EXISTS preferred_contact_method VARCHAR(32),
    ADD COLUMN IF NOT EXISTS zone VARCHAR(100);

COMMIT;
