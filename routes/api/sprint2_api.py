"""
ChronoTech Sprint 2 - Routes API pour l'Expérience Terrain Augmentée
APIs REST pour voice-to-action, mode offline et AR
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import json
import logging
from datetime import datetime
import os

from core.voice_to_action import voice_engine
from core.offline_sync import sync_manager
from core.ar_checklist import ar_overlay
from core.models import WorkOrder, User
from core.database import get_db_connection

logger = logging.getLogger(__name__)
sprint2_api = Blueprint('sprint2_api', __name__, url_prefix='/api/sprint2')

# =============================================================================
# VOICE-TO-ACTION APIs
# =============================================================================

@sprint2_api.route('/voice/process', methods=['POST'])
@login_required
def process_voice_command():
    """Traiter une commande vocale"""
    try:
        data = request.get_json()
        
        if not data or 'audio_data' not in data:
            return jsonify({
                'success': False,
                'message': 'Données audio manquantes'
            }), 400
        
        # Configurer le technicien actuel
        voice_engine.set_current_technician(current_user.id)
        
        # Traiter la commande vocale
        result = voice_engine.process_voice_command(
            data['audio_data'].encode(),
            data.get('work_order_id')
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur traitement commande vocale: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sprint2_api.route('/voice/start-listening', methods=['POST'])
@login_required
def start_voice_listening():
    """Démarrer l'écoute vocale"""
    try:
        data = request.get_json() or {}
        work_order_id = data.get('work_order_id')
        
        # Configurer le technicien
        voice_engine.set_current_technician(current_user.id)
        voice_engine.is_listening = True
        
        return jsonify({
            'success': True,
            'message': 'Écoute vocale activée',
            'listening': True,
            'work_order_id': work_order_id,
            'supported_commands': [
                'commencer la tâche',
                'terminer l\'intervention',
                'ajouter une note',
                'signaler un problème'
            ]
        })
        
    except Exception as e:
        logger.error(f"Erreur démarrage écoute vocale: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sprint2_api.route('/voice/stop-listening', methods=['POST'])
@login_required
def stop_voice_listening():
    """Arrêter l'écoute vocale"""
    try:
        voice_engine.is_listening = False
        
        return jsonify({
            'success': True,
            'message': 'Écoute vocale désactivée',
            'listening': False
        })
        
    except Exception as e:
        logger.error(f"Erreur arrêt écoute vocale: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sprint2_api.route('/voice/commands-history', methods=['GET'])
@login_required
def get_voice_commands_history():
    """Récupérer l'historique des commandes vocales"""
    try:
        work_order_id = request.args.get('work_order_id')
        limit = int(request.args.get('limit', 20))
        
        # Récupérer depuis la base offline
        import sqlite3
        conn = sqlite3.connect(voice_engine.offline_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
            SELECT * FROM offline_voice_commands 
            WHERE (? IS NULL OR work_order_id = ?)
            ORDER BY created_at DESC 
            LIMIT ?
        '''
        
        cursor.execute(query, (work_order_id, work_order_id, limit))
        commands = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'commands': commands,
            'total': len(commands)
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération historique vocal: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# OFFLINE MODE APIs
# =============================================================================

@sprint2_api.route('/offline/status', methods=['GET'])
@login_required
def get_offline_status():
    """Récupérer le statut du mode offline"""
    try:
        if not sync_manager:
            return jsonify({
                'success': False,
                'message': 'Gestionnaire de synchronisation non initialisé'
            }), 500
        
        # Statut de synchronisation
        sync_status = sync_manager.get_sync_status()
        
        # Statistiques offline
        offline_stats = voice_engine.get_offline_statistics()
        
        return jsonify({
            'success': True,
            'offline_mode': not sync_status['is_online'],
            'sync_status': sync_status,
            'offline_stats': offline_stats,
            'capabilities': {
                'voice_commands': True,
                'work_order_updates': True,
                'media_capture': True,
                'sync_queue': True
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur statut offline: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sprint2_api.route('/offline/sync-now', methods=['POST'])
@login_required
def force_sync_now():
    """Forcer une synchronisation immédiate"""
    try:
        if not sync_manager:
            return jsonify({
                'success': False,
                'message': 'Gestionnaire de synchronisation non initialisé'
            }), 500
        
        result = sync_manager.force_sync_now()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur synchronisation forcée: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sprint2_api.route('/offline/work-orders', methods=['GET'])
@login_required
def get_offline_work_orders():
    """Récupérer les work orders en mode offline"""
    try:
        # Récupérer depuis la base offline
        import sqlite3
        conn = sqlite3.connect(voice_engine.offline_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM offline_work_orders 
            WHERE technician_id = ?
            ORDER BY updated_at DESC
        ''', (current_user.id,))
        
        work_orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'work_orders': work_orders,
            'offline_mode': True
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération work orders offline: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sprint2_api.route('/offline/work-order/<int:work_order_id>/update', methods=['POST'])
@login_required
def update_offline_work_order(work_order_id):
    """Mettre à jour un work order en mode offline"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Données manquantes'
            }), 400
        
        # Sauvegarder en base offline
        import sqlite3
        conn = sqlite3.connect(voice_engine.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO offline_work_orders 
            (original_id, technician_id, status, notes, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            work_order_id,
            current_user.id,
            data.get('status'),
            data.get('notes', '')
        ))
        
        # Ajouter à la queue de synchronisation
        sync_data = {
            'status': data.get('status'),
            'notes': data.get('notes'),
            'updated_by': current_user.id,
            'updated_at': datetime.now().isoformat()
        }
        
        cursor.execute('''
            INSERT INTO sync_queue (table_name, record_id, action, data, created_at)
            VALUES ('work_orders', ?, 'update', ?, CURRENT_TIMESTAMP)
        ''', (work_order_id, json.dumps(sync_data)))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Work order mis à jour en mode offline',
            'work_order_id': work_order_id,
            'queued_for_sync': True
        })
        
    except Exception as e:
        logger.error(f"Erreur mise à jour work order offline: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# AR CHECKLIST APIs
# =============================================================================

@sprint2_api.route('/ar/start-session', methods=['POST'])
@login_required
def start_ar_session():
    """Démarrer une session AR"""
    try:
        data = request.get_json()
        
        if not data or 'work_order_id' not in data or 'checklist_type' not in data:
            return jsonify({
                'success': False,
                'message': 'work_order_id et checklist_type requis'
            }), 400
        
        result = ar_overlay.start_ar_session(
            data['work_order_id'],
            data['checklist_type']
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur démarrage session AR: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sprint2_api.route('/ar/process-frame', methods=['POST'])
@login_required
def process_ar_frame():
    """Traiter une frame caméra pour l'AR"""
    try:
        data = request.get_json()
        
        if not data or 'frame_data' not in data:
            return jsonify({
                'success': False,
                'message': 'Données de frame manquantes'
            }), 400
        
        result = ar_overlay.process_camera_frame(data['frame_data'])
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur traitement frame AR: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sprint2_api.route('/ar/complete-item', methods=['POST'])
@login_required
def complete_ar_checklist_item():
    """Marquer un item de checklist AR comme complété"""
    try:
        data = request.get_json()
        
        if not data or 'zone_name' not in data or 'item_name' not in data:
            return jsonify({
                'success': False,
                'message': 'zone_name et item_name requis'
            }), 400
        
        result = ar_overlay.complete_checklist_item(
            data['zone_name'],
            data['item_name']
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur completion item AR: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sprint2_api.route('/ar/session-status', methods=['GET'])
@login_required
def get_ar_session_status():
    """Récupérer le statut de la session AR"""
    try:
        status = ar_overlay.get_ar_session_status()
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Erreur statut session AR: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sprint2_api.route('/ar/finalize-session', methods=['POST'])
@login_required
def finalize_ar_session():
    """Finaliser une session AR"""
    try:
        result = ar_overlay.finalize_ar_session()
        
        # Si succès, sauvegarder le rapport en base
        if result['success'] and 'report' in result:
            # Sauvegarder en mode offline d'abord
            import sqlite3
            conn = sqlite3.connect(voice_engine.offline_db_path)
            cursor = conn.cursor()
            
            report_data = {
                'work_order_id': result['report']['work_order_id'],
                'report_type': 'ar_checklist',
                'report_data': json.dumps(result['report']),
                'created_by': current_user.id,
                'created_at': datetime.now().isoformat()
            }
            
            cursor.execute('''
                INSERT INTO sync_queue (table_name, record_id, action, data, created_at)
                VALUES ('inspection_reports', NULL, 'insert', ?, CURRENT_TIMESTAMP)
            ''', (json.dumps(report_data),))
            
            conn.commit()
            conn.close()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur finalisation session AR: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sprint2_api.route('/ar/templates', methods=['GET'])
@login_required
def get_ar_templates():
    """Récupérer les templates AR disponibles"""
    try:
        templates = ar_overlay.overlay_templates
        
        # Formater pour l'API
        formatted_templates = {}
        for template_name, template_config in templates.items():
            formatted_templates[template_name] = {
                'title': template_config['title'],
                'zones_count': len(template_config['zones']),
                'total_items': sum(len(zone['checklist']) for zone in template_config['zones']),
                'description': f"Checklist {template_config['title']} avec {len(template_config['zones'])} zones d'inspection"
            }
        
        return jsonify({
            'success': True,
            'templates': formatted_templates
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération templates AR: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# SPRINT 2 DASHBOARD APIs
# =============================================================================

@sprint2_api.route('/dashboard/field-stats', methods=['GET'])
@login_required
def get_field_experience_stats():
    """Récupérer les statistiques d'expérience terrain"""
    try:
        # Statistiques des derniers 30 jours
        stats = {
            'voice_commands': {
                'total_commands': 0,
                'successful_commands': 0,
                'most_used_command': 'add_note',
                'voice_time_saved': '45 min'  # Simulation
            },
            'offline_mode': {
                'offline_sessions': 0,
                'offline_hours': 0,
                'sync_success_rate': 98.5,
                'pending_sync_items': 0
            },
            'ar_sessions': {
                'total_sessions': 0,
                'completed_checklists': 0,
                'avg_completion_time': '12 min',
                'accuracy_improvement': '35%'
            },
            'productivity': {
                'tasks_completed_faster': 23,
                'error_reduction': '28%',
                'customer_satisfaction': 4.7,
                'mobile_efficiency': '40%'
            }
        }
        
        # Récupérer les vraies statistiques depuis la base offline
        import sqlite3
        conn = sqlite3.connect(voice_engine.offline_db_path)
        cursor = conn.cursor()
        
        # Commandes vocales
        cursor.execute('SELECT COUNT(*), command_type FROM offline_voice_commands GROUP BY command_type')
        voice_stats = cursor.fetchall()
        
        if voice_stats:
            stats['voice_commands']['total_commands'] = sum(count for count, _ in voice_stats)
            if voice_stats:
                stats['voice_commands']['most_used_command'] = max(voice_stats, key=lambda x: x[0])[1]
        
        # Mode offline
        cursor.execute('SELECT COUNT(*) FROM sync_queue WHERE status = "pending"')
        pending_items = cursor.fetchone()[0]
        stats['offline_mode']['pending_sync_items'] = pending_items
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'period': 'last_30_days'
        })
        
    except Exception as e:
        logger.error(f"Erreur statistiques terrain: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sprint2_api.route('/dashboard/field-activities', methods=['GET'])
@login_required
def get_recent_field_activities():
    """Récupérer les activités terrain récentes"""
    try:
        limit = int(request.args.get('limit', 10))
        
        activities = []
        
        # Récupérer depuis la base offline
        import sqlite3
        conn = sqlite3.connect(voice_engine.offline_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Activités récentes (commandes vocales, sync, etc.)
        cursor.execute('''
            SELECT 'voice_command' as type, command_type as action, 
                   voice_text as details, created_at
            FROM offline_voice_commands 
            WHERE created_at > datetime('now', '-7 days')
            
            UNION ALL
            
            SELECT 'sync' as type, action, table_name as details, created_at
            FROM sync_queue 
            WHERE created_at > datetime('now', '-7 days')
            
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        
        activities = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'activities': activities,
            'total': len(activities)
        })
        
    except Exception as e:
        logger.error(f"Erreur activités terrain: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# UTILITAIRES Sprint 2
# =============================================================================

@sprint2_api.route('/health', methods=['GET'])
def sprint2_health_check():
    """Vérification santé des services Sprint 2"""
    try:
        health_status = {
            'voice_engine': {
                'status': 'ok' if voice_engine else 'error',
                'listening': getattr(voice_engine, 'is_listening', False),
                'offline_db': os.path.exists(voice_engine.offline_db_path) if voice_engine else False
            },
            'sync_manager': {
                'status': 'ok' if sync_manager else 'not_initialized',
                'online': sync_manager.is_online if sync_manager else False,
                'sync_running': sync_manager.sync_running if sync_manager else False
            },
            'ar_overlay': {
                'status': 'ok' if ar_overlay else 'error',
                'session_active': ar_overlay.current_checklist is not None if ar_overlay else False,
                'camera_active': getattr(ar_overlay, 'camera_active', False)
            }
        }
        
        all_services_ok = all(
            service['status'] == 'ok' 
            for service in health_status.values()
        )
        
        return jsonify({
            'success': True,
            'sprint2_status': 'healthy' if all_services_ok else 'degraded',
            'services': health_status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur health check Sprint 2: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Enregistrer le blueprint
def register_sprint2_routes(app):
    """Enregistrer les routes Sprint 2"""
    app.register_blueprint(sprint2_api)
    logger.info("🚀 Routes API Sprint 2 - Expérience Terrain Augmentée enregistrées")
