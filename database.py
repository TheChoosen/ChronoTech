"""
Utilitaires pour la base de données ChronoTech
Connexions, migrations, et fonctions communes
"""

import pymysql
import os
import logging
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestionnaire de base de données pour ChronoTech"""
    
    def __init__(self, config=None):
        self.config = config or Config()
        self._connection = None
    
    def get_connection(self):
        """Obtenir une connexion à la base de données"""
        try:
            # Créer une nouvelle connexion à chaque fois avec timeouts optimisés
            connection = pymysql.connect(
                host=self.config.MYSQL_HOST,
                user=self.config.MYSQL_USER,
                password=self.config.MYSQL_PASSWORD,
                database=self.config.MYSQL_DB,
                port=self.config.MYSQL_PORT,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
                connect_timeout=3,   # Timeout de connexion très court
                read_timeout=5,      # Timeout de lecture court
                write_timeout=5,     # Timeout d'écriture court
                sql_mode="TRADITIONAL",
                init_command="SET SESSION sql_mode='TRADITIONAL'"
            )
            logger.debug("Connexion DB établie")
            return connection
        except Exception as e:
            logger.error(f"Erreur de connexion à la base de données: {e}")
            # Retourner None plutôt que de lever une exception
            return None
    
    def close_connection(self):
        """Fermer la connexion à la base de données"""
        if self._connection and self._connection.open:
            self._connection.close()
            logger.info("Connexion à la base de données fermée")
    
    def execute_query(self, query, params=None, fetch_one=False, fetch_all=True):
        """Exécuter une requête SQL"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                
                if query.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE')):
                    if fetch_one:
                        return cursor.fetchone()
                    elif fetch_all:
                        return cursor.fetchall()
                    else:
                        return cursor
                else:
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"Erreur lors de l'exécution de la requête: {e}")
            raise
    
    def execute_transaction(self, queries):
        """Exécuter plusieurs requêtes dans une transaction"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                for query, params in queries:
                    cursor.execute(query, params)
                conn.commit()
                logger.info("Transaction exécutée avec succès")
                return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Erreur lors de la transaction: {e}")
            raise
    
    def check_tables_exist(self, tables):
        """Vérifier si les tables existent"""
        existing_tables = []
        for table in tables:
            try:
                result = self.execute_query(f"SHOW TABLES LIKE '{table}'", fetch_one=True)
                if result:
                    existing_tables.append(table)
            except Exception as e:
                logger.warning(f"Erreur lors de la vérification de la table {table}: {e}")
        
        return existing_tables
    
    def get_table_info(self, table_name):
        """Obtenir les informations sur une table"""
        try:
            return self.execute_query(f"DESCRIBE {table_name}")
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations de la table {table_name}: {e}")
            return None

# Instance globale du gestionnaire de base de données
db_manager = DatabaseManager()

def get_db_connection():
    """Fonction helper pour obtenir une connexion à la base de données"""
    return db_manager.get_connection()

def quick_db_test():
    """Test ultra-rapide de la base de données avec timeouts courts"""
    try:
        # Test de connexion avec timeout de 2 secondes seulement
        test_conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            port=Config.MYSQL_PORT,
            charset='utf8mb4',
            connect_timeout=2,
            read_timeout=2,
            write_timeout=2
        )
        
        with test_conn.cursor() as cursor:
            # Test ultra-rapide : vérifier une table essentielle
            cursor.execute("SHOW TABLES LIKE 'users'")
            users_table = cursor.fetchone()
            
            cursor.execute("SHOW TABLES LIKE 'work_orders'")
            work_orders_table = cursor.fetchone()
        
        test_conn.close()
        
        if users_table and work_orders_table:
            return "ready"  # BD prête avec tables
        else:
            return "accessible"  # BD accessible mais besoin de setup
            
    except Exception as e:
        logger.debug(f"Test BD rapide échoué: {e}")
        return "unavailable"  # BD non accessible

def is_database_ready():
    """Vérifier si la base de données est déjà configurée et prête"""
    try:
        # Vérification rapide : tester les tables essentielles
        essential_tables = ['users', 'work_orders', 'customers']
        
        conn = db_manager.get_connection()
        if conn is None:
            return False
            
        with conn.cursor() as cursor:
            for table in essential_tables:
                cursor.execute(f"SHOW TABLES LIKE '{table}'")
                if not cursor.fetchone():
                    conn.close()
                    return False
                    
            # Vérifier une structure basique (que la table users a des colonnes attendues)
            cursor.execute("DESCRIBE users")
            columns = [row['Field'] for row in cursor.fetchall()]
            required_columns = ['id', 'name', 'email', 'role']
            
            for col in required_columns:
                if col not in columns:
                    conn.close()
                    return False
        
        conn.close()
        logger.info("Base de données validée - toutes les tables essentielles présentes")
        return True
        
    except Exception as e:
        logger.debug(f"Vérification DB échouée (normal au premier démarrage): {e}")
        return False

def init_database():
    """Initialiser la base de données avec les tables nécessaires"""
    logger.info("Initialisation de la base de données...")
    
    # Vérification des tables essentielles
    essential_tables = [
        'users', 'customers', 'work_orders', 'work_order_lines',
        'intervention_notes', 'intervention_media', 'notifications'
    ]
    
    existing_tables = db_manager.check_tables_exist(essential_tables)
    missing_tables = [table for table in essential_tables if table not in existing_tables]
    
    if missing_tables:
        logger.warning(f"Tables manquantes détectées: {missing_tables}")
        return False
    else:
        logger.info("Toutes les tables essentielles sont présentes")
        return True

def setup_database():
    """Configuration initiale de la base de données avec timeout optimisé"""
    try:
        # Test de connexion rapide d'abord
        logger.info("Test de connexion rapide à MySQL...")
        temp_conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            port=Config.MYSQL_PORT,
            charset='utf8mb4',
            connect_timeout=3,   # Timeout très court pour test rapide
            read_timeout=5,      # Timeout court pour lecture
            write_timeout=5      # Timeout court pour écriture
        )
        
        with temp_conn.cursor() as cursor:
            # Test rapide : juste vérifier la connexion
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if not result:
                raise Exception("Test de connexion échoué")
            
            # Création/vérification de la base de données
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            temp_conn.commit()
        
        temp_conn.close()
        logger.info(f"✅ Connexion MySQL OK - Base {Config.MYSQL_DB} prête")
        
        # Initialisation seulement si nécessaire
        if init_database():
            logger.info("✅ Tables de base de données vérifiées")
            return True
        else:
            logger.error("Échec de l'initialisation de la base de données")
            return False
            
    except Exception as e:
        logger.error(f"Erreur lors de la configuration de la base de données: {e}")
        return False

def migrate_database():
    """Effectuer les migrations de base de données"""
    logger.info("Début des migrations de base de données...")
    
    migrations = [
        # Migration 1: Vérification de la structure des tables
        {
            'name': 'check_intervention_notes_structure',
            'query': """
                ALTER TABLE intervention_notes 
                MODIFY COLUMN note_type ENUM('private', 'internal', 'customer') NOT NULL DEFAULT 'private'
            """,
            'check': "SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'intervention_notes' AND COLUMN_NAME = 'note_type'"
        },
        
        # Migration 2: Ajout de la colonne customer_id si manquante
        {
            'name': 'add_customer_id_to_work_orders',
            'query': """
                ALTER TABLE work_orders 
                ADD COLUMN IF NOT EXISTS customer_id int(11) DEFAULT NULL AFTER created_by_user_id,
                ADD KEY IF NOT EXISTS customer_id (customer_id)
            """,
            'check': "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'work_orders' AND COLUMN_NAME = 'customer_id'"
        }
    ]
    
    success_count = 0
    for migration in migrations:
        try:
            # Vérifier si la migration est nécessaire
            check_result = db_manager.execute_query(migration['check'], fetch_one=True)
            
            if migration['name'] == 'check_intervention_notes_structure':
                # Vérifier si la colonne a le bon type
                if check_result and 'customer' not in str(check_result.get('COLUMN_TYPE', '')):
                    db_manager.execute_query(migration['query'])
                    logger.info(f"Migration {migration['name']} appliquée")
                    success_count += 1
                else:
                    logger.info(f"Migration {migration['name']} déjà appliquée")
                    success_count += 1
            
            elif migration['name'] == 'add_customer_id_to_work_orders':
                # Vérifier si la colonne existe
                if not check_result:
                    db_manager.execute_query(migration['query'])
                    logger.info(f"Migration {migration['name']} appliquée")
                    success_count += 1
                else:
                    logger.info(f"Migration {migration['name']} déjà appliquée")
                    success_count += 1
                    
        except Exception as e:
            logger.error(f"Erreur lors de la migration {migration['name']}: {e}")
    
    logger.info(f"Migrations terminées: {success_count}/{len(migrations)} réussies")
    return success_count == len(migrations)

def seed_database():
    """Insérer des données de test dans la base de données"""
    logger.info("Insertion des données de test...")
    
    # Données utilisateurs
    users_data = [
        (1, 'Admin System', 'admin@chronotech.fr', 'hashed_password_admin', 'admin'),
        (2, 'Marie Technicienne', 'marie@chronotech.fr', 'hashed_password_marie', 'technician'),
        (3, 'Luc Superviseur', 'luc@chronotech.fr', 'hashed_password_luc', 'supervisor'),
        (4, 'Sophie Manager', 'sophie@chronotech.fr', 'hashed_password_sophie', 'manager')
    ]
    
    # Données clients
    customers_data = [
        (1, 'Martin Dubois', 'Entreprise ABC', 'martin.dubois@abc.fr', '0123456789', '123 Rue de la Paix, 75001 Paris', 'Véhicule utilitaire Renault Master 2020'),
        (2, 'Sophie Laurent', 'Société XYZ', 'sophie.laurent@xyz.fr', '0987654321', '456 Avenue des Champs, 69002 Lyon', 'Camion Iveco Daily 2019'),
        (3, 'Pierre Moreau', 'SARL Tech Plus', 'pierre.moreau@techplus.fr', '0555123456', '789 Boulevard Tech, 13001 Marseille', 'Fourgon Peugeot Boxer 2021')
    ]
    
    # Données work orders
    work_orders_data = [
        (1, 'WO-2025-001', 'Entreprise ABC', '123 Rue de la Paix, 75001 Paris', '0123456789', 'Maintenance préventive système climatisation', 'medium', 'assigned', 2, 1, 1, 180, '2025-08-15 09:00:00'),
        (2, 'WO-2025-002', 'Société XYZ', '456 Avenue des Champs, 69002 Lyon', '0987654321', 'Réparation urgente - Panne électrique', 'urgent', 'in_progress', 2, 3, 2, 120, '2025-08-12 14:00:00'),
        (3, 'WO-2025-003', 'SARL Tech Plus', '789 Boulevard Tech, 13001 Marseille', '0555123456', 'Installation nouveau matériel', 'high', 'pending', None, 3, 3, 240, '2025-08-16 08:30:00')
    ]
    
    try:
        # Insertion des utilisateurs
        insert_users_query = """
            INSERT IGNORE INTO users (id, name, email, password, role) 
            VALUES (%s, %s, %s, %s, %s)
        """
        for user in users_data:
            db_manager.execute_query(insert_users_query, user)
        
        # Insertion des clients
        insert_customers_query = """
            INSERT IGNORE INTO customers (id, name, company, email, phone, address, vehicle_info) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        for customer in customers_data:
            db_manager.execute_query(insert_customers_query, customer)
        
        # Insertion des work orders
        insert_work_orders_query = """
            INSERT IGNORE INTO work_orders (id, claim_number, customer_name, customer_address, customer_phone, description, priority, status, assigned_technician_id, created_by_user_id, customer_id, estimated_duration, scheduled_date) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        for work_order in work_orders_data:
            db_manager.execute_query(insert_work_orders_query, work_order)
        
        logger.info("Données de test insérées avec succès")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de l'insertion des données de test: {e}")
        return False

def cleanup_database():
    """Nettoyer les anciennes données"""
    logger.info("Nettoyage de la base de données...")
    
    cleanup_queries = [
        # Nettoyage des sessions expirées
        "DELETE FROM user_sessions WHERE expires_at < NOW()",
        
        # Nettoyage des notifications anciennes lues
        "DELETE FROM notifications WHERE is_read = TRUE AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY)",
        
        # Nettoyage des logs d'activité anciens (garder 90 jours)
        "DELETE FROM activity_logs WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY)"
    ]
    
    try:
        for query in cleanup_queries:
            affected_rows = db_manager.execute_query(query)
            logger.info(f"Nettoyage terminé: {affected_rows} lignes supprimées")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage: {e}")
        return False

def get_database_stats():
    """Obtenir les statistiques de la base de données"""
    try:
        stats_query = """
            SELECT 
                (SELECT COUNT(*) FROM users) as total_users,
                (SELECT COUNT(*) FROM customers) as total_customers,
                (SELECT COUNT(*) FROM work_orders) as total_work_orders,
                (SELECT COUNT(*) FROM work_orders WHERE status = 'pending') as pending_orders,
                (SELECT COUNT(*) FROM work_orders WHERE status = 'in_progress') as active_orders,
                (SELECT COUNT(*) FROM work_orders WHERE status = 'completed') as completed_orders,
                (SELECT COUNT(*) FROM intervention_notes) as total_notes,
                (SELECT COUNT(*) FROM intervention_media) as total_media
        """
        
        return db_manager.execute_query(stats_query, fetch_one=True)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
        return None

# Fonctions helper pour les contrôleurs
def log_activity(user_id, action, entity_type=None, entity_id=None, details=None, ip_address=None, user_agent=None):
    """Enregistrer une activité utilisateur"""
    try:
        query = """
            INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (user_id, action, entity_type, entity_id, details, ip_address, user_agent)
        db_manager.execute_query(query, params)
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement de l'activité: {e}")

def create_notification(user_id, title, message, notification_type='info', related_id=None, related_type=None):
    """Créer une notification pour un utilisateur"""
    try:
        query = """
            INSERT INTO notifications (user_id, title, message, type, related_id, related_type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (user_id, title, message, notification_type, related_id, related_type)
        db_manager.execute_query(query, params)
        logger.info(f"Notification créée pour l'utilisateur {user_id}")
    except Exception as e:
        logger.error(f"Erreur lors de la création de la notification: {e}")

if __name__ == "__main__":
    # Configuration des logs pour les tests
    logging.basicConfig(level=logging.INFO)
    
    # Test de connexion
    try:
        setup_database()
        migrate_database()
        seed_database()
        stats = get_database_stats()
        print("Statistiques de la base de données:", stats)
    except Exception as e:
        print(f"Erreur: {e}")
    finally:
        db_manager.close_connection()
