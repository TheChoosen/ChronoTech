#!/usr/bin/env python3
"""
Script d'initialisation des tables Customer 360
Crée les tables manquantes si elles n'existent pas
"""

import pymysql
from core.config import get_db_config
from core.utils import log_info, log_error

def create_missing_tables():
    """Créer les tables manquantes pour Customer 360"""
    try:
        config = get_db_config()
        connection = pymysql.connect(**config)
        
        with connection.cursor() as cursor:
            # Vérifier si la table customer_documents existe
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'customer_documents'
            """)
            
            if cursor.fetchone()[0] == 0:
                log_info("Création de la table customer_documents...")
                
                cursor.execute("""
                    CREATE TABLE `customer_documents` (
                      `id` int(11) NOT NULL AUTO_INCREMENT,
                      `customer_id` int(11) NOT NULL,
                      `filename` varchar(255) NOT NULL COMMENT 'Nom du fichier stocké',
                      `original_filename` varchar(255) NOT NULL COMMENT 'Nom original du fichier',
                      `file_path` varchar(500) NOT NULL COMMENT 'Chemin complet du fichier',
                      `file_size` bigint(20) NOT NULL COMMENT 'Taille en bytes',
                      `mime_type` varchar(100) NOT NULL COMMENT 'Type MIME du fichier',
                      `category` enum('contract','invoice','technical','identity','other') DEFAULT 'other' COMMENT 'Catégorie du document',
                      `description` text COMMENT 'Description du document',
                      `is_private` tinyint(1) DEFAULT '0' COMMENT 'Document privé/confidentiel',
                      `uploaded_by` int(11) DEFAULT NULL COMMENT 'ID de l\'utilisateur qui a uploadé',
                      `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      PRIMARY KEY (`id`),
                      KEY `idx_customer_documents_customer` (`customer_id`),
                      KEY `idx_customer_documents_category` (`category`),
                      KEY `idx_customer_documents_uploaded_by` (`uploaded_by`),
                      KEY `idx_customer_documents_created` (`created_at`),
                      KEY `idx_customer_documents_filename` (`original_filename`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Documents associés aux clients'
                """)
                
                log_info("✅ Table customer_documents créée")
            
            # Vérifier si la table customer_activity existe  
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'customer_activity'
            """)
            
            if cursor.fetchone()[0] == 0:
                log_info("Création de la table customer_activity...")
                
                cursor.execute("""
                    CREATE TABLE `customer_activity` (
                      `id` int(11) NOT NULL AUTO_INCREMENT,
                      `customer_id` int(11) NOT NULL,
                      `activity_type` varchar(50) NOT NULL COMMENT 'Type d\'activité',
                      `title` varchar(255) NOT NULL COMMENT 'Titre de l\'activité',
                      `description` text COMMENT 'Description détaillée',
                      `reference_id` int(11) DEFAULT NULL COMMENT 'ID de référence (bon de travail, facture, etc.)',
                      `reference_table` varchar(50) DEFAULT NULL COMMENT 'Table de référence',
                      `metadata` json DEFAULT NULL COMMENT 'Métadonnées additionnelles',
                      `actor_id` int(11) DEFAULT NULL COMMENT 'Utilisateur qui a effectué l\'action',
                      `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      PRIMARY KEY (`id`),
                      KEY `idx_customer_activity_customer` (`customer_id`),
                      KEY `idx_customer_activity_type` (`activity_type`),
                      KEY `idx_customer_activity_actor` (`actor_id`),
                      KEY `idx_customer_activity_created` (`created_at`),
                      KEY `idx_customer_activity_reference` (`reference_table`, `reference_id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Journal des activités client'
                """)
                
                log_info("✅ Table customer_activity créée")
                
                # Ajouter quelques activités de démonstration
                cursor.execute("""
                    INSERT INTO `customer_activity` (`customer_id`, `activity_type`, `title`, `description`, `created_at`) VALUES
                    (1, 'create', 'Client créé', 'Création du profil client', NOW() - INTERVAL 30 DAY),
                    (1, 'contact', 'Appel téléphonique', 'Prise de contact pour nouveau service', NOW() - INTERVAL 15 DAY),
                    (1, 'email', 'Email envoyé', 'Devis transmis par email', NOW() - INTERVAL 10 DAY),
                    (1, 'meeting', 'Rendez-vous', 'Rencontre sur site pour évaluation', NOW() - INTERVAL 5 DAY),
                    (1, 'work_order', 'Bon de travail créé', 'Nouveau bon de travail #001', NOW() - INTERVAL 2 DAY)
                """)
                
                log_info("✅ Données de démonstration ajoutées")
            
            connection.commit()
            log_info("✅ Toutes les tables Customer 360 sont prêtes")
            
    except Exception as e:
        log_error(f"Erreur lors de la création des tables: {e}")
        return False
    finally:
        if 'connection' in locals():
            connection.close()
    
    return True

if __name__ == "__main__":
    create_missing_tables()
