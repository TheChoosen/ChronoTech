"""
Module API REST - ChronoTech
Endpoints pour l'intégration mobile et externe
"""

from flask import Blueprint, request, jsonify, session
import pymysql
from core.config import get_db_config
from core.utils import log_info, log_error, log_warning
from datetime import datetime
import json

# Création du blueprint
bp = Blueprint('api', __name__)

def get_db_connection():
    """Obtient une connexion à la base de données"""
    try:
        cfg = get_db_config()
        # Ensure we always get dict rows
        cfg.setdefault('cursorclass', pymysql.cursors.DictCursor)
        return pymysql.connect(**cfg)
    except Exception as e:
        log_error(f"Erreur de connexion à la base de données: {e}")
        return None

def authenticate_request():
    """Authentification simple pour l'API (à améliorer en production)"""
    # Pour le moment, vérification basique
    # En production, utiliser JWT ou OAuth
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != 'chronotech_api_2025':
        return False
    return True

def require_auth(f):
    """Décorateur pour l'authentification API"""
    def decorated_function(*args, **kwargs):
        if not authenticate_request():
            return jsonify({'error': 'Authentication required', 'code': 401}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# ====================
# DASHBOARD API ENDPOINTS
# ====================

@bp.route('/notifications', methods=['GET'])
def get_notifications():
    """Récupérer les notifications pour le dashboard"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'notifications': []}), 500
        
        with conn.cursor() as cursor:
            # Récupérer les notifications (pour l'instant, on simule)
            notifications = [
                {
                    'id': 1,
                    'title': 'Nouveau bon de travail',
                    'message': 'Un nouveau bon de travail a été créé',
                    'type': 'info',
                    'timestamp': datetime.now().isoformat(),
                    'read': False
                },
                {
                    'id': 2,
                    'title': 'Intervention terminée',
                    'message': 'L\'intervention #123 a été marquée comme terminée',
                    'type': 'success',
                    'timestamp': datetime.now().isoformat(),
                    'read': False
                }
            ]
            
        conn.close()
        return jsonify({'success': True, 'notifications': notifications})
        
    except Exception as e:
        log_error(f"Erreur récupération notifications: {e}")
        return jsonify({'success': False, 'notifications': []}), 500

@bp.route('/calendar-events', methods=['GET'])
def get_calendar_events():
    """Récupérer les événements du calendrier pour FullCalendar"""
    try:
        start = request.args.get('start')
        end = request.args.get('end')
        
        conn = get_db_connection()
        if not conn:
            return jsonify([]), 500
        
        with conn.cursor() as cursor:
            # Récupérer les rendez-vous et work orders comme événements
            events = []
            
            # Rendez-vous
            try:
                cursor.execute("""
                    SELECT a.id, a.scheduled_date, a.duration_minutes, a.description,
                           c.name as customer_name, a.customer_id
                    FROM appointments a
                    LEFT JOIN customers c ON a.customer_id = c.id
                    WHERE a.scheduled_date BETWEEN %s AND %s
                    ORDER BY a.scheduled_date
                """, (start, end))
                
                appointments = cursor.fetchall()
                for apt in appointments:
                    events.append({
                        'id': f'apt_{apt["id"]}',
                        'title': f'RDV: {apt["customer_name"] or "Client inconnu"}',
                        'start': apt['scheduled_date'].isoformat() if apt['scheduled_date'] else None,
                        'end': (apt['scheduled_date'] + datetime.timedelta(minutes=apt['duration_minutes'] or 60)).isoformat() if apt['scheduled_date'] else None,
                        'backgroundColor': '#007bff',
                        'borderColor': '#007bff',
                        'textColor': '#ffffff',
                        'extendedProps': {
                            'type': 'appointment',
                            'customer_id': apt['customer_id'],
                            'description': apt['description']
                        }
                    })
            except Exception as e:
                log_error(f"Erreur récupération rendez-vous: {e}")
            
            # Work Orders avec dates
            try:
                cursor.execute("""
                    SELECT wo.id, wo.created_at, wo.status, wo.priority, wo.description,
                           c.name as customer_name, wo.customer_id
                    FROM work_orders wo
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    WHERE wo.created_at BETWEEN %s AND %s
                    ORDER BY wo.created_at
                """, (start, end))
                
                work_orders = cursor.fetchall()
                for wo in work_orders:
                    color = '#28a745' if wo['status'] == 'completed' else '#ffc107' if wo['status'] == 'in_progress' else '#6c757d'
                    # Utiliser la description ou claim_number comme titre
                    title = wo['description'][:50] if wo['description'] else f"Bon de travail #{wo['id']}"
                    events.append({
                        'id': f'wo_{wo["id"]}',
                        'title': f'BT: {title}',
                        'start': wo['created_at'].isoformat() if wo['created_at'] else None,
                        'backgroundColor': color,
                        'borderColor': color,
                        'textColor': '#ffffff',
                        'extendedProps': {
                            'type': 'work_order',
                            'customer_id': wo['customer_id'],
                            'status': wo['status'],
                            'priority': wo['priority']
                        }
                    })
            except Exception as e:
                log_error(f"Erreur récupération work orders: {e}")
                
        conn.close()
        return jsonify(events)
        
    except Exception as e:
        log_error(f"Erreur récupération événements calendrier: {e}")
        return jsonify([]), 500

# ====================
# CHAT API ENDPOINTS
# ====================

@bp.route('/current-user', methods=['GET'])
def get_current_user():
    """Récupérer les informations de l'utilisateur actuel"""
    try:
        # Récupérer depuis la session ou utiliser l'admin par défaut
        user_id = session.get('user_id', 1)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, role, department
            FROM users 
            WHERE id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            # Utilisateur par défaut
            return jsonify({
                'id': 1,
                'name': 'Admin System',
                'email': 'admin@chronotech.com',
                'role': 'admin',
                'department': 'Administration'
            })
        
        return jsonify(user)
        
    except Exception as e:
        log_error(f"Erreur récupération utilisateur actuel: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/chat-history', methods=['GET'])
def get_chat_history():
    """Récupérer l'historique des messages d'un salon"""
    try:
        room_name = request.args.get('room', 'general')
        limit = int(request.args.get('limit', 50))
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Construire la requête selon le type de room
        if room_name == 'general':
            query = """
                SELECT cm.*, u.name as sender_name
                FROM chat_messages cm
                LEFT JOIN users u ON cm.user_id = u.id
                WHERE cm.room_name = 'general' OR cm.room_name IS NULL
                ORDER BY cm.created_at DESC
                LIMIT %s
            """
            params = (limit,)
        else:
            query = """
                SELECT cm.*, u.name as sender_name
                FROM chat_messages cm
                LEFT JOIN users u ON cm.user_id = u.id
                WHERE cm.room_name = %s
                ORDER BY cm.created_at DESC
                LIMIT %s
            """
            params = (room_name, limit)
        
        cursor.execute(query, params)
        messages = cursor.fetchall()
        
        # Inverser l'ordre pour avoir les plus anciens en premier
        messages.reverse()
        
        # Formater les dates
        for msg in messages:
            if msg['created_at']:
                msg['created_at'] = msg['created_at'].isoformat()
                msg['timestamp'] = msg['created_at']  # Alias pour compatibilité
        
        cursor.close()
        conn.close()
        
        return jsonify({'messages': messages})
        
    except Exception as e:
        log_error(f"Erreur récupération historique chat: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ====================
# KANBAN API ENDPOINTS - FONCTIONNALITÉ COMPLÈTE
# ====================

@bp.route('/work-orders', methods=['GET'])
def get_work_orders():
    """Récupérer tous les bons de travail pour le Kanban"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Construire la requête avec filtres
        base_query = """
            SELECT wo.*, 
                   u1.name as assigned_technician_name,
                   u2.name as created_by_name,
                   v.make as vehicle_make,
                   v.model as vehicle_model,
                   v.license_plate as vehicle_license_plate,
                   v.department as vehicle_department,
                   CASE 
                       WHEN wo.priority = 'urgent' THEN 4
                       WHEN wo.priority = 'high' THEN 3
                       WHEN wo.priority = 'medium' THEN 2
                       ELSE 1
                   END as priority_order
            FROM work_orders wo
            LEFT JOIN users u1 ON wo.assigned_technician_id = u1.id
            LEFT JOIN users u2 ON wo.created_by_user_id = u2.id
            LEFT JOIN vehicles v ON wo.vehicle_id = v.id
            WHERE 1=1
        """
        
        params = []
        
        # Filtres
        status_filter = request.args.get('status')
        priority_filter = request.args.get('priority')
        technician_filter = request.args.get('technician')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        search = request.args.get('search')
        
        if status_filter:
            base_query += " AND wo.status = %s"
            params.append(status_filter)
        
        if priority_filter:
            base_query += " AND wo.priority = %s"
            params.append(priority_filter)
        
        if technician_filter:
            base_query += " AND wo.assigned_technician_id = %s"
            params.append(int(technician_filter))
        
        if date_from:
            base_query += " AND DATE(wo.scheduled_date) >= %s"
            params.append(date_from)
        
        if date_to:
            base_query += " AND DATE(wo.scheduled_date) <= %s"
            params.append(date_to)
        
        if search:
            base_query += " AND (wo.customer_name LIKE %s OR wo.description LIKE %s OR wo.claim_number LIKE %s)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])
        
        # Ordre par priorité et date
        base_query += " ORDER BY priority_order DESC, wo.scheduled_date ASC"
        
        cursor.execute(base_query, params)
        work_orders = cursor.fetchall()
        
        # Formater les dates pour JSON
        for wo in work_orders:
            if wo['scheduled_date']:
                wo['scheduled_date'] = wo['scheduled_date'].isoformat()
            if wo['completion_date']:
                wo['completion_date'] = wo['completion_date'].isoformat()
            if wo['created_at']:
                wo['created_at'] = wo['created_at'].isoformat()
            if wo['updated_at']:
                wo['updated_at'] = wo['updated_at'].isoformat()
        
        cursor.close()
        conn.close()
        
        return jsonify({'work_orders': work_orders})
        
    except Exception as e:
        log_error(f"Erreur récupération work orders: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/work-orders/<int:work_order_id>/status', methods=['PUT'])
def update_work_order_status(work_order_id):
    """Mettre à jour le statut d'un bon de travail"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        valid_statuses = ['draft', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Récupérer l'état actuel
        cursor.execute("SELECT status, claim_number FROM work_orders WHERE id = %s", (work_order_id,))
        current = cursor.fetchone()
        
        if not current:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Work order not found'}), 404
        
        old_status = current['status']
        claim_number = current['claim_number']
        
        # Mettre à jour le statut
        update_query = "UPDATE work_orders SET status = %s, updated_at = %s"
        params = [new_status, datetime.now()]
        
        # Si complété, ajouter la date de completion
        if new_status == 'completed':
            update_query += ", completion_date = %s"
            params.append(datetime.now())
        
        update_query += " WHERE id = %s"
        params.append(work_order_id)
        
        cursor.execute(update_query, params)
        
        # Enregistrer dans l'historique Kanban
        history_query = """
            INSERT INTO kanban_history (task_id, old_status, new_status, 
                                      moved_by, move_reason)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        # Récupérer l'utilisateur actuel (à adapter selon votre système d'auth)
        user_id = session.get('user_id', 1)  # Par défaut admin
        
        cursor.execute(history_query, (
            work_order_id, old_status, new_status, 
            user_id, f"Statut changé de {old_status} à {new_status}"
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        log_info(f"Work order {claim_number} (ID: {work_order_id}) status updated: {old_status} -> {new_status}")
        
        return jsonify({
            'success': True,
            'work_order_id': work_order_id,
            'old_status': old_status,
            'new_status': new_status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_error(f"Erreur mise à jour statut work order {work_order_id}: {e}")
        
        # Plus de détails sur l'erreur pour le debugging
        import traceback
        log_error(f"Traceback: {traceback.format_exc()}")
        
        # Retourner un message d'erreur plus spécifique si possible
        error_msg = str(e)
        if "kanban_history" in error_msg:
            error_msg = "Erreur lors de l'enregistrement dans l'historique"
        elif "work_orders" in error_msg:
            error_msg = "Erreur lors de la mise à jour du bon de travail"
        else:
            error_msg = "Erreur interne du serveur"
            
        return jsonify({
            'error': error_msg,
            'debug_info': str(e)  # Toujours inclure pour le debugging
        }), 500

@bp.route('/work-orders/<int:work_order_id>/assign', methods=['PUT'])
def assign_work_order(work_order_id):
    """Assigner un bon de travail à un technicien"""
    try:
        data = request.get_json()
        technician_id = data.get('technician_id')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Vérifier que le technicien existe
        if technician_id:
            cursor.execute("SELECT name FROM users WHERE id = %s", (technician_id,))
            technician = cursor.fetchone()
            if not technician:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Technician not found'}), 404
        
        # Mettre à jour l'assignment
        cursor.execute("""
            UPDATE work_orders 
            SET assigned_technician_id = %s, 
                status = CASE 
                    WHEN %s IS NOT NULL AND status = 'pending' THEN 'assigned'
                    WHEN %s IS NULL THEN 'pending'
                    ELSE status 
                END,
                updated_at = %s
            WHERE id = %s
        """, (technician_id, technician_id, technician_id, datetime.now(), work_order_id))
        
        # Enregistrer dans l'historique
        user_id = session.get('user_id', 1)
        notes = f"Assigné à {technician['name']}" if technician_id else "Assignment retiré"
        
        cursor.execute("""
            INSERT INTO kanban_history (task_id, old_status, new_status, 
                                      moved_by, move_reason)
            VALUES (%s, %s, %s, %s, %s)
        """, (work_order_id, 'assignment_change', 'assignment_change', 
              user_id, notes))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'work_order_id': work_order_id,
            'technician_id': technician_id,
            'technician_name': technician['name'] if technician_id else None
        })
        
    except Exception as e:
        log_error(f"Erreur assignment work order: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/technicians', methods=['GET'])
def get_technicians():
    """Récupérer la liste des techniciens"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Try technicians table first, fallback to users table
        try:
            cursor.execute("""
                SELECT id, CONCAT(first_name, ' ', last_name) as name, email, phone
                FROM technicians 
                WHERE status = 'active'
                ORDER BY first_name, last_name
            """)
            technicians = cursor.fetchall()
        except:
            # Fallback to users table if technicians table doesn't exist
            cursor.execute("""
                SELECT id, name, email, department as phone, role
                FROM users 
                WHERE role IN ('technician', 'admin', 'supervisor')
                ORDER BY name
            """)
            technicians = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(technicians)
        
    except Exception as e:
        log_error(f"Erreur récupération techniciens: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/technicians/<int:id>/stats', methods=['GET'])
def technician_stats(id):
    """Récupérer les statistiques d'un technicien spécifique"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Statistiques des bons de travail assignés à ce technicien
        cursor.execute("""
            SELECT 
                COUNT(*) as total_interventions,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_interventions,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress_interventions,
                COUNT(CASE WHEN status = 'assigned' THEN 1 END) as assigned_interventions,
                AVG(CASE WHEN status = 'completed' AND estimated_duration > 0 THEN estimated_duration END) as avg_duration
            FROM work_orders 
            WHERE technician_id = %s OR technician_name = (
                SELECT CONCAT(first_name, ' ', last_name) FROM technicians WHERE id = %s
                UNION 
                SELECT name FROM users WHERE id = %s
                LIMIT 1
            )
        """, (id, id, id))
        
        stats = cursor.fetchone()
        
        # Calcul du taux de completion
        total = stats['total_interventions'] if stats['total_interventions'] else 0
        completed = stats['completed_interventions'] if stats['completed_interventions'] else 0
        completion_rate = round((completed / total * 100), 1) if total > 0 else 0
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'total_interventions': total,
            'completed_interventions': completed,
            'in_progress_interventions': stats['in_progress_interventions'] or 0,
            'assigned_interventions': stats['assigned_interventions'] or 0,
            'completion_rate': completion_rate,
            'avg_duration': round(stats['avg_duration'], 1) if stats['avg_duration'] else 0
        })
        
    except Exception as e:
        log_error(f"Erreur lors de la récupération du technicien {id}: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@bp.route('/technicians/<int:technician_id>/schedule-events', methods=['GET'])
def technician_schedule_events(technician_id):
    """Récupérer les événements du planning pour un technicien spécifique"""
    try:
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Requête pour récupérer les bons de travail assignés au technicien dans la période
        # Utiliser les vrais noms de colonnes de la table work_orders
        query = """
            SELECT 
                id,
                claim_number,
                customer_name,
                description,
                status,
                priority,
                created_at,
                scheduled_date,
                estimated_duration,
                assigned_technician_name as technician_name,
                assigned_technician_id
            FROM work_orders 
            WHERE assigned_technician_id = %s
        """
        
        params = [technician_id]
        
        # Ajouter les filtres de date si fournis
        if start_date:
            query += " AND (scheduled_date >= %s OR (scheduled_date IS NULL AND created_at >= %s))"
            params.extend([start_date, start_date])
        
        if end_date:
            query += " AND (scheduled_date <= %s OR (scheduled_date IS NULL AND created_at <= %s))"
            params.extend([end_date, end_date])
        
        query += " ORDER BY COALESCE(scheduled_date, created_at)"
        
        cursor.execute(query, params)
        work_orders = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(work_orders)
        
    except Exception as e:
        log_error(f"Erreur lors de la récupération des événements du technicien {technician_id}: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@bp.route('/work-orders/<int:work_order_id>', methods=['GET'])
def get_work_order(work_order_id):
    """Récupérer les détails d'un bon de travail spécifique"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id,
                claim_number,
                customer_name,
                description,
                status,
                priority,
                created_at,
                scheduled_date,
                estimated_duration,
                technician_name,
                technician_id
            FROM work_orders 
            WHERE id = %s
        """, (work_order_id,))
        
        work_order = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not work_order:
            return jsonify({'error': 'Work order not found', 'success': False}), 404
        
        return jsonify({'success': True, 'work_order': work_order})
        
    except Exception as e:
        log_error(f"Erreur lors de la récupération du bon de travail {work_order_id}: {e}")
        return jsonify({'error': f'Database error: {str(e)}', 'success': False}), 500

@bp.route('/kanban/stats', methods=['GET'])
def get_kanban_stats():
    """Statistiques pour le tableau Kanban"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Statistiques par statut
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM work_orders
            GROUP BY status
        """)
        status_stats = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Statistiques par priorité
        cursor.execute("""
            SELECT priority, COUNT(*) as count
            FROM work_orders
            GROUP BY priority
        """)
        priority_stats = {row['priority']: row['count'] for row in cursor.fetchall()}
        
        # Statistiques par technicien
        cursor.execute("""
            SELECT u.name, COUNT(wo.id) as count
            FROM users u
            LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id
            WHERE u.role IN ('technician', 'admin', 'supervisor')
            GROUP BY u.id, u.name
            ORDER BY count DESC
        """)
        technician_stats = {row['name']: row['count'] for row in cursor.fetchall()}
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status_stats': status_stats,
            'priority_stats': priority_stats,
            'technician_stats': technician_stats
        })
        
    except Exception as e:
        log_error(f"Erreur récupération stats Kanban: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/kanban-data', methods=['GET'])
def get_kanban_data():
    """Récupérer les données formatées pour le Kanban"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Requête pour récupérer tous les bons de travail avec les infos complètes
        query = """
            SELECT wo.*, 
                   c.name as customer_name,
                   t.name as technician_name,
                   DATE_FORMAT(wo.created_at, '%Y-%m-%d %H:%i') as formatted_created_at,
                   DATE_FORMAT(wo.scheduled_date, '%Y-%m-%d') as formatted_scheduled_date
            FROM work_orders wo
            LEFT JOIN customers c ON wo.customer_id = c.id
            LEFT JOIN users t ON wo.assigned_technician_id = t.id
            ORDER BY 
                CASE 
                    WHEN wo.priority = 'urgent' THEN 4
                    WHEN wo.priority = 'high' THEN 3
                    WHEN wo.priority = 'medium' THEN 2
                    ELSE 1
                END DESC, wo.created_at DESC
        """
        
        cursor.execute(query)
        work_orders = cursor.fetchall()
        
        # Organiser par statut pour le Kanban
        kanban_data = {
            'draft': [],
            'pending': [],
            'assigned': [],
            'in_progress': [],
            'completed': [],
            'cancelled': []
        }
        
        for wo in work_orders:
            # Assurer que le statut existe dans notre structure
            status = wo.get('status', 'pending')
            if status not in kanban_data:
                status = 'pending'
            
            kanban_data[status].append({
                'id': wo['id'],
                'claim_number': wo.get('claim_number', f"WO-{wo['id']}"),
                'customer_name': wo.get('customer_name', 'Client inconnu'),
                'technician_name': wo.get('technician_name', None),
                'description': wo.get('description', ''),
                'priority': wo.get('priority', 'medium'),
                'status': status,
                'created_at': wo.get('formatted_created_at', ''),
                'scheduled_date': wo.get('formatted_scheduled_date', ''),
                'estimated_duration': wo.get('estimated_duration', 0)
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'kanban_data': kanban_data,
            'total_count': len(work_orders),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_error(f"Erreur récupération données Kanban: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@bp.route('/dashboard-stats', methods=['GET'])
def dashboard_stats():
    """Récupérer les statistiques du dashboard"""
    try:
        conn = get_db_connection()
        if not conn:
            log_error("Database connection failed in dashboard_stats")
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Statistiques des bons de travail avec gestion d'erreur
        try:
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM work_orders 
                GROUP BY status
            """)
            work_orders_result = cursor.fetchall()
            work_orders_stats = {row['status']: row['count'] for row in work_orders_result}
        except Exception as e:
            log_error(f"Error fetching work_orders stats: {e}")
            work_orders_stats = {}
        
        # Statistiques des techniciens avec gestion d'erreur
        try:
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN status IS NULL OR status = '' THEN 'available'
                        ELSE status 
                    END as status, 
                    COUNT(*) as count 
                FROM users 
                WHERE role = 'technician' AND is_active = 1
                GROUP BY status
            """)
            technicians_result = cursor.fetchall()
            technicians_stats = {row['status']: row['count'] for row in technicians_result}
        except Exception as e:
            log_error(f"Error fetching technicians stats: {e}")
            technicians_stats = {}
        
        # Total des bons de travail
        try:
            cursor.execute("SELECT COUNT(*) as total FROM work_orders")
            total_work_orders = cursor.fetchone()['total']
        except Exception as e:
            log_error(f"Error fetching total work_orders: {e}")
            total_work_orders = 0
        
        # Total des techniciens actifs
        try:
            cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'technician' AND is_active = 1")
            total_technicians = cursor.fetchone()['total']
        except Exception as e:
            log_error(f"Error fetching total technicians: {e}")
            total_technicians = 0
        
        # Total des clients
        try:
            cursor.execute("SELECT COUNT(*) as total FROM customers")
            total_customers = cursor.fetchone()['total']
        except Exception as e:
            log_error(f"Error fetching total customers: {e}")
            total_customers = 0
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'work_orders': {
                'draft': work_orders_stats.get('draft', 0),
                'pending': work_orders_stats.get('pending', 0),
                'assigned': work_orders_stats.get('assigned', 0),
                'in_progress': work_orders_stats.get('in_progress', 0),
                'completed': work_orders_stats.get('completed', 0),
                'cancelled': work_orders_stats.get('cancelled', 0),
                'total': total_work_orders
            },
            'technicians': {
                'available': technicians_stats.get('available', 0),
                'busy': technicians_stats.get('busy', 0),
                'break': technicians_stats.get('break', 0),
                'offline': technicians_stats.get('offline', 0),
                'total': total_technicians
            },
            'customers': {
                'total': total_customers
            }
        })
        
    except Exception as e:
        log_error(f"Error in dashboard_stats endpoint: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@bp.route('/online-users', methods=['GET'])
def online_users():
    """Récupérer la liste des utilisateurs en ligne"""
    try:
        # Pour l'instant, retourner une liste simulée
        # À implémenter avec un vrai système de présence plus tard
        return jsonify({
            'users': [],
            'count': 0,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_error(f"Error fetching online users: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/presence-heartbeat', methods=['POST'])
def presence_heartbeat():
    """Recevoir un signal de présence d'un utilisateur"""
    try:
        # Pour l'instant, juste confirmer la réception
        # À implémenter avec un vrai système de présence plus tard
        return jsonify({
            'status': 'received',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_error(f"Error processing presence heartbeat: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/health')
def health_check():
    """Vérification de l'état de l'API"""
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'unhealthy',
                'database': 'disconnected',
                'timestamp': datetime.now().isoformat()
            }), 503
    except Exception as e:
        log_error(f"Health check error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500
