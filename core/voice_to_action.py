"""
ChronoTech Sprint 2 - Module Voice-to-Action
Système de commandes vocales pour techniciens terrain
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import sqlite3
import os
import threading
import queue
import time

logger = logging.getLogger(__name__)

class VoiceToActionEngine:
    """Moteur de reconnaissance et traitement des commandes vocales technicien"""
    
    def __init__(self, offline_db_path='data/offline.db'):
        self.offline_db_path = offline_db_path
        self.command_patterns = self._load_command_patterns()
        self.voice_commands_queue = queue.Queue()
        self.is_listening = False
        self.current_technician_id = None
        
        # Initialiser la base offline
        self._init_offline_db()
        
    def _load_command_patterns(self) -> Dict:
        """Patterns de reconnaissance des commandes vocales"""
        return {
            'start_task': {
                'patterns': [
                    'commencer la tâche',
                    'démarrer l\'intervention',
                    'début de travail',
                    'start task',
                    'commencer',
                    'je commence'
                ],
                'confidence_threshold': 0.7,
                'action': 'start_work_order'
            },
            'complete_task': {
                'patterns': [
                    'terminer la tâche',
                    'finir l\'intervention',
                    'travail terminé',
                    'c\'est fini',
                    'complete task',
                    'terminé'
                ],
                'confidence_threshold': 0.8,
                'action': 'complete_work_order'
            },
            'add_note': {
                'patterns': [
                    'ajouter une note',
                    'prendre note',
                    'note',
                    'observation',
                    'commentaire'
                ],
                'confidence_threshold': 0.6,
                'action': 'add_voice_note'
            },
            'change_status': {
                'patterns': [
                    'changer le statut',
                    'modifier l\'état',
                    'mettre en pause',
                    'pause',
                    'reprendre'
                ],
                'confidence_threshold': 0.7,
                'action': 'change_status'
            },
            'report_issue': {
                'patterns': [
                    'signaler un problème',
                    'problème détecté',
                    'erreur',
                    'dysfonctionnement',
                    'incident'
                ],
                'confidence_threshold': 0.8,
                'action': 'report_issue'
            }
        }
    
    def _init_offline_db(self):
        """Initialiser la base de données SQLite offline"""
        os.makedirs(os.path.dirname(self.offline_db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        # Tables pour le mode offline
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_work_orders (
                id INTEGER PRIMARY KEY,
                original_id INTEGER,
                technician_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                notes TEXT,
                voice_actions TEXT, -- JSON des actions vocales
                media_files TEXT, -- JSON des fichiers média
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'pending' -- pending, synced, error
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_voice_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id INTEGER,
                command_type TEXT NOT NULL,
                voice_text TEXT,
                confidence_score REAL,
                processed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'pending'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id INTEGER,
                file_path TEXT NOT NULL,
                file_type TEXT,
                transcription TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'pending'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                action TEXT NOT NULL, -- insert, update, delete
                data TEXT, -- JSON data
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                attempts INTEGER DEFAULT 0,
                last_attempt TIMESTAMP,
                status TEXT DEFAULT 'pending' -- pending, synced, failed
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("🗃️ Base de données offline initialisée")
    
    def process_voice_command(self, audio_data: bytes, work_order_id: int = None) -> Dict:
        """Traiter une commande vocale"""
        try:
            # Transcription (simulation - en production utiliser Whisper/Google Speech)
            transcription = self._mock_transcription(audio_data)
            
            # Analyse de la commande
            command_result = self._analyze_voice_command(transcription)
            
            if command_result['recognized']:
                # Sauvegarder en offline d'abord
                self._save_voice_command_offline(
                    work_order_id, 
                    command_result['command_type'],
                    transcription,
                    command_result['confidence']
                )
                
                # Exécuter l'action
                action_result = self._execute_voice_action(
                    command_result['action'],
                    work_order_id,
                    transcription,
                    command_result.get('parameters', {})
                )
                
                return {
                    'success': True,
                    'transcription': transcription,
                    'command_type': command_result['command_type'],
                    'confidence': command_result['confidence'],
                    'action_result': action_result,
                    'message': f"Commande '{command_result['command_type']}' exécutée avec succès"
                }
            else:
                return {
                    'success': False,
                    'transcription': transcription,
                    'message': 'Commande non reconnue',
                    'suggestion': 'Essayez: "commencer la tâche", "terminer", "ajouter une note"'
                }
                
        except Exception as e:
            logger.error(f"Erreur traitement commande vocale: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Erreur de traitement vocal'
            }
    
    def _mock_transcription(self, audio_data: bytes) -> str:
        """Simulation de transcription - remplacer par Whisper en production"""
        # Simulation de différentes transcriptions possibles
        mock_transcriptions = [
            "commencer la tâche numéro douze trente quatre",
            "terminer l'intervention",
            "ajouter une note vérification des freins effectuée",
            "problème détecté sur le système hydraulique",
            "travail terminé tout est en ordre"
        ]
        
        # En production, utiliser OpenAI Whisper ou Google Speech-to-Text
        import random
        return random.choice(mock_transcriptions)
    
    def _analyze_voice_command(self, transcription: str) -> Dict:
        """Analyser la transcription pour identifier la commande"""
        transcription_lower = transcription.lower()
        
        best_match = {
            'recognized': False,
            'command_type': None,
            'action': None,
            'confidence': 0.0,
            'parameters': {}
        }
        
        for command_type, config in self.command_patterns.items():
            for pattern in config['patterns']:
                if pattern.lower() in transcription_lower:
                    # Calcul de confiance basique (en production utiliser ML)
                    confidence = len(pattern) / len(transcription_lower)
                    confidence = min(confidence, 1.0)
                    
                    if confidence >= config['confidence_threshold'] and confidence > best_match['confidence']:
                        best_match = {
                            'recognized': True,
                            'command_type': command_type,
                            'action': config['action'],
                            'confidence': confidence,
                            'parameters': self._extract_parameters(transcription, command_type)
                        }
        
        return best_match
    
    def _extract_parameters(self, transcription: str, command_type: str) -> Dict:
        """Extraire les paramètres de la commande"""
        parameters = {}
        
        if command_type == 'add_note':
            # Extraire le contenu de la note
            note_patterns = ['note', 'observation', 'commentaire']
            for pattern in note_patterns:
                if pattern in transcription.lower():
                    # Prendre tout ce qui suit le pattern
                    parts = transcription.lower().split(pattern)
                    if len(parts) > 1:
                        parameters['note_content'] = parts[1].strip()
                        break
            
            if not parameters.get('note_content'):
                parameters['note_content'] = transcription  # Toute la transcription comme note
        
        elif command_type == 'report_issue':
            parameters['issue_description'] = transcription
            parameters['severity'] = 'medium'  # Par défaut
            
            # Détecter la sévérité
            if any(word in transcription.lower() for word in ['urgent', 'critique', 'danger']):
                parameters['severity'] = 'high'
            elif any(word in transcription.lower() for word in ['mineur', 'léger']):
                parameters['severity'] = 'low'
        
        return parameters
    
    def _execute_voice_action(self, action: str, work_order_id: int, transcription: str, parameters: Dict) -> Dict:
        """Exécuter l'action correspondant à la commande vocale"""
        try:
            if action == 'start_work_order':
                return self._start_work_order_voice(work_order_id)
            
            elif action == 'complete_work_order':
                return self._complete_work_order_voice(work_order_id, transcription)
            
            elif action == 'add_voice_note':
                note_content = parameters.get('note_content', transcription)
                return self._add_voice_note(work_order_id, note_content)
            
            elif action == 'change_status':
                return self._change_status_voice(work_order_id, parameters)
            
            elif action == 'report_issue':
                return self._report_issue_voice(work_order_id, parameters)
            
            else:
                return {'success': False, 'message': f'Action {action} non implémentée'}
                
        except Exception as e:
            logger.error(f"Erreur exécution action {action}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _start_work_order_voice(self, work_order_id: int) -> Dict:
        """Démarrer un bon de travail via commande vocale"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        # Mettre à jour en offline d'abord
        cursor.execute('''
            INSERT OR REPLACE INTO offline_work_orders 
            (original_id, technician_id, status, updated_at)
            VALUES (?, ?, 'in_progress', CURRENT_TIMESTAMP)
        ''', (work_order_id, self.current_technician_id))
        
        # Ajouter à la queue de synchronisation
        self._add_to_sync_queue('work_orders', work_order_id, 'update', {
            'status': 'in_progress',
            'started_at': datetime.now().isoformat(),
            'voice_activated': True
        })
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': 'Intervention démarrée par commande vocale',
            'new_status': 'in_progress'
        }
    
    def _complete_work_order_voice(self, work_order_id: int, completion_note: str) -> Dict:
        """Terminer un bon de travail via commande vocale"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        # Mettre à jour en offline
        cursor.execute('''
            INSERT OR REPLACE INTO offline_work_orders 
            (original_id, technician_id, status, notes, updated_at)
            VALUES (?, ?, 'completed', ?, CURRENT_TIMESTAMP)
        ''', (work_order_id, self.current_technician_id, completion_note))
        
        # Ajouter à la queue de synchronisation
        self._add_to_sync_queue('work_orders', work_order_id, 'update', {
            'status': 'completed',
            'completed_at': datetime.now().isoformat(),
            'completion_note': completion_note,
            'voice_completed': True
        })
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': 'Intervention terminée par commande vocale',
            'new_status': 'completed',
            'completion_note': completion_note
        }
    
    def _add_voice_note(self, work_order_id: int, note_content: str) -> Dict:
        """Ajouter une note vocale"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        # Sauvegarder la note en offline
        cursor.execute('''
            INSERT INTO offline_voice_commands 
            (work_order_id, command_type, voice_text, confidence_score, created_at)
            VALUES (?, 'voice_note', ?, 1.0, CURRENT_TIMESTAMP)
        ''', (work_order_id, note_content))
        
        # Ajouter à la queue de synchronisation
        self._add_to_sync_queue('intervention_notes', None, 'insert', {
            'work_order_id': work_order_id,
            'note': note_content,
            'note_type': 'voice',
            'technician_id': self.current_technician_id,
            'created_at': datetime.now().isoformat()
        })
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': 'Note vocale ajoutée',
            'note_content': note_content
        }
    
    def _change_status_voice(self, work_order_id: int, parameters: Dict) -> Dict:
        """Changer le statut via commande vocale"""
        # Logique de changement de statut
        new_status = parameters.get('new_status', 'in_progress')
        
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO offline_work_orders 
            (original_id, technician_id, status, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (work_order_id, self.current_technician_id, new_status))
        
        self._add_to_sync_queue('work_orders', work_order_id, 'update', {
            'status': new_status,
            'status_changed_at': datetime.now().isoformat(),
            'voice_status_change': True
        })
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'Statut changé en {new_status}',
            'new_status': new_status
        }
    
    def _report_issue_voice(self, work_order_id: int, parameters: Dict) -> Dict:
        """Signaler un problème via commande vocale"""
        issue_description = parameters.get('issue_description', '')
        severity = parameters.get('severity', 'medium')
        
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        # Sauvegarder le problème en offline
        cursor.execute('''
            INSERT INTO offline_voice_commands 
            (work_order_id, command_type, voice_text, confidence_score, created_at)
            VALUES (?, 'issue_report', ?, 1.0, CURRENT_TIMESTAMP)
        ''', (work_order_id, issue_description))
        
        # Créer une alerte
        self._add_to_sync_queue('issues', None, 'insert', {
            'work_order_id': work_order_id,
            'description': issue_description,
            'severity': severity,
            'reported_by': self.current_technician_id,
            'reported_via': 'voice',
            'created_at': datetime.now().isoformat()
        })
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'Problème signalé ({severity})',
            'issue_description': issue_description,
            'severity': severity
        }
    
    def _save_voice_command_offline(self, work_order_id: int, command_type: str, transcription: str, confidence: float):
        """Sauvegarder la commande vocale en base offline"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO offline_voice_commands 
            (work_order_id, command_type, voice_text, confidence_score, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (work_order_id, command_type, transcription, confidence))
        
        conn.commit()
        conn.close()
    
    def _add_to_sync_queue(self, table_name: str, record_id: int, action: str, data: Dict):
        """Ajouter un élément à la queue de synchronisation"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sync_queue (table_name, record_id, action, data, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (table_name, record_id, action, json.dumps(data)))
        
        conn.commit()
        conn.close()
    
    def set_current_technician(self, technician_id: int):
        """Définir le technicien actuel pour les commandes vocales"""
        self.current_technician_id = technician_id
    
    def get_offline_statistics(self) -> Dict:
        """Récupérer les statistiques du mode offline"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        # Compter les éléments en attente de synchronisation
        cursor.execute('SELECT COUNT(*) FROM sync_queue WHERE status = "pending"')
        pending_sync = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM offline_voice_commands WHERE sync_status = "pending"')
        pending_voice_commands = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM offline_work_orders WHERE sync_status = "pending"')
        pending_work_orders = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'pending_sync_items': pending_sync,
            'pending_voice_commands': pending_voice_commands,
            'pending_work_orders': pending_work_orders,
            'offline_mode': True,
            'last_sync': self.get_last_sync_time()
        }
    
    def get_last_sync_time(self) -> Optional[str]:
        """Récupérer l'heure de dernière synchronisation"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT MAX(last_attempt) FROM sync_queue WHERE status = "synced"
        ''')
        
        result = cursor.fetchone()[0]
        conn.close()
        
        return result


# Instance globale du moteur vocal
voice_engine = VoiceToActionEngine()
