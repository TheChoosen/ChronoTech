-- Migration: Système de tracking temporel des interventions
-- Date: 29/08/2025
-- Description: Ajout table pour suivi détaillé des temps d'intervention

CREATE TABLE IF NOT EXISTS intervention_time_tracking (
    id int AUTO_INCREMENT PRIMARY KEY,
    work_order_id int NOT NULL,
    technician_id int NOT NULL,
    action_type enum('start', 'pause', 'resume', 'complete') NOT NULL,
    timestamp datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    duration_minutes int DEFAULT NULL,
    notes text DEFAULT NULL,
    created_at timestamp DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_work_order (work_order_id),
    INDEX idx_technician (technician_id),
    INDEX idx_timestamp (timestamp),
    
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Ajouter colonne pour status temps dans work_orders
ALTER TABLE work_orders 
ADD COLUMN time_status enum('not_started', 'in_progress', 'paused', 'completed') 
DEFAULT 'not_started' AFTER status;

-- Index pour optimiser les requêtes
CREATE INDEX idx_work_orders_time_status ON work_orders(time_status);
