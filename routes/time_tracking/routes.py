from core.database import get_db_connection
"""
Routes pour le système de tracking temporel des interventions
"""
from flask import Blueprint, request, jsonify, session
import pymysql
from datetime import datetime, timedelta
import os

# Blueprint pour les routes de tracking temporel
time_tracking_bp = Blueprint('time_tracking', __name__)

# Import de la connexion centralisée
from core.database import get_db_connection

@time_tracking_bp.route('/interventions/<int:work_order_id>/time_action', methods=['POST'])
def time_action(work_order_id):
    """Gérer les actions temporelles : start, pause, resume, complete"""
    action = request.json.get('action')
    notes = request.json.get('notes', '')
    technician_id = session.get('user_id')
    
    if not technician_id:
        return jsonify({'success': False, 'message': 'Non authentifié'}), 401
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Vérifier l'état actuel
            cursor.execute("""
                SELECT time_status, status FROM work_orders 
                WHERE id = %s AND (assigned_technician_id = %s OR %s IN (SELECT id FROM users WHERE role = 'admin'))
            """, (work_order_id, technician_id, technician_id))
            
            work_order = cursor.fetchone()
            if not work_order:
                return jsonify({'success': False, 'message': 'Intervention non trouvée ou non autorisée'}), 404
            
            current_time_status = work_order['time_status']
            
            # Logique des transitions d'état
            if action == 'start' and current_time_status == 'not_started':
                new_status = 'in_progress'
                new_time_status = 'in_progress'
                
            elif action == 'pause' and current_time_status == 'in_progress':
                new_status = work_order['status']  # Garder le même status
                new_time_status = 'paused'
                
            elif action == 'resume' and current_time_status == 'paused':
                new_status = 'in_progress'
                new_time_status = 'in_progress'
                
            elif action == 'complete' and current_time_status in ['in_progress', 'paused']:
                new_status = 'completed'
                new_time_status = 'completed'
                
            else:
                return jsonify({'success': False, 'message': f'Action {action} non valide pour l\'état actuel {current_time_status}'}), 400
            
            # Calculer la durée si c'est une pause ou completion
            duration_minutes = None
            if action in ['pause', 'complete']:
                cursor.execute("""
                    SELECT timestamp FROM intervention_time_tracking 
                    WHERE work_order_id = %s AND action_type IN ('start', 'resume')
                    ORDER BY timestamp DESC LIMIT 1
                """, (work_order_id,))
                
                last_start = cursor.fetchone()
                if last_start:
                    duration = datetime.now() - last_start['timestamp']
                    duration_minutes = int(duration.total_seconds() / 60)
            
            # Enregistrer l'action
            cursor.execute("""
                INSERT INTO intervention_time_tracking 
                (work_order_id, technician_id, action_type, duration_minutes, notes)
                VALUES (%s, %s, %s, %s, %s)
            """, (work_order_id, technician_id, action, duration_minutes, notes))
            
            # Mettre à jour le work_order
            update_fields = ['time_status = %s', 'updated_at = NOW()']
            params = [new_time_status]
            
            if action == 'start':
                update_fields.append('status = %s')
                params.append(new_status)
            elif action == 'complete':
                update_fields.append('status = %s')
                update_fields.append('completion_date = NOW()')
                params.append(new_status)
            
            params.append(work_order_id)
            
            cursor.execute(f"""
                UPDATE work_orders SET {', '.join(update_fields)}
                WHERE id = %s
            """, params)
            
            conn.commit()
            
            # Messages utilisateur
            messages = {
                'start': 'Intervention démarrée',
                'pause': f'Intervention mise en pause ({duration_minutes} min)',
                'resume': 'Intervention reprise',
                'complete': f'Intervention terminée (durée totale calculée)'
            }
            
            return jsonify({
                'success': True, 
                'message': messages[action],
                'new_time_status': new_time_status,
                'duration_minutes': duration_minutes
            })
            
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500
    finally:
        conn.close()

