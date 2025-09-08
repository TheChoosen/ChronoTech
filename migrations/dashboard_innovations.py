"""
Script de migration pour ajouter les tables nécessaires aux nouvelles fonctionnalités
"""

# Table pour la configuration des widgets personnalisables
CREATE_USER_DASHBOARD_CONFIG = """
CREATE TABLE IF NOT EXISTS user_dashboard_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    layout_config JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# Table pour les coordonnées géographiques (cache géocodage)
CREATE_GEO_COORDINATES = """
CREATE TABLE IF NOT EXISTS geo_coordinates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_customer (customer_id),
    INDEX idx_coordinates (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# Table pour les messages de chat contextuel
CREATE_CHAT_MESSAGES = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    context_type ENUM('work_order', 'customer', 'technician', 'general') NOT NULL,
    context_id INT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_context (context_type, context_id),
    INDEX idx_user_created (user_id, created_at),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# Table pour les liens de partage public
CREATE_PUBLIC_SHARE_LINKS = """
CREATE TABLE IF NOT EXISTS public_share_links (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token VARCHAR(32) NOT NULL UNIQUE,
    work_order_id INT NOT NULL,
    expiration_date DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accessed_count INT DEFAULT 0,
    last_accessed_at DATETIME NULL,
    INDEX idx_token (token),
    INDEX idx_work_order (work_order_id),
    INDEX idx_expiration (expiration_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# Table pour les feedbacks clients sur les liens partagés
CREATE_SHARING_FEEDBACK = """
CREATE TABLE IF NOT EXISTS sharing_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    share_link_id INT NOT NULL,
    work_order_id INT NOT NULL,
    approved BOOLEAN NOT NULL,
    feedback_text TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_share_link (share_link_id),
    INDEX idx_work_order (work_order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# Table pour les KPIs des techniciens (cache)
CREATE_TECHNICIAN_KPIS = """
CREATE TABLE IF NOT EXISTS technician_kpis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    technician_id INT NOT NULL,
    date DATE NOT NULL,
    efficiency_rate DECIMAL(5,2) DEFAULT 0,
    on_time_rate DECIMAL(5,2) DEFAULT 0,
    avg_completion_time INT DEFAULT 0,
    total_completed INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_tech_date (technician_id, date),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# Table pour les équipements (maintenance prédictive)
CREATE_EQUIPMENT = """
CREATE TABLE IF NOT EXISTS equipment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    model VARCHAR(255) NULL,
    serial_number VARCHAR(255) NULL,
    hours_of_use INT DEFAULT 0,
    last_maintenance_date DATE NULL,
    next_maintenance_due DATE NULL,
    status ENUM('active', 'maintenance', 'retired') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_customer (customer_id),
    INDEX idx_next_maintenance (next_maintenance_due),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# Table de liaison équipements <-> bons de travail
CREATE_EQUIPMENT_MAINTENANCE = """
CREATE TABLE IF NOT EXISTS equipment_maintenance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id INT NOT NULL,
    work_order_id INT NOT NULL,
    maintenance_type ENUM('preventive', 'corrective', 'predictive') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_equipment_work_order (equipment_id, work_order_id),
    INDEX idx_equipment (equipment_id),
    INDEX idx_work_order (work_order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# Table pour les annotations visuelles
CREATE_VISUAL_ANNOTATIONS = """
CREATE TABLE IF NOT EXISTS visual_annotations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_order_id INT NOT NULL,
    original_image_path VARCHAR(500) NOT NULL,
    annotated_image_path VARCHAR(500) NOT NULL,
    annotation_data JSON NULL,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_work_order (work_order_id),
    INDEX idx_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# Liste de toutes les tables à créer
ALL_TABLES = [
    CREATE_USER_DASHBOARD_CONFIG,
    CREATE_GEO_COORDINATES,
    CREATE_CHAT_MESSAGES,
    CREATE_PUBLIC_SHARE_LINKS,
    CREATE_SHARING_FEEDBACK,
    CREATE_TECHNICIAN_KPIS,
    CREATE_EQUIPMENT,
    CREATE_EQUIPMENT_MAINTENANCE,
    CREATE_VISUAL_ANNOTATIONS
]

def run_migrations(db_connection):
    """Exécute toutes les migrations"""
    cursor = db_connection.cursor()
    
    for table_sql in ALL_TABLES:
        try:
            cursor.execute(table_sql)
            print(f"✅ Table créée/vérifiée")
        except Exception as e:
            print(f"❌ Erreur lors de la création de table: {e}")
    
    db_connection.commit()
    cursor.close()
    print("🎉 Migrations terminées")

if __name__ == "__main__":
    # Pour tests locaux
    print("Script de migration des tables - Dashboard Innovations")
    print("Exécutez ce script via core/database.py")
