-- Ajoute les colonnes manquantes pour la gestion de la localisation et des notes internes
ALTER TABLE work_orders
  ADD COLUMN location_address TEXT DEFAULT NULL,
  ADD COLUMN location_latitude DECIMAL(10,6) DEFAULT NULL,
  ADD COLUMN location_longitude DECIMAL(10,6) DEFAULT NULL,
  ADD COLUMN internal_notes TEXT DEFAULT NULL;