@time_tracking_bp.route('/interventions/<int:work_order_id>/time_entries', methods=['GET'])
def get_time_entries(work_order_id):
    """Récupérer toutes les entrées de temps pour une intervention"""
    technician_id = session.get('user_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    itt.*,
                    u.name as technician_name,
                    DATE_FORMAT(itt.timestamp, '%%d/%%m/%%Y %%H:%%i') as formatted_timestamp
                FROM intervention_time_tracking itt
                JOIN users u ON itt.technician_id = u.id
                WHERE itt.work_order_id = %s
                ORDER BY itt.timestamp DESC
            """, (work_order_id,))
            
            entries = cursor.fetchall()
            
            # Calculer le temps total
            total_minutes = 0
            current_session_start = None
            
            for entry in reversed(entries):  # Parcourir chronologiquement
                if entry['action_type'] in ['start', 'resume']:
                    current_session_start = entry['timestamp']
                elif entry['action_type'] in ['pause', 'complete'] and entry['duration_minutes']:
                    total_minutes += entry['duration_minutes']
            
            # Si une session est en cours, ajouter le temps écoulé
            if current_session_start:
                current_duration = datetime.now() - current_session_start
                total_minutes += int(current_duration.total_seconds() / 60)
            
            return jsonify({
                'success': True,
                'entries': entries,
                'total_minutes': total_minutes,
                'total_formatted': f"{total_minutes // 60}h {total_minutes % 60}min"
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500
    finally:
        conn.close()

@time_tracking_bp.route('/interventions/<int:work_order_id>/time_entries/<int:entry_id>', methods=['PUT'])
def update_time_entry(work_order_id, entry_id):
    """Modifier une entrée de temps"""
    data = request.json
    technician_id = session.get('user_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Vérifier les permissions
            cursor.execute("""
                SELECT itt.* FROM intervention_time_tracking itt
                JOIN work_orders wo ON itt.work_order_id = wo.id
                WHERE itt.id = %s AND itt.work_order_id = %s 
                AND (wo.assigned_technician_id = %s OR %s IN (SELECT id FROM users WHERE role = 'admin'))
            """, (entry_id, work_order_id, technician_id, technician_id))
            
            entry = cursor.fetchone()
            if not entry:
                return jsonify({'success': False, 'message': 'Entrée non trouvée ou non autorisée'}), 404
            
            # Mettre à jour
            cursor.execute("""
                UPDATE intervention_time_tracking 
                SET duration_minutes = %s, notes = %s, updated_at = NOW()
                WHERE id = %s
            """, (data.get('duration_minutes'), data.get('notes', ''), entry_id))
            
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Entrée mise à jour'})
            
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500
    finally:
        conn.close()

@time_tracking_bp.route('/interventions/<int:work_order_id>/time_entries/<int:entry_id>', methods=['DELETE'])
def delete_time_entry(work_order_id, entry_id):
    """Supprimer une entrée de temps"""
    technician_id = session.get('user_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Vérifier les permissions (admin seulement pour suppression)
            cursor.execute("""
                SELECT itt.* FROM intervention_time_tracking itt
                JOIN work_orders wo ON itt.work_order_id = wo.id
                WHERE itt.id = %s AND itt.work_order_id = %s 
                AND %s IN (SELECT id FROM users WHERE role = 'admin')
            """, (entry_id, work_order_id, technician_id))
            
            entry = cursor.fetchone()
            if not entry:
                return jsonify({'success': False, 'message': 'Entrée non trouvée ou permissions insuffisantes'}), 404
            
            # Supprimer
            cursor.execute("DELETE FROM intervention_time_tracking WHERE id = %s", (entry_id,))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Entrée supprimée'})
            
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500
    finally:
        conn.close()

# Routes simplifiées pour compatibilité avec l'interface
@time_tracking_bp.route('/interventions/<int:work_order_id>/time_entries', methods=['GET'])
def get_intervention_time_entries(work_order_id):
    """Route simplifiée pour récupérer les entrées d'une intervention"""
    return get_time_entries(work_order_id)

@time_tracking_bp.route('/entry/<int:entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    """Route simplifiée pour supprimer une entrée"""
    technician_id = session.get('user_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupérer l'intervention associée pour les permissions
            cursor.execute("""
                SELECT work_order_id FROM intervention_time_tracking WHERE id = %s
            """, (entry_id,))
            
            result = cursor.fetchone()
            if not result:
                return jsonify({'success': False, 'message': 'Entrée non trouvée'}), 404
            
            work_order_id = result['work_order_id']
            
            # Vérifier les permissions (admin seulement)
            cursor.execute("""
                SELECT id FROM users WHERE id = %s AND role = 'admin'
            """, (technician_id,))
            
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'Permissions insuffisantes'}), 403
            
            # Supprimer
            cursor.execute("DELETE FROM intervention_time_tracking WHERE id = %s", (entry_id,))
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Entrée supprimée'})
            
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500
    finally:
        conn.close()

@time_tracking_bp.route('/entries/<int:work_order_id>', methods=['DELETE'])
def clear_intervention_history(work_order_id):
    """Effacer tout l'historique d'une intervention (admin seulement)"""
    technician_id = session.get('user_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Vérifier les permissions (admin seulement)
            cursor.execute("""
                SELECT id FROM users WHERE id = %s AND role = 'admin'
            """, (technician_id,))
            
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'Permissions insuffisantes'}), 403
            
            # Supprimer toutes les entrées
            cursor.execute("""
                DELETE FROM intervention_time_tracking WHERE work_order_id = %s
            """, (work_order_id,))
            
            # Remettre le statut à not_started
            cursor.execute("""
                UPDATE work_orders SET time_status = 'not_started' WHERE id = %s
            """, (work_order_id,))
            
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Historique effacé'})
            
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500
    finally:
        conn.close()

@time_tracking_bp.route('/report/<int:work_order_id>')
def generate_time_report(work_order_id):
    """Générer un rapport PDF des temps (placeholder)"""
    return jsonify({'success': False, 'message': 'Génération PDF en développement'}), 501
