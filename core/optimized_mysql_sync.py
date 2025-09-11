"""
ChronoTech - Gestionnaire de Synchronisation Optimisé MySQL-First
Version corrigée sans verrous SQLite et privilégiant MySQL
"""
import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import mysql.connector
from mysql.connector import Error

logger = logging.getLogger(__name__)

class OptimizedSyncManager:
    """Gestionnaire de synchronisation optimisé MySQL-First"""
    
    def __init__(self, mysql_config: Dict, offline_db_path: str = 'data/offline.db'):
        self.mysql_config = mysql_config
        self.offline_db_path = offline_db_path
        self.sync_interval = 10  # Réduit à 10 secondes
        self.is_online = True  # Par défaut MySQL prioritaire
        self.sync_running = False
        self.sync_thread = None
        self._connection_pool = []
        self._max_pool_size = 3
        
        # Stats de synchronisation
        self.sync_stats = {
            'last_sync': None,
            'total_synced': 0,
            'sync_errors': 0,
            'pending_items': 0,
            'mysql_primary': True
        }
        
        # Initialisation optimisée
        self._init_optimized_sync()
    
    def _init_optimized_sync(self):
        """Initialisation optimisée privilégiant MySQL"""
        try:
            # Test de connexion MySQL
            if self._test_mysql_connection():
                self.is_online = True
                logger.info("✅ MySQL disponible - Mode synchronisé activé")
                
                # Créer les tables MySQL si nécessaires
                self._ensure_mysql_sync_tables()
                
                # Initialiser SQLite minimal (sans verrous longs)
                self._init_minimal_sqlite()
                
            else:
                self.is_online = False
                logger.warning("⚠️ MySQL indisponible - Mode offline activé")
                self._init_full_sqlite()
                
        except Exception as e:
            logger.error(f"❌ Erreur initialisation sync: {e}")
            self.is_online = False
    
    def _test_mysql_connection(self) -> bool:
        """Test rapide de connexion MySQL"""
        try:
            conn = mysql.connector.connect(
                host=self.mysql_config['host'],
                user=self.mysql_config['user'],
                password=self.mysql_config['password'],
                database=self.mysql_config['database'],
                connection_timeout=5  # Timeout court
            )
            conn.close()
            return True
        except Exception:
            return False
    
    def _ensure_mysql_sync_tables(self):
        """S'assurer que les tables MySQL de synchronisation existent"""
        try:
            conn = mysql.connector.connect(**self.mysql_config)
            cursor = conn.cursor()
            
            # Table pour le statut de synchronisation
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_status (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    table_name VARCHAR(64) NOT NULL,
                    record_id INT NOT NULL,
                    sync_type ENUM('insert', 'update', 'delete') NOT NULL,
                    sync_data JSON,
                    status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_table_record (table_name, record_id),
                    INDEX idx_status (status)
                )
            """)
            
            # Table pour les actions offline (si nécessaire)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS offline_actions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    action_type VARCHAR(64) NOT NULL,
                    table_name VARCHAR(64) NOT NULL,
                    record_data JSON NOT NULL,
                    technician_id INT,
                    device_id VARCHAR(128),
                    offline_timestamp TIMESTAMP NOT NULL,
                    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_technician (technician_id),
                    INDEX idx_offline_time (offline_timestamp)
                )
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("📊 Tables MySQL pour la synchronisation créées")
            
        except Exception as e:
            logger.error(f"❌ Erreur création tables MySQL sync: {e}")
    
    def _init_minimal_sqlite(self):
        """Initialisation SQLite minimale (mode MySQL prioritaire)"""
        try:
            # Créer uniquement si nécessaire et avec timeout court
            if not os.path.exists(self.offline_db_path):
                os.makedirs(os.path.dirname(self.offline_db_path), exist_ok=True)
                
                # Connexion avec timeout et mode WAL pour éviter les verrous
                conn = sqlite3.connect(
                    self.offline_db_path, 
                    timeout=2.0,
                    check_same_thread=False
                )
                
                # Mode WAL pour éviter les verrous de lecture/écriture
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA busy_timeout=1000")
                
                cursor = conn.cursor()
                
                # Table ultra-simple pour les actions offline critiques uniquement
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS critical_offline_actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        synced INTEGER DEFAULT 0
                    )
                """)
                
                conn.commit()
                conn.close()
                logger.info("✅ SQLite minimal initialisé (mode MySQL-first)")
                
        except Exception as e:
            logger.error(f"❌ Erreur SQLite minimal: {e}")
    
    def _init_full_sqlite(self):
        """Initialisation SQLite complète (mode offline)"""
        try:
            os.makedirs(os.path.dirname(self.offline_db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.offline_db_path, timeout=5.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            
            cursor = conn.cursor()
            
            # Tables complètes pour mode offline
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS offline_work_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_id INTEGER,
                    status TEXT NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced INTEGER DEFAULT 0
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS offline_media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_order_id INTEGER,
                    file_path TEXT NOT NULL,
                    file_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced INTEGER DEFAULT 0
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("✅ SQLite complet initialisé (mode offline)")
            
        except Exception as e:
            logger.error(f"❌ Erreur SQLite complet: {e}")
    
    def start_sync_service(self):
        """Démarrer le service de synchronisation optimisé"""
        if self.sync_running:
            return
            
        self.sync_running = True
        self.sync_thread = threading.Thread(
            target=self._sync_loop_optimized,
            daemon=True,
            name="OptimizedSyncThread"
        )
        self.sync_thread.start()
        logger.info("🔄 Service de synchronisation optimisé démarré")
    
    def _sync_loop_optimized(self):
        """Boucle de synchronisation optimisée"""
        while self.sync_running:
            try:
                if self.is_online:
                    # Mode MySQL prioritaire - synchronisation légère
                    self._light_sync_check()
                else:
                    # Mode offline - synchronisation complète quand possible
                    if self._test_mysql_connection():
                        self.is_online = True
                        self._full_sync_recovery()
                
                # Attendre avant le prochain cycle
                time.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"❌ Erreur boucle sync: {e}")
                time.sleep(self.sync_interval * 2)  # Attendre plus longtemps en cas d'erreur
    
    def _light_sync_check(self):
        """Vérification légère de synchronisation (mode MySQL)"""
        try:
            # Vérifier s'il y a des actions critiques à synchroniser
            if os.path.exists(self.offline_db_path):
                conn = sqlite3.connect(self.offline_db_path, timeout=1.0)
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM critical_offline_actions WHERE synced = 0")
                pending_count = cursor.fetchone()[0]
                
                if pending_count > 0:
                    self._sync_critical_actions(cursor)
                
                conn.close()
                
            # Mettre à jour les stats
            self.sync_stats['last_sync'] = datetime.now().isoformat()
            self.sync_stats['pending_items'] = pending_count if 'pending_count' in locals() else 0
            
        except sqlite3.OperationalError:
            # Base verrouillée - ignorer silencieusement en mode MySQL-first
            pass
        except Exception as e:
            logger.warning(f"⚠️ Sync léger: {e}")
    
    def _sync_critical_actions(self, cursor):
        """Synchroniser les actions critiques vers MySQL"""
        try:
            cursor.execute("SELECT id, action_data FROM critical_offline_actions WHERE synced = 0 LIMIT 10")
            actions = cursor.fetchall()
            
            if not actions:
                return
            
            # Connexion MySQL
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            mysql_cursor = mysql_conn.cursor()
            
            for action_id, action_data_str in actions:
                try:
                    action_data = json.loads(action_data_str)
                    
                    # Insérer dans la table MySQL appropriée
                    if action_data.get('type') == 'work_order_update':
                        mysql_cursor.execute("""
                            INSERT INTO offline_actions 
                            (action_type, table_name, record_data, technician_id, offline_timestamp)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            action_data.get('type'),
                            'work_orders',
                            json.dumps(action_data),
                            action_data.get('technician_id'),
                            action_data.get('timestamp', datetime.now())
                        ))
                    
                    # Marquer comme synchronisé
                    cursor.execute("UPDATE critical_offline_actions SET synced = 1 WHERE id = ?", (action_id,))
                    self.sync_stats['total_synced'] += 1
                    
                except Exception as e:
                    logger.error(f"❌ Erreur sync action {action_id}: {e}")
            
            mysql_conn.commit()
            mysql_cursor.close()
            mysql_conn.close()
            
        except Exception as e:
            logger.error(f"❌ Erreur sync actions critiques: {e}")
    
    def add_offline_action(self, action_data: Dict):
        """Ajouter une action offline (priorité MySQL si disponible)"""
        if self.is_online:
            # Mode MySQL - enregistrer directement
            try:
                conn = mysql.connector.connect(**self.mysql_config)
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO offline_actions 
                    (action_type, table_name, record_data, technician_id, offline_timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    action_data.get('type', 'unknown'),
                    action_data.get('table', 'unknown'),
                    json.dumps(action_data),
                    action_data.get('technician_id'),
                    datetime.now()
                ))
                
                conn.commit()
                cursor.close()
                conn.close()
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ MySQL indisponible, fallback SQLite: {e}")
                self.is_online = False
        
        # Mode offline - SQLite
        try:
            conn = sqlite3.connect(self.offline_db_path, timeout=2.0)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO critical_offline_actions (action_data)
                VALUES (?)
            """, (json.dumps(action_data),))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Impossible d'enregistrer action offline: {e}")
            return False
    
    def get_sync_status(self) -> Dict:
        """Obtenir le statut de synchronisation"""
        return {
            **self.sync_stats,
            'is_online': self.is_online,
            'mysql_available': self._test_mysql_connection(),
            'sync_running': self.sync_running
        }
    
    def stop_sync_service(self):
        """Arrêter le service de synchronisation"""
        self.sync_running = False
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)
        logger.info("🛑 Service de synchronisation arrêté")


# Instance globale optimisée
optimized_sync_manager = None

def get_optimized_sync_manager(mysql_config: Dict = None) -> OptimizedSyncManager:
    """Obtenir l'instance du gestionnaire de synchronisation optimisé"""
    global optimized_sync_manager
    
    if optimized_sync_manager is None and mysql_config:
        optimized_sync_manager = OptimizedSyncManager(mysql_config)
        optimized_sync_manager.start_sync_service()
    
    return optimized_sync_manager
