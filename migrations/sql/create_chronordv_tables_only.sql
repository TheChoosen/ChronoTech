-- Script de création des tables ChronoRDV (sans données exemple)
-- Tables nouvelles entités pour la gestion des rendez-vous et de la planification

-- Table appointments (RDV planifiés)
CREATE TABLE IF NOT EXISTS appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_id INT NOT NULL,
    technician_id INT NULL,
    start DATETIME NOT NULL,
    end DATETIME NULL,
    status ENUM('scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled', 'rescheduled') DEFAULT 'scheduled',
    window_start TIME NULL COMMENT 'Début de fenêtre préférée',
    window_end TIME NULL COMMENT 'Fin de fenêtre préférée',
    location_lat DECIMAL(10, 8) NULL COMMENT 'Latitude du rendez-vous',
    location_lng DECIMAL(11, 8) NULL COMMENT 'Longitude du rendez-vous',
    location_address TEXT NULL COMMENT 'Adresse complète du rendez-vous',
    notes TEXT NULL COMMENT 'Notes spécifiques au rendez-vous',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE SET NULL,
    
    INDEX idx_appointments_date (start, end),
    INDEX idx_appointments_technician (technician_id),
    INDEX idx_appointments_status (status),
    INDEX idx_appointments_work_order (work_order_id)
);

-- Table route_plan (séquences ordonnées par technicien/jour)
CREATE TABLE IF NOT EXISTS route_plan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    technician_id INT NOT NULL,
    date DATE NOT NULL,
    stops JSON NOT NULL COMMENT 'Séquence ordonnée des arrêts (JSON array)',
    distance_km DECIMAL(10, 2) DEFAULT 0 COMMENT 'Distance totale en kilomètres',
    duration_min INT DEFAULT 0 COMMENT 'Durée totale en minutes',
    score DECIMAL(5, 2) DEFAULT 0 COMMENT 'Score d''optimisation (0-100)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE CASCADE,
    
    UNIQUE KEY unique_technician_date (technician_id, date),
    INDEX idx_route_plan_date (date),
    INDEX idx_route_plan_technician (technician_id)
);

-- Table tech_skills (rattachement utilisateurs ↔ compétences)
CREATE TABLE IF NOT EXISTS tech_skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    skill_name VARCHAR(100) NOT NULL COMMENT 'Nom de la compétence',
    skill_level ENUM('beginner', 'intermediate', 'advanced', 'expert') DEFAULT 'intermediate',
    certification_date DATE NULL COMMENT 'Date de certification',
    expiry_date DATE NULL COMMENT 'Date d''expiration de la certification',
    notes TEXT NULL COMMENT 'Notes sur la compétence',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    UNIQUE KEY unique_user_skill (user_id, skill_name),
    INDEX idx_tech_skills_user (user_id),
    INDEX idx_tech_skills_name (skill_name),
    INDEX idx_tech_skills_level (skill_level)
);

-- Table appointment_constraints (fenêtres, préférences, exigences)
CREATE TABLE IF NOT EXISTS appointment_constraints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    appointment_id INT NOT NULL,
    constraint_type ENUM('time_window', 'skill_required', 'equipment_needed', 'customer_preference', 'travel_restriction') NOT NULL,
    window_start TIME NULL COMMENT 'Début de fenêtre contrainte',
    window_end TIME NULL COMMENT 'Fin de fenêtre contrainte',
    preference_level ENUM('required', 'preferred', 'optional') DEFAULT 'preferred',
    requirement_text TEXT NULL COMMENT 'Description textuelle de la contrainte',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE,
    
    INDEX idx_constraints_appointment (appointment_id),
    INDEX idx_constraints_type (constraint_type),
    INDEX idx_constraints_preference (preference_level)
);

-- Table travel_segments (segments calculés)
CREATE TABLE IF NOT EXISTS travel_segments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    route_plan_id INT NOT NULL,
    from_stop INT NOT NULL COMMENT 'Index du point de départ dans le plan',
    to_stop INT NOT NULL COMMENT 'Index du point d''arrivée dans le plan',
    meters INT DEFAULT 0 COMMENT 'Distance en mètres',
    seconds INT DEFAULT 0 COMMENT 'Durée en secondes',
    mode ENUM('driving', 'walking', 'transit', 'bicycling') DEFAULT 'driving',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (route_plan_id) REFERENCES route_plan(id) ON DELETE CASCADE,
    
    INDEX idx_travel_segments_route (route_plan_id),
    INDEX idx_travel_segments_stops (from_stop, to_stop)
);

-- Table user_presence (pour le suivi des techniciens en ligne)
CREATE TABLE IF NOT EXISTS user_presence (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status ENUM('online', 'away', 'busy', 'offline') DEFAULT 'offline',
    location_lat DECIMAL(10, 8) NULL COMMENT 'Dernière position connue',
    location_lng DECIMAL(11, 8) NULL COMMENT 'Dernière position connue',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    UNIQUE KEY unique_user_presence (user_id),
    INDEX idx_user_presence_last_seen (last_seen),
    INDEX idx_user_presence_status (status)
);

-- Affichage des tables créées
SELECT 'Tables ChronoRDV créées avec succès:' as message;
