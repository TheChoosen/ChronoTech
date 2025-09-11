"""
API Kanban pour les interventions - ChronoTech
Vue Kanban des interventions avec drag & drop
"""
import os
import pymysql
import logging
from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Blueprint pour l'API Kanban
kanban_bp = Blueprint('kanban_api', __name__)

def get_db_connection():
    """Connexion à la base de données"""
    return pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        user=os.getenv('MYSQL_USER', 'chronotech_user'),
        password=os.getenv('MYSQL_PASSWORD', 'ChronoTech2024!'),
        database=os.getenv('MYSQL_DB', 'chronotech_db'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def require_auth(f):
    """Décorateur pour vérifier l'authentification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@kanban_bp.route('/api/kanban/interventions', methods=['GET'])
@require_auth
def get_kanban_data():
    """Récupérer les données pour la vue Kanban des interventions"""
    try:
        user_role = session.get('user_role', 'admin')
        user_id = session.get('user_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Définir le filtre selon le rôle
        if user_role == 'technician':
            where_clause = "WHERE wo.assigned_technician_id = %s"
            params = [user_id]
        else:
            where_clause = "WHERE 1=1"
            params = []
        
        # Ajouter des filtres optionnels
        date_filter = request.args.get('date')
        technician_filter = request.args.get('technician_id')
        priority_filter = request.args.get('priority')
        
        if date_filter:
            where_clause += " AND DATE(wo.scheduled_date) = %s"
            params.append(date_filter)
        
        if technician_filter and user_role != 'technician':
            where_clause += " AND wo.assigned_technician_id = %s"
            params.append(technician_filter)
            
        if priority_filter:
            where_clause += " AND wo.priority = %s"
            params.append(priority_filter)
        
        # Requête principale pour récupérer les interventions
        cursor.execute(f"""
            SELECT 
                wo.id,
                wo.claim_number,
                wo.description,
                wo.status,
                wo.priority,
                wo.scheduled_date,
                wo.estimated_duration,
                wo.created_at,
                wo.updated_at,
                c.name as customer_name,
                c.phone as customer_phone,
                c.address as customer_address,
                u.name as technician_name,
                u.id as technician_id,
                v.make as vehicle_make,
                v.model as vehicle_model,
                v.license_plate,
                
                -- Compter les notes et médias
                COUNT(DISTINCT in_.id) as notes_count,
                COUNT(DISTINCT im.id) as media_count,
                MAX(in_.created_at) as last_note_date,
                
                -- Indicateurs visuels
                CASE 
                    WHEN wo.priority = 'urgent' THEN '#dc3545'
                    WHEN wo.priority = 'high' THEN '#fd7e14' 
                    WHEN wo.priority = 'medium' THEN '#ffc107'
                    ELSE '#6c757d'
                END as priority_color,
                
                CASE
                    WHEN wo.scheduled_date < NOW() AND wo.status NOT IN ('completed', 'cancelled') THEN 1
                    ELSE 0
                END as is_overdue,
                
                TIMESTAMPDIFF(HOUR, wo.created_at, NOW()) as age_hours
                
            FROM work_orders wo
            LEFT JOIN customers c ON wo.customer_id = c.id
            LEFT JOIN users u ON wo.assigned_technician_id = u.id
            LEFT JOIN vehicles v ON wo.vehicle_id = v.id
            LEFT JOIN intervention_notes in_ ON wo.id = in_.work_order_id
            LEFT JOIN intervention_media im ON wo.id = im.work_order_id
            {where_clause}
            GROUP BY wo.id
            ORDER BY 
                FIELD(wo.priority, 'urgent', 'high', 'medium', 'low'),
                wo.scheduled_date ASC,
                wo.created_at DESC
        """, params)
        
        interventions = cursor.fetchall()
        
        # Organiser par colonnes Kanban
        kanban_columns = {
            'pending': {
                'title': 'En attente',
                'color': '#6c757d',
                'items': []
            },
            'assigned': {
                'title': 'Assigné',
                'color': '#007bff',
                'items': []
            },
            'in_progress': {
                'title': 'En cours',
                'color': '#ffc107',
                'items': []
            },
            'waiting_parts': {
                'title': 'Attente pièces',
                'color': '#fd7e14',
                'items': []
            },
            'completed': {
                'title': 'Terminé',
                'color': '#28a745',
                'items': []
            },
            'cancelled': {
                'title': 'Annulé',
                'color': '#dc3545',
                'items': []
            }
        }
        
        # Répartir les interventions dans les colonnes
        for intervention in interventions:
            status = intervention['status'] or 'pending'
            if status in kanban_columns:
                kanban_columns[status]['items'].append({
                    'id': intervention['id'],
                    'claim_number': intervention['claim_number'],
                    'description': intervention['description'][:100] + '...' if len(intervention['description']) > 100 else intervention['description'],
                    'customer_name': intervention['customer_name'],
                    'customer_phone': intervention['customer_phone'],
                    'technician_name': intervention['technician_name'],
                    'technician_id': intervention['technician_id'],
                    'vehicle_info': f"{intervention['vehicle_make']} {intervention['vehicle_model']}" if intervention['vehicle_make'] else None,
                    'license_plate': intervention['license_plate'],
                    'priority': intervention['priority'],
                    'priority_color': intervention['priority_color'],
                    'scheduled_date': intervention['scheduled_date'].isoformat() if intervention['scheduled_date'] else None,
                    'estimated_duration': intervention['estimated_duration'],
                    'notes_count': intervention['notes_count'],
                    'media_count': intervention['media_count'],
                    'is_overdue': bool(intervention['is_overdue']),
                    'age_hours': intervention['age_hours'],
                    'last_note_date': intervention['last_note_date'].isoformat() if intervention['last_note_date'] else None
                })
        
        # Statistiques globales
        stats = {
            'total': len(interventions),
            'urgent': len([i for i in interventions if i['priority'] == 'urgent']),
            'overdue': len([i for i in interventions if i['is_overdue']]),
            'in_progress': len(kanban_columns['in_progress']['items']),
            'completed_today': len([i for i in interventions if i['status'] == 'completed' and i['updated_at'].date() == datetime.now().date()])
        }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'columns': kanban_columns,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération données Kanban: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@kanban_bp.route('/api/kanban/interventions/<int:intervention_id>/status', methods=['PUT'])
@require_auth
def update_intervention_status(intervention_id):
    """Mettre à jour le statut d'une intervention (drag & drop)"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        user_id = session.get('user_id')
        
        if not new_status:
            return jsonify({'success': False, 'error': 'Status required'}), 400
        
        # Vérifier que le statut est valide
        valid_statuses = ['pending', 'assigned', 'in_progress', 'waiting_parts', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier l'accès à l'intervention
        cursor.execute("""
            SELECT wo.*, u.name as technician_name
            FROM work_orders wo
            LEFT JOIN users u ON wo.assigned_technician_id = u.id
            WHERE wo.id = %s
        """, (intervention_id,))
        
        intervention = cursor.fetchone()
        if not intervention:
            return jsonify({'success': False, 'error': 'Intervention not found'}), 404
        
        # Vérifier les permissions
        user_role = session.get('user_role')
        if user_role == 'technician' and intervention['assigned_technician_id'] != user_id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Mettre à jour le statut
        cursor.execute("""
            UPDATE work_orders 
            SET status = %s, updated_at = %s
            WHERE id = %s
        """, (new_status, datetime.now(), intervention_id))
        
        # Enregistrer l'historique du changement
        cursor.execute("""
            INSERT INTO intervention_notes (work_order_id, user_id, note_type, content, created_at)
            VALUES (%s, %s, 'status_change', %s, %s)
        """, (
            intervention_id,
            user_id,
            f"Statut changé vers: {new_status}",
            datetime.now()
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Statut mis à jour vers: {new_status}',
            'new_status': new_status
        })
        
    except Exception as e:
        logger.error(f"Erreur mise à jour statut intervention {intervention_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@kanban_bp.route('/api/kanban/interventions/<int:intervention_id>/assign', methods=['PUT'])
@require_auth
def assign_intervention(intervention_id):
    """Assigner une intervention à un technicien"""
    try:
        data = request.get_json()
        technician_id = data.get('technician_id')
        user_id = session.get('user_id')
        user_role = session.get('user_role')
        
        # Seuls les admins et superviseurs peuvent assigner
        if user_role not in ['admin', 'supervisor']:
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
        if not technician_id:
            return jsonify({'success': False, 'error': 'Technician ID required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier que le technicien existe
        cursor.execute("SELECT name FROM users WHERE id = %s AND role = 'technician'", (technician_id,))
        technician = cursor.fetchone()
        if not technician:
            return jsonify({'success': False, 'error': 'Technician not found'}), 404
        
        # Mettre à jour l'assignation
        cursor.execute("""
            UPDATE work_orders 
            SET assigned_technician_id = %s, 
                status = CASE WHEN status = 'pending' THEN 'assigned' ELSE status END,
                updated_at = %s
            WHERE id = %s
        """, (technician_id, datetime.now(), intervention_id))
        
        # Ajouter une note d'historique
        cursor.execute("""
            INSERT INTO intervention_notes (work_order_id, user_id, note_type, content, created_at)
            VALUES (%s, %s, 'assignment', %s, %s)
        """, (
            intervention_id,
            user_id,
            f"Intervention assignée à: {technician['name']}",
            datetime.now()
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Intervention assignée à {technician["name"]}',
            'technician_name': technician['name']
        })
        
    except Exception as e:
        logger.error(f"Erreur assignation intervention {intervention_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@kanban_bp.route('/api/kanban/technicians', methods=['GET'])
@require_auth
def get_available_technicians():
    """Récupérer la liste des techniciens disponibles pour assignation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                u.id,
                u.name,
                u.email,
                COUNT(wo.id) as active_interventions,
                AVG(COALESCE(wo.estimated_duration, 120)) as avg_duration
            FROM users u
            LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id 
                AND wo.status IN ('assigned', 'in_progress')
            WHERE u.role = 'technician' AND u.is_active = 1
            GROUP BY u.id, u.name, u.email
            ORDER BY active_interventions ASC, u.name ASC
        """)
        
        technicians = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'technicians': technicians
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération techniciens: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
