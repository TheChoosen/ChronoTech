"""
ChronoTech Sprint 2 - Système de Synchronisation Offline
Synchronisation SQLite local avec MySQL cloud
"""
import asyncio
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import aiohttp
import mysql.connector
from mysql.connector import Error
import threading
import queue

logger = logging.getLogger(__name__)

class OfflineSyncManager:
    """Gestionnaire de synchronisation entre SQLite local et MySQL cloud"""
    
    def __init__(self, mysql_config: Dict, offline_db_path: str = 'data/offline.db'):
        self.mysql_config = mysql_config
        self.offline_db_path = offline_db_path
        self.sync_interval = 30  # Secondes entre les tentatives de sync
        self.max_retry_attempts = 3
        self.is_online = False
        self.sync_running = False
        self.sync_thread = None
        self.sync_stats = {
            'last_sync': None,
            'total_synced': 0,
            'sync_errors': 0,
            'pending_items': 0
        }
        
        # Queue pour les synchronisations prioritaires
        self.priority_sync_queue = queue.Queue()
        
        # Initialiser la base SQLite locale
        self._init_offline_database()
        
    def _init_offline_database(self):
        """Initialiser la base de données SQLite pour le mode offline"""
        try:
            # Créer le dossier data s'il n'existe pas
            os.makedirs(os.path.dirname(self.offline_db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.offline_db_path)
            cursor = conn.cursor()
            
            # Vérifier et migrer si nécessaire
            self._migrate_offline_database(cursor)
            
            conn.commit()
            conn.close()
            logger.info("✅ Base de données SQLite initialisée")
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation base SQLite: {e}")
    
    def _migrate_offline_database(self, cursor):
        """Migrer la base de données SQLite si nécessaire"""
        try:
            # Vérifier si les tables existent
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            # Si aucunes tables, créer toutes les tables
            if not existing_tables:
                self._create_all_offline_tables(cursor)
                return

            # Vérifier la structure de TOUTES les tables existantes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            all_tables = [row[0] for row in cursor.fetchall()]
            
            for table_name in all_tables:
                # Vérifier si la colonne updated_at existe
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'updated_at' not in columns:
                    # Ajouter la colonne updated_at
                    try:
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                        logger.info(f"✅ Colonne updated_at ajoutée à {table_name}")
                    except Exception as e:
                        logger.warning(f"⚠️ Impossible d'ajouter updated_at à {table_name}: {e}")
            
            # Créer les tables manquantes
            self._create_all_offline_tables(cursor)
            
        except Exception as e:
            logger.error(f"❌ Erreur migration base SQLite: {e}")
            # En cas d'erreur, recréer toutes les tables
            self._create_all_offline_tables(cursor)
    
    def _create_all_offline_tables(self, cursor):
        """Créer toutes les tables SQLite offline"""
        # Table pour les bons de travail offline
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_work_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                notes TEXT,
                sync_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table pour les commandes vocales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_voice_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_text TEXT NOT NULL,
                work_order_id INTEGER,
                action_type TEXT NOT NULL,
                sync_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table pour les fichiers média
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_media_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id INTEGER,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                sync_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table pour la queue générale
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL,
                item_data TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                sync_status TEXT DEFAULT 'pending',
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def start_sync_service(self):
        """Démarrer le service de synchronisation en arrière-plan"""
        if not self.sync_running:
            self.sync_running = True
            self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
            self.sync_thread.start()
            logger.info("🔄 Service de synchronisation démarré")
    
    def stop_sync_service(self):
        """Arrêter le service de synchronisation"""
        self.sync_running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        logger.info("⏹️ Service de synchronisation arrêté")
    
    def _sync_loop(self):
        """Boucle principale de synchronisation"""
        while self.sync_running:
            try:
                # Vérifier la connectivité
                self._check_connectivity()
                
                if self.is_online:
                    # Traiter les synchronisations prioritaires
                    self._process_priority_sync()
                    
                    # Synchronisation complète
                    self._perform_full_sync()
                    
                    # Mettre à jour les statistiques
                    self._update_sync_stats()
                
                # Attendre avant la prochaine synchronisation
                time.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de synchronisation: {e}")
                self.sync_stats['sync_errors'] += 1
                time.sleep(self.sync_interval * 2)  # Attendre plus longtemps en cas d'erreur
    
    def _check_connectivity(self) -> bool:
        """Vérifier la connectivité réseau et base de données"""
        try:
            # Test de connexion MySQL
            connection = mysql.connector.connect(**self.mysql_config, connection_timeout=5)
            if connection.is_connected():
                connection.close()
                self.is_online = True
                return True
        except Error as e:
            logger.debug(f"Pas de connexion MySQL: {e}")
        except Exception as e:
            logger.debug(f"Erreur de connectivité: {e}")
        
        self.is_online = False
        return False
    
    def _process_priority_sync(self):
        """Traiter les éléments prioritaires de synchronisation"""
        while not self.priority_sync_queue.empty():
            try:
                sync_item = self.priority_sync_queue.get_nowait()
                self._sync_single_item(sync_item)
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Erreur sync prioritaire: {e}")
    
    def _perform_full_sync(self):
        """Effectuer une synchronisation complète"""
        try:
            # 1. Synchroniser les bons de travail
            self._sync_work_orders()
            
            # 2. Synchroniser les commandes vocales
            self._sync_voice_commands()
            
            # 3. Synchroniser les fichiers média
            self._sync_media_files()
            
            # 4. Synchroniser la queue générale
            self._sync_queue_items()
            
            # 5. Nettoyer les éléments synchronisés anciens
            self._cleanup_synced_items()
            
            logger.info("✅ Synchronisation complète terminée")
            
        except Exception as e:
            logger.error(f"Erreur synchronisation complète: {e}")
            self.sync_stats['sync_errors'] += 1
    
    def _sync_work_orders(self):
        """Synchroniser les bons de travail offline vers MySQL"""
        offline_conn = sqlite3.connect(self.offline_db_path)
        offline_conn.row_factory = sqlite3.Row
        offline_cursor = offline_conn.cursor()
        
        # Récupérer les work orders à synchroniser
        offline_cursor.execute('''
            SELECT * FROM offline_work_orders 
            WHERE sync_status = 'pending'
            ORDER BY updated_at ASC
        ''')
        
        work_orders = offline_cursor.fetchall()
        
        if work_orders:
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            mysql_cursor = mysql_conn.cursor()
            
            for wo in work_orders:
                try:
                    # Mettre à jour dans MySQL
                    mysql_cursor.execute('''
                        UPDATE work_orders 
                        SET status = %s, notes = CONCAT(IFNULL(notes, ''), %s), 
                            updated_at = %s
                        WHERE id = %s
                    ''', (
                        wo['status'],
                        f"\n[Voice] {wo['notes']}" if wo['notes'] else "",
                        wo['updated_at'],
                        wo['original_id']
                    ))
                    
                    # Marquer comme synchronisé
                    offline_cursor.execute('''
                        UPDATE offline_work_orders 
                        SET sync_status = 'synced' 
                        WHERE id = ?
                    ''', (wo['id'],))
                    
                    self.sync_stats['total_synced'] += 1
                    logger.debug(f"Work order {wo['original_id']} synchronisé")
                    
                except Error as e:
                    logger.error(f"Erreur sync work order {wo['original_id']}: {e}")
                    offline_cursor.execute('''
                        UPDATE offline_work_orders 
                        SET sync_status = 'error' 
                        WHERE id = ?
                    ''', (wo['id'],))
            
            mysql_conn.commit()
            mysql_conn.close()
        
        offline_conn.commit()
        offline_conn.close()
    
    def _sync_voice_commands(self):
        """Synchroniser les commandes vocales vers MySQL"""
        offline_conn = sqlite3.connect(self.offline_db_path)
        offline_conn.row_factory = sqlite3.Row
        offline_cursor = offline_conn.cursor()
        
        # Récupérer les commandes vocales à synchroniser
        offline_cursor.execute('''
            SELECT * FROM offline_voice_commands 
            WHERE sync_status = 'pending'
            ORDER BY created_at ASC
        ''')
        
        voice_commands = offline_cursor.fetchall()
        
        if voice_commands:
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            mysql_cursor = mysql_conn.cursor()
            
            for cmd in voice_commands:
                try:
                    if cmd['command_type'] == 'voice_note':
                        # Insérer comme note d'intervention
                        mysql_cursor.execute('''
                            INSERT INTO intervention_notes 
                            (work_order_id, note, note_type, created_at)
                            VALUES (%s, %s, 'voice', %s)
                        ''', (
                            cmd['work_order_id'],
                            cmd['voice_text'],
                            cmd['created_at']
                        ))
                    
                    elif cmd['command_type'] == 'issue_report':
                        # Créer un incident
                        mysql_cursor.execute('''
                            INSERT INTO issues 
                            (work_order_id, description, severity, reported_via, created_at)
                            VALUES (%s, %s, 'medium', 'voice', %s)
                        ''', (
                            cmd['work_order_id'],
                            cmd['voice_text'],
                            cmd['created_at']
                        ))
                    
                    # Archiver l'historique des commandes vocales
                    mysql_cursor.execute('''
                        INSERT INTO voice_command_history 
                        (work_order_id, command_type, transcription, confidence_score, processed_at)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (
                        cmd['work_order_id'],
                        cmd['command_type'],
                        cmd['voice_text'],
                        cmd['confidence_score'],
                        cmd['created_at']
                    ))
                    
                    # Marquer comme synchronisé
                    offline_cursor.execute('''
                        UPDATE offline_voice_commands 
                        SET sync_status = 'synced' 
                        WHERE id = ?
                    ''', (cmd['id'],))
                    
                    self.sync_stats['total_synced'] += 1
                    logger.debug(f"Commande vocale {cmd['id']} synchronisée")
                    
                except Error as e:
                    logger.error(f"Erreur sync commande vocale {cmd['id']}: {e}")
                    offline_cursor.execute('''
                        UPDATE offline_voice_commands 
                        SET sync_status = 'error' 
                        WHERE id = ?
                    ''', (cmd['id'],))
            
            mysql_conn.commit()
            mysql_conn.close()
        
        offline_conn.commit()
        offline_conn.close()
    
    def _sync_media_files(self):
        """Synchroniser les fichiers média (photos, audio) vers le cloud"""
        offline_conn = sqlite3.connect(self.offline_db_path)
        offline_conn.row_factory = sqlite3.Row
        offline_cursor = offline_conn.cursor()
        
        # Récupérer les fichiers média à synchroniser
        offline_cursor.execute('''
            SELECT * FROM offline_media 
            WHERE sync_status = 'pending'
            ORDER BY created_at ASC
        ''')
        
        media_files = offline_cursor.fetchall()
        
        for media in media_files:
            try:
                # Upload du fichier (simulation - implémenter upload S3/cloud)
                uploaded_url = self._upload_media_file(media['file_path'])
                
                if uploaded_url:
                    # Enregistrer l'URL dans MySQL
                    mysql_conn = mysql.connector.connect(**self.mysql_config)
                    mysql_cursor = mysql_conn.cursor()
                    
                    mysql_cursor.execute('''
                        INSERT INTO work_order_media 
                        (work_order_id, file_url, file_type, transcription, uploaded_at)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (
                        media['work_order_id'],
                        uploaded_url,
                        media['file_type'],
                        media['transcription'],
                        media['created_at']
                    ))
                    
                    mysql_conn.commit()
                    mysql_conn.close()
                    
                    # Marquer comme synchronisé
                    offline_cursor.execute('''
                        UPDATE offline_media 
                        SET sync_status = 'synced' 
                        WHERE id = ?
                    ''', (media['id'],))
                    
                    self.sync_stats['total_synced'] += 1
                    logger.debug(f"Fichier média {media['id']} synchronisé")
                
            except Exception as e:
                logger.error(f"Erreur sync média {media['id']}: {e}")
                offline_cursor.execute('''
                    UPDATE offline_media 
                    SET sync_status = 'error' 
                    WHERE id = ?
                ''', (media['id'],))
        
        offline_conn.commit()
        offline_conn.close()
    
    def _sync_queue_items(self):
        """Synchroniser les éléments de la queue générale"""
        offline_conn = sqlite3.connect(self.offline_db_path)
        offline_conn.row_factory = sqlite3.Row
        offline_cursor = offline_conn.cursor()
        
        # Récupérer les éléments de la queue à synchroniser
        offline_cursor.execute('''
            SELECT * FROM sync_queue 
            WHERE status = 'pending' AND attempts < ?
            ORDER BY created_at ASC
            LIMIT 50
        ''', (self.max_retry_attempts,))
        
        queue_items = offline_cursor.fetchall()
        
        if queue_items:
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            mysql_cursor = mysql_conn.cursor()
            
            for item in queue_items:
                try:
                    data = json.loads(item['data'])
                    
                    if item['action'] == 'insert':
                        self._execute_insert(mysql_cursor, item['table_name'], data)
                    elif item['action'] == 'update':
                        self._execute_update(mysql_cursor, item['table_name'], item['record_id'], data)
                    elif item['action'] == 'delete':
                        self._execute_delete(mysql_cursor, item['table_name'], item['record_id'])
                    
                    # Marquer comme synchronisé
                    offline_cursor.execute('''
                        UPDATE sync_queue 
                        SET status = 'synced', last_attempt = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (item['id'],))
                    
                    self.sync_stats['total_synced'] += 1
                    
                except Exception as e:
                    logger.error(f"Erreur sync queue item {item['id']}: {e}")
                    
                    # Incrémenter les tentatives
                    offline_cursor.execute('''
                        UPDATE sync_queue 
                        SET attempts = attempts + 1, last_attempt = CURRENT_TIMESTAMP,
                            status = CASE 
                                WHEN attempts + 1 >= ? THEN 'failed' 
                                ELSE 'pending' 
                            END
                        WHERE id = ?
                    ''', (self.max_retry_attempts, item['id']))
            
            mysql_conn.commit()
            mysql_conn.close()
        
        offline_conn.commit()
        offline_conn.close()
    
    def _execute_insert(self, cursor, table_name: str, data: Dict):
        """Exécuter une insertion dans MySQL"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        values = list(data.values())
        
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        cursor.execute(query, values)
    
    def _execute_update(self, cursor, table_name: str, record_id: int, data: Dict):
        """Exécuter une mise à jour dans MySQL"""
        set_clause = ', '.join([f"{key} = %s" for key in data.keys()])
        values = list(data.values()) + [record_id]
        
        query = f"UPDATE {table_name} SET {set_clause} WHERE id = %s"
        cursor.execute(query, values)
    
    def _execute_delete(self, cursor, table_name: str, record_id: int):
        """Exécuter une suppression dans MySQL"""
        query = f"DELETE FROM {table_name} WHERE id = %s"
        cursor.execute(query, (record_id,))
    
    def _upload_media_file(self, file_path: str) -> Optional[str]:
        """Upload d'un fichier média vers le cloud (simulation)"""
        # En production, implémenter upload vers S3, Google Cloud, etc.
        import os
        import hashlib
        
        if os.path.exists(file_path):
            # Simuler l'upload
            file_hash = hashlib.md5(file_path.encode()).hexdigest()
            simulated_url = f"https://chronotech-media.cloud/{file_hash}/{os.path.basename(file_path)}"
            
            # Simulation d'upload réussi
            time.sleep(0.1)  # Simuler le temps d'upload
            return simulated_url
        
        return None
    
    def _cleanup_synced_items(self):
        """Nettoyer les éléments synchronisés anciens"""
        offline_conn = sqlite3.connect(self.offline_db_path)
        offline_cursor = offline_conn.cursor()
        
        # Supprimer les éléments synchronisés vieux de plus de 7 jours
        cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()
        
        tables_to_clean = [
            'offline_work_orders',
            'offline_voice_commands', 
            'offline_media',
            'sync_queue'
        ]
        
        for table in tables_to_clean:
            offline_cursor.execute(f'''
                DELETE FROM {table} 
                WHERE sync_status = 'synced' AND updated_at < ?
            ''', (cutoff_date,))
        
        offline_conn.commit()
        offline_conn.close()
        
        logger.debug("🧹 Nettoyage des éléments synchronisés anciens")
    
    def _update_sync_stats(self):
        """Mettre à jour les statistiques de synchronisation"""
        try:
            offline_conn = sqlite3.connect(self.offline_db_path, timeout=10.0)
            offline_cursor = offline_conn.cursor()
        
            # Compter les éléments en attente avec gestion d'erreurs
            pending_count = 0
            try:
                offline_cursor.execute('SELECT COUNT(*) FROM offline_work_orders WHERE sync_status = "pending"')
                pending_count += offline_cursor.fetchone()[0]
            except sqlite3.OperationalError:
                pass
                
            try:
                offline_cursor.execute('SELECT COUNT(*) FROM offline_voice_commands WHERE sync_status = "pending"')
                pending_count += offline_cursor.fetchone()[0]
            except sqlite3.OperationalError:
                pass
                
            try:
                offline_cursor.execute('SELECT COUNT(*) FROM offline_media WHERE sync_status = "pending"')
                pending_count += offline_cursor.fetchone()[0]
            except sqlite3.OperationalError:
                pass
                
            try:
                offline_cursor.execute('SELECT COUNT(*) FROM sync_queue WHERE status = "pending"')
                pending_count += offline_cursor.fetchone()[0]
            except sqlite3.OperationalError:
                pass
                
            self.sync_stats['pending_items'] = pending_count
            self.sync_stats['last_sync'] = datetime.now().isoformat()
            
            offline_conn.close()
            
        except Exception as e:
            logger.error(f"Erreur mise à jour stats sync: {e}")
    
    def add_priority_sync(self, sync_item: Dict):
        """Ajouter un élément à la synchronisation prioritaire"""
        self.priority_sync_queue.put(sync_item)
    
    def force_sync_now(self) -> Dict:
        """Forcer une synchronisation immédiate"""
        if not self.is_online:
            return {
                'success': False,
                'message': 'Pas de connexion réseau disponible'
            }
        
        try:
            self._perform_full_sync()
            return {
                'success': True,
                'message': 'Synchronisation forcée terminée',
                'stats': self.sync_stats
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur lors de la synchronisation: {e}'
            }
    
    def get_sync_status(self) -> Dict:
        """Récupérer le statut de synchronisation"""
        return {
            'is_online': self.is_online,
            'sync_running': self.sync_running,
            'stats': self.sync_stats,
            'next_sync_in': self.sync_interval if self.sync_running else None
        }
    
    def _sync_single_item(self, sync_item: Dict):
        """Synchroniser un élément unique"""
        # Implémentation de synchronisation d'un élément spécifique
        pass

# Fonction utilitaire pour créer les tables MySQL nécessaires
def create_mysql_tables(mysql_config: Dict):
    """Créer les tables MySQL nécessaires pour la synchronisation"""
    connection = mysql.connector.connect(**mysql_config)
    cursor = connection.cursor()
    
    # Table pour l'historique des commandes vocales
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voice_command_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            work_order_id INT,
            command_type VARCHAR(50) NOT NULL,
            transcription TEXT,
            confidence_score DECIMAL(3,2),
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_work_order (work_order_id),
            INDEX idx_command_type (command_type)
        ) ENGINE=InnoDB
    ''')
    
    # Table pour les fichiers média des work orders
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_order_media (
            id INT AUTO_INCREMENT PRIMARY KEY,
            work_order_id INT NOT NULL,
            file_url VARCHAR(500) NOT NULL,
            file_type VARCHAR(50),
            transcription TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_work_order (work_order_id)
        ) ENGINE=InnoDB
    ''')
    
    # Table pour les incidents signalés
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id INT AUTO_INCREMENT PRIMARY KEY,
            work_order_id INT,
            description TEXT NOT NULL,
            severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
            reported_via VARCHAR(50) DEFAULT 'manual',
            status ENUM('open', 'in_progress', 'resolved', 'closed') DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP NULL,
            INDEX idx_work_order (work_order_id),
            INDEX idx_severity (severity),
            INDEX idx_status (status)
        ) ENGINE=InnoDB
    ''')
    
    connection.commit()
    connection.close()
    
    logger.info("📊 Tables MySQL pour la synchronisation créées")


# Instance globale du gestionnaire de synchronisation
sync_manager = None

def init_sync_manager(mysql_config: Dict, offline_db_path: str = 'data/offline.db'):
    """Initialiser le gestionnaire de synchronisation"""
    global sync_manager
    sync_manager = OfflineSyncManager(mysql_config, offline_db_path)
    
    # Créer les tables MySQL nécessaires
    create_mysql_tables(mysql_config)
    
    return sync_manager
