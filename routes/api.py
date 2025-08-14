"""
Module API REST - ChronoTech
Endpoints pour l'intégration mobile et externe
"""

from flask import Blueprint, request, jsonify, session
import pymysql
from config import get_db_config
from utils import log_info, log_error, log_warning
from datetime import datetime
import json

# Création du blueprint
bp = Blueprint('api', __name__)

def get_db_connection():
    """Obtient une connexion à la base de données"""
    try:
        return pymysql.connect(**get_db_config())
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

@bp.route('/health')
def health_check():
    """Vérification de l'état de l'API"""
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            db_status = 'connected'
        else:
            db_status = 'disconnected'
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': db_status,
            'version': '1.0.0'
        })
    except Exception as e:
        log_error(f"Erreur lors de la vérification de santé: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 503

@bp.route('/work_orders', methods=['GET'])
@require_auth
def get_work_orders():
    """Récupérer la liste des bons de travail"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Paramètres de filtrage
        status = request.args.get('status')
        priority = request.args.get('priority')
        technician_id = request.args.get('technician_id')
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100
        offset = int(request.args.get('offset', 0))
        
        # Construction de la requête
        query = """
            SELECT 
                w.id,
                w.claim_number,
                w.customer_name,
                w.customer_address,
                w.customer_phone,
                w.description,
                w.priority,
                w.status,
                w.estimated_duration,
                w.scheduled_date,
                w.created_at,
                w.updated_at,
                u.name as technician_name,
                u.email as technician_email
            FROM work_orders w
            LEFT JOIN users u ON w.assigned_technician_id = u.id
            WHERE 1=1
        """
        
        params = []
        
        if status:
            query += " AND w.status = %s"
            params.append(status)
        
        if priority:
            query += " AND w.priority = %s"
            params.append(priority)
        
        if technician_id:
            query += " AND w.assigned_technician_id = %s"
            params.append(technician_id)
        
        query += " ORDER BY w.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        work_orders = cursor.fetchall()
        
        # Conversion des dates en ISO format
        for order in work_orders:
            for key, value in order.items():
                if isinstance(value, datetime):
                    order[key] = value.isoformat()
        
        # Compter le total pour la pagination
        count_query = "SELECT COUNT(*) as total FROM work_orders w WHERE 1=1"
        count_params = []
        
        if status:
            count_query += " AND w.status = %s"
            count_params.append(status)
        
        if priority:
            count_query += " AND w.priority = %s"
            count_params.append(priority)
        
        if technician_id:
            count_query += " AND w.assigned_technician_id = %s"
            count_params.append(technician_id)
        
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()['total']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'work_orders': work_orders,
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_next': offset + limit < total
            }
        })
        
    except Exception as e:
        log_error(f"Erreur API lors de la récupération des bons de travail: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/work_orders/<int:work_order_id>', methods=['GET'])
@require_auth
def get_work_order(work_order_id):
    """Récupérer un bon de travail spécifique"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                w.*,
                u.name as technician_name,
                u.email as technician_email,
                u.phone as technician_phone,
                c.name as customer_name,
                c.company as customer_company,
                c.email as customer_email
            FROM work_orders w
            LEFT JOIN users u ON w.assigned_technician_id = u.id
            LEFT JOIN customers c ON w.customer_id = c.id
            WHERE w.id = %s
        """, (work_order_id,))
        
        work_order = cursor.fetchone()
        
        if not work_order:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Work order not found'}), 404
        
        # Conversion des dates
        for key, value in work_order.items():
            if isinstance(value, datetime):
                work_order[key] = value.isoformat()
        
        cursor.close()
        conn.close()
        
        return jsonify({'work_order': work_order})
        
    except Exception as e:
        log_error(f"Erreur API lors de la récupération du bon de travail {work_order_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/work_orders/<int:work_order_id>/status', methods=['PUT'])
@require_auth
def update_work_order_status(work_order_id):
    """Mettre à jour le statut d'un bon de travail"""
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
        
        new_status = data['status']
        valid_statuses = ['pending', 'assigned', 'in_progress', 'completed', 'cancelled', 'on_hold']
        
        if new_status not in valid_statuses:
            return jsonify({'error': 'Invalid status', 'valid_statuses': valid_statuses}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE work_orders 
            SET status = %s, updated_at = NOW()
            WHERE id = %s
        """, (new_status, work_order_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Work order not found'}), 404
        
        conn.commit()
        cursor.close()
        conn.close()
        
        log_info(f"API: Statut du bon de travail {work_order_id} mis à jour vers {new_status}")
        
        return jsonify({
            'success': True,
            'work_order_id': work_order_id,
            'new_status': new_status,
            'updated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_error(f"Erreur API lors de la mise à jour du statut du bon de travail {work_order_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/work_orders', methods=['POST'])
@require_auth
def create_work_order():
    """Créer un nouveau bon de travail"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data required'}), 400
        
        # Validation des champs requis
        required_fields = ['customer_name', 'description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Générer un numéro de réclamation unique
        cursor.execute("SELECT COUNT(*) as count FROM work_orders WHERE DATE(created_at) = CURDATE()")
        daily_count = cursor.fetchone()[0] + 1
        claim_number = f"WO-{datetime.now().strftime('%Y%m%d')}-{daily_count:03d}"
        
        cursor.execute("""
            INSERT INTO work_orders (
                claim_number, customer_name, customer_address, customer_phone,
                description, priority, status, estimated_duration, scheduled_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            claim_number,
            data.get('customer_name'),
            data.get('customer_address', ''),
            data.get('customer_phone', ''),
            data.get('description'),
            data.get('priority', 'medium'),
            data.get('status', 'pending'),
            data.get('estimated_duration'),
            data.get('scheduled_date')
        ))
        
        work_order_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        log_info(f"API: Nouveau bon de travail créé: {claim_number} (ID: {work_order_id})")
        
        return jsonify({
            'success': True,
            'work_order_id': work_order_id,
            'claim_number': claim_number,
            'created_at': datetime.now().isoformat()
        }), 201
        
    except Exception as e:
        log_error(f"Erreur API lors de la création du bon de travail: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/technicians', methods=['GET'])
@require_auth
def get_technicians():
    """Récupérer la liste des techniciens"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                u.id,
                u.name,
                u.email,
                u.role,
                u.is_active,
                COUNT(w.id) as active_orders,
                COALESCE(SUM(w.estimated_duration), 0) as total_workload_minutes
            FROM users u
            LEFT JOIN work_orders w ON u.id = w.assigned_technician_id 
                AND w.status IN ('assigned', 'in_progress')
            WHERE u.role IN ('technician', 'supervisor', 'manager') 
            AND u.is_active = TRUE
            GROUP BY u.id, u.name, u.email, u.role, u.is_active
            ORDER BY u.name ASC
        """)
        
        technicians = cursor.fetchall()
        
        # Ajouter des informations calculées
        for tech in technicians:
            tech['workload_hours'] = round(tech['total_workload_minutes'] / 60, 1)
            tech['availability_status'] = 'available' if tech['active_orders'] < 3 else 'busy'
        
        cursor.close()
        conn.close()
        
        return jsonify({'technicians': technicians})
        
    except Exception as e:
        log_error(f"Erreur API lors de la récupération des techniciens: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/customers', methods=['GET'])
@require_auth
def get_customers():
    """Récupérer la liste des clients"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Paramètres de recherche
        search = request.args.get('search', '').strip()
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))
        
        if search:
            cursor.execute("""
                SELECT id, name, company, email, phone, address, created_at
                FROM customers 
                WHERE is_active = TRUE 
                AND (name LIKE %s OR company LIKE %s OR email LIKE %s)
                ORDER BY name ASC
                LIMIT %s OFFSET %s
            """, (f"%{search}%", f"%{search}%", f"%{search}%", limit, offset))
        else:
            cursor.execute("""
                SELECT id, name, company, email, phone, address, created_at
                FROM customers 
                WHERE is_active = TRUE
                ORDER BY name ASC
                LIMIT %s OFFSET %s
            """, (limit, offset))
        
        customers = cursor.fetchall()
        
        # Conversion des dates
        for customer in customers:
            for key, value in customer.items():
                if isinstance(value, datetime):
                    customer[key] = value.isoformat()
        
        cursor.close()
        conn.close()
        
        return jsonify({'customers': customers})
        
    except Exception as e:
        log_error(f"Erreur API lors de la récupération des clients: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/stats', methods=['GET'])
@require_auth
def get_stats():
    """Récupérer les statistiques générales"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        stats = {}
        
        # Statistiques des bons de travail
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'assigned' THEN 1 ELSE 0 END) as assigned,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN priority = 'urgent' THEN 1 ELSE 0 END) as urgent
            FROM work_orders
        """)
        
        work_order_stats = cursor.fetchone()
        stats['work_orders'] = work_order_stats
        
        # Statistiques des techniciens
        cursor.execute("""
            SELECT 
                COUNT(*) as total_technicians,
                SUM(CASE WHEN role = 'technician' THEN 1 ELSE 0 END) as technicians,
                SUM(CASE WHEN role = 'supervisor' THEN 1 ELSE 0 END) as supervisors,
                SUM(CASE WHEN role = 'manager' THEN 1 ELSE 0 END) as managers
            FROM users 
            WHERE role IN ('technician', 'supervisor', 'manager') AND is_active = TRUE
        """)
        
        technician_stats = cursor.fetchone()
        stats['technicians'] = technician_stats
        
        # Statistiques des clients
        cursor.execute("SELECT COUNT(*) as total_customers FROM customers WHERE is_active = TRUE")
        customer_stats = cursor.fetchone()
        stats['customers'] = customer_stats
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_error(f"Erreur API lors de la récupération des statistiques: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.errorhandler(404)
def api_not_found(error):
    """Gestionnaire d'erreur 404 pour l'API"""
    return jsonify({'error': 'Endpoint not found'}), 404

@bp.errorhandler(405)
def api_method_not_allowed(error):
    """Gestionnaire d'erreur 405 pour l'API"""
    return jsonify({'error': 'Method not allowed'}), 405

@bp.errorhandler(500)
def api_internal_error(error):
    """Gestionnaire d'erreur 500 pour l'API"""
    log_error(f"Erreur interne de l'API: {error}")
    return jsonify({'error': 'Internal server error'}), 500
