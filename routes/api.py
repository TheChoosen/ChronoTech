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

        cursor = conn.cursor()

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


@bp.route('/dashboard', methods=['GET'])
@require_auth
def get_dashboard_stats():
    """Renvoie les statistiques principales pour le tableau de bord en JSON"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # active_orders
        cursor.execute("SELECT COUNT(*) AS active_orders FROM work_orders WHERE status = 'in_progress'")
        active_row = cursor.fetchone() or {}

        # completed_today (prefer completion_date, fallback to updated_at)
        cursor.execute(
            """
            SELECT COUNT(*) AS completed_today
            FROM work_orders
            WHERE status = 'completed'
            AND (
                (completion_date IS NOT NULL AND DATE(completion_date) = CURDATE())
                OR DATE(updated_at) = CURDATE()
            )
            """
        )
        completed_row = cursor.fetchone() or {}

        # urgent_orders
        cursor.execute("SELECT COUNT(*) AS urgent_orders FROM work_orders WHERE priority = 'urgent' AND status NOT IN ('completed','cancelled')")
        urgent_row = cursor.fetchone() or {}

        # active_technicians (case-insensitive role match, fallback to status if is_active missing)
        cursor.execute("""
            SELECT COUNT(*) AS active_technicians
            FROM users
            WHERE LOWER(COALESCE(role, '')) = 'technician'
                AND (is_active = 1 OR LOWER(COALESCE(status, '')) = 'active')
        """)
        tech_row = cursor.fetchone() or {}
        cursor.close()
        conn.close()

        return jsonify({
            'active_orders': int(active_row.get('active_orders') or 0),
            'completed_today': int(completed_row.get('completed_today') or 0),
            'urgent_orders': int(urgent_row.get('urgent_orders') or 0),
            'active_technicians': int(tech_row.get('active_technicians') or 0)
        })

    except Exception as e:
        log_error(f"Erreur API lors de la récupération des stats dashboard: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/dashboard_session', methods=['GET'])
def get_dashboard_stats_session():
    """Version session (sans API key) pour le tableau de bord interne."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) AS active_orders FROM work_orders WHERE status = 'in_progress'")
        active_row = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT COUNT(*) AS completed_today
            FROM work_orders
            WHERE status = 'completed'
            AND (
                (completion_date IS NOT NULL AND DATE(completion_date) = CURDATE())
                OR DATE(updated_at) = CURDATE()
            )
            """
        )
        completed_row = cursor.fetchone() or {}

        cursor.execute("SELECT COUNT(*) AS urgent_orders FROM work_orders WHERE priority = 'urgent' AND status NOT IN ('completed','cancelled')")
        urgent_row = cursor.fetchone() or {}

        # Online technicians via presence table (fallback to users table if presence empty)
        try:
            cursor.execute("""
                SELECT COUNT(*) AS online_count
                FROM user_presence up JOIN users u ON u.id=up.user_id
                WHERE u.role='technician' AND up.last_seen >= DATE_SUB(NOW(), INTERVAL 60 SECOND)
            """)
            online_row = cursor.fetchone() or {}
            active_technicians = int(online_row.get('online_count') or 0)
        except Exception:
            cursor.execute("""
                SELECT COUNT(*) AS active_technicians
                FROM users
                WHERE LOWER(COALESCE(role, '')) = 'technician'
                    AND (is_active = 1 OR LOWER(COALESCE(status, '')) = 'active')
            """)
            r = cursor.fetchone() or {}
            active_technicians = int(r.get('active_technicians') or 0)

        cursor.close()
        conn.close()

        return jsonify({
            'active_orders': int(active_row.get('active_orders') or 0),
            'completed_today': int(completed_row.get('completed_today') or 0),
            'urgent_orders': int(urgent_row.get('urgent_orders') or 0),
            'active_technicians': active_technicians
        })
    except Exception as e:
        log_error(f"Erreur API dashboard_session: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/work_orders/<int:work_order_id>', methods=['GET'])
@require_auth
def get_work_order(work_order_id):
    """Récupérer un bon de travail spécifique"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
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

        cursor = conn.cursor()
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


@bp.route('/technicians/<int:id>/stats', methods=['GET'])
def technician_stats(id):
    """Récupérer des statistiques ciblées pour un technicien (utilisé par l'UI interne)."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Nombre total d'interventions et complétées
        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
            FROM work_orders
            WHERE assigned_technician_id = %s
            """,
            (id,),
        )
        row = cursor.fetchone() or {}
        total = int(row.get('total') or 0)
        completed = int(row.get('completed') or 0)
        completion_rate = round((completed / total) * 100) if total > 0 else 0

        # Charge actuelle (minutes) pour assigned/in_progress
        cursor.execute(
            "SELECT COALESCE(SUM(estimated_duration),0) as total_minutes FROM work_orders WHERE assigned_technician_id = %s AND status IN ('assigned','in_progress')",
            (id,),
        )
        mm = cursor.fetchone() or {}
        total_minutes = int(mm.get('total_minutes') or 0)

        # Récupérer le plafond d'heures hebdomadaire si présent
        cursor.execute("SELECT COALESCE(max_weekly_hours, max_hours, 40) as max_hours FROM users WHERE id = %s", (id,))
        mh = cursor.fetchone() or {}
        max_hours = float(mh.get('max_hours') or 40)

        current_workload = 0
        if max_hours and total_minutes:
            current_workload = round((total_minutes / 60.0) / max_hours * 100)

        # Pour l'instant, utiliser le taux de complétion comme proxy d'efficacité
        efficiency_score = completion_rate

        cursor.close()
        conn.close()

        return jsonify({
            'total_interventions': total,
            'completed_interventions': completed,
            'completion_rate': completion_rate,
            'current_workload': current_workload,
            'efficiency_score': efficiency_score,
        })

    except Exception as e:
        log_error(f"Erreur API technician_stats pour {id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/customers', methods=['GET'])
@require_auth
def get_customers():
    """Récupérer la liste des clients"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

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

        cursor = conn.cursor()

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

@bp.route('/trend_data', methods=['GET'])
@require_auth
def get_trend_data():
    """Récupérer les données de tendance pour les graphiques"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # Type de données demandé (par défaut: monthly)
        data_type = request.args.get('type', 'monthly')

        if data_type == 'monthly':
            # Données mensuelles des 12 derniers mois
            cursor.execute("""
                SELECT 
                    DATE_FORMAT(created_at, '%Y-%m') as period,
                    COUNT(*) as count,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN priority = 'urgent' THEN 1 ELSE 0 END) as urgent
                FROM work_orders 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
                GROUP BY DATE_FORMAT(created_at, '%Y-%m')
                ORDER BY period
            """)
        elif data_type == 'weekly':
            # Données hebdomadaires des 8 dernières semaines
            cursor.execute("""
                SELECT 
                    CONCAT(YEAR(created_at), '-W', LPAD(WEEK(created_at), 2, '0')) as period,
                    COUNT(*) as count,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN priority = 'urgent' THEN 1 ELSE 0 END) as urgent
                FROM work_orders 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 8 WEEK)
                GROUP BY YEAR(created_at), WEEK(created_at)
                ORDER BY period
            """)
        elif data_type == 'daily':
            # Données quotidiennes des 30 derniers jours
            cursor.execute("""
                SELECT 
                    DATE(created_at) as period,
                    COUNT(*) as count,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN priority = 'urgent' THEN 1 ELSE 0 END) as urgent
                FROM work_orders 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY DATE(created_at)
                ORDER BY period
            """)
        else:
            return jsonify({'error': 'Invalid type parameter'}), 400

        trend_data = cursor.fetchall()

        # Formatage des données pour Chart.js
        labels = []
        total_data = []
        completed_data = []
        urgent_data = []

        for row in trend_data:
            labels.append(str(row['period']))
            total_data.append(row['count'])
            completed_data.append(row['completed'])
            urgent_data.append(row['urgent'])

        cursor.close()
        conn.close()

        return jsonify({
            'labels': labels,
            'datasets': [
                {
                    'label': 'Total',
                    'data': total_data,
                    'borderColor': 'rgb(75, 192, 192)',
                    'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                    'tension': 0.1
                },
                {
                    'label': 'Complétés',
                    'data': completed_data,
                    'borderColor': 'rgb(54, 162, 235)',
                    'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                    'tension': 0.1
                },
                {
                    'label': 'Urgents',
                    'data': urgent_data,
                    'borderColor': 'rgb(255, 99, 132)',
                    'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                    'tension': 0.1
                }
            ],
            'type': data_type,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        log_error(f"Erreur API lors de la récupération des données de tendance: {e}")
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

# -------- Dashboard Enhancements: Presence, Kanban, and Chat (session-auth) --------

@bp.route('/presence/heartbeat', methods=['POST'])
def presence_heartbeat():
    """Update the current user's presence (session-based)."""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401

        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()

        # Ensure table exists
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_presence (
                user_id INT PRIMARY KEY,
                status VARCHAR(32) DEFAULT 'online',
                last_seen DATETIME NOT NULL,
                last_ip VARCHAR(45) NULL,
                user_agent VARCHAR(255) NULL,
                INDEX (last_seen)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        cursor.execute(
            """
            INSERT INTO user_presence (user_id, status, last_seen, last_ip, user_agent)
            VALUES (%s, 'online', NOW(), %s, %s)
            ON DUPLICATE KEY UPDATE status = VALUES(status), last_seen = VALUES(last_seen), last_ip = VALUES(last_ip), user_agent = VALUES(user_agent)
            """,
            (user_id, request.remote_addr, (request.headers.get('User-Agent') or '')[:255])
        )
        conn.commit()

        # Return quick summary
        cursor.execute("""
            SELECT COUNT(*) AS online_count
            FROM user_presence
            WHERE last_seen >= DATE_SUB(NOW(), INTERVAL 60 SECOND)
        """)
        online_count = int((cursor.fetchone() or {}).get('online_count') or 0)

        cursor.close()
        conn.close()
        return jsonify({'ok': True, 'online_count': online_count})
    except Exception as e:
        log_error(f"Erreur heartbeat presence: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/presence/online', methods=['GET'])
def presence_online():
    """Return currently online users based on recent heartbeat."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()

        # Join with users table for names/roles
        cursor.execute(
            """
            SELECT u.id, u.name, u.email, u.role, up.last_seen
            FROM user_presence up
            JOIN users u ON u.id = up.user_id
            WHERE up.last_seen >= DATE_SUB(NOW(), INTERVAL 60 SECOND)
            ORDER BY u.name ASC
            """
        )
        users = cursor.fetchall() or []
        cursor.close()
        conn.close()
        # Normalize datetimes
        from datetime import datetime as _dt
        for u in users:
            if isinstance(u.get('last_seen'), _dt):
                u['last_seen'] = u['last_seen'].isoformat()
        return jsonify({'users': users})
    except Exception as e:
        log_error(f"Erreur presence_online: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/kanban', methods=['GET'])
def kanban_data():
    """Return work orders grouped by status for Kanban board."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()

        # Fetch recent items per status
        cursor.execute(
            """
            SELECT w.id, w.claim_number, w.customer_name, w.priority, w.status, w.updated_at,
                   u.name AS technician_name
            FROM work_orders w
            LEFT JOIN users u ON w.assigned_technician_id = u.id
            ORDER BY FIELD(w.status,'pending','assigned','in_progress','on_hold','completed','cancelled'),
                     FIELD(w.priority,'urgent','high','medium','low'), w.updated_at DESC
            LIMIT 400
            """
        )
        rows = cursor.fetchall() or []
        cursor.close()
        conn.close()

        columns = {
            'pending': [],
            'assigned': [],
            'in_progress': [],
            'on_hold': [],
            'completed': [],
            'cancelled': []
        }
        from datetime import datetime as _dt
        for r in rows:
            # normalize dates
            if isinstance(r.get('updated_at'), _dt):
                r['updated_at'] = r['updated_at'].isoformat()
            if r.get('status') in columns:
                columns[r['status']].append(r)
        return jsonify({'columns': columns})
    except Exception as e:
        log_error(f"Erreur kanban_data: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/chat/history', methods=['GET'])
def chat_history():
    """Return last N chat messages for the global team room."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()

        # Ensure table exists
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                message TEXT NOT NULL,
                is_bot TINYINT(1) DEFAULT 0,
                channel_type VARCHAR(64) DEFAULT 'global',
                channel_id INT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX(created_at),
                INDEX(is_bot),
                INDEX(channel_type),
                INDEX(channel_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        # support optional channel filtering
        channel_type = request.args.get('channel_type') or 'global'
        channel_id = request.args.get('channel_id', type=int)
        since_id = request.args.get('since_id', type=int)
        log_info(f"chat_history request: channel_type={channel_type} channel_id={channel_id} since_id={since_id}")
        params = []
        where = "WHERE 1=1"
        if channel_type:
            where += " AND m.channel_type = %s"
            params.append(channel_type)
        if channel_id:
            where += " AND m.channel_id = %s"
            params.append(channel_id)
        if since_id:
            params = [since_id] + params
            cursor.execute("SELECT m.*, u.name as user_name FROM chat_messages m LEFT JOIN users u ON m.user_id=u.id WHERE m.id > %s " + (" AND m.channel_type = %s" if channel_type else "") + (" AND m.channel_id = %s" if channel_id else "") + " ORDER BY m.id ASC LIMIT 200", params)
        else:
            # latest N messages filtered by channel
            q = "SELECT m.*, u.name as user_name FROM chat_messages m LEFT JOIN users u ON m.user_id=u.id " + where + " ORDER BY m.id DESC LIMIT 50"
            cursor.execute(q, params)
        rows = cursor.fetchall() or []
        rows = list(reversed(rows)) if not since_id else rows

        # normalize
        from datetime import datetime as _dt
        for r in rows:
            if isinstance(r.get('created_at'), _dt):
                r['created_at'] = r['created_at'].isoformat()

        cursor.close()
        conn.close()
        return jsonify({'messages': rows})
    except Exception as e:
        log_error(f"Erreur chat_history: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/chat/send', methods=['POST'])
def chat_send():
    """Send a message to the global team room; optional echo to bot."""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        data = request.get_json(silent=True) or {}
        message = (data.get('message') or '').strip()
        if not message:
            return jsonify({'error': 'Message required'}), 400
        channel_type = (data.get('channel_type') or 'global')
        channel_id = data.get('channel_id')

        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()

        cursor.execute("INSERT INTO chat_messages (user_id, message, is_bot, channel_type, channel_id) VALUES (%s, %s, 0, %s, %s)", (user_id, message, channel_type, channel_id))
        conn.commit()
        msg_id = cursor.lastrowid

        log_info(f"chat_send: user_id={user_id} id={msg_id} channel_type={channel_type} channel_id={channel_id} message_len={len(message)}")

        cursor.close()
        conn.close()
        return jsonify({'ok': True, 'id': msg_id})
    except Exception as e:
        log_error(f"Erreur chat_send: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/chat/assistant', methods=['POST'])
def chat_assistant():
    """Simple assistant using OpenAI if configured; stores bot reply."""
    try:
        import os, requests as _requests
        api_key = os.environ.get('OPENAI_API_KEY')
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        data = request.get_json(silent=True) or {}
        message = (data.get('message') or '').strip()
        if not message:
            return jsonify({'error': 'Message required'}), 400
        channel_type = (data.get('channel_type') or 'global')
        channel_id = data.get('channel_id')

        reply = None
        if api_key:
            try:
                base = os.environ.get('OPENAI_API_BASE', 'https://api.openai.com')
                payload = {
                    'model': os.environ.get('OPENAI_CHAT_MODEL', 'gpt-4o-mini'),
                    'messages': [
                        {'role': 'system', 'content': 'Tu es un assistant ChronoTech qui aide les équipes à mieux communiquer et accélérer la gestion des bons. Réponds en français, bref et utile.'},
                        {'role': 'user', 'content': message}
                    ],
                    'temperature': 0.2,
                    'max_tokens': 600
                }
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                resp = _requests.post(f"{base}/v1/chat/completions", headers=headers, json=payload, timeout=60)
                if resp.status_code == 200:
                    jr = resp.json()
                    choices = jr.get('choices') or []
                    reply = (choices[0].get('message', {}) or {}).get('content') if choices else None
            except Exception as ee:
                log_warning(f"Assistant OpenAI erreur: {ee}")

        if not reply:
            reply = "Je ne peux pas contacter l'assistant pour le moment. Voici un rappel: utilisez le Kanban pour glisser-déposer vos bons et le chat pour coordonner."

    # Store user prompt (dedup if identical last message by same user in the last 10s) and bot reply
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()
        # Ensure table exists
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                message TEXT NOT NULL,
                is_bot TINYINT(1) DEFAULT 0,
                channel_type VARCHAR(64) DEFAULT 'global',
                channel_id INT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        try:
            cursor.execute(
                """
                SELECT id, message, created_at FROM chat_messages
                WHERE user_id = %s AND is_bot = 0
                ORDER BY id DESC LIMIT 1
                """,
                (user_id,)
            )
            last = cursor.fetchone() or {}
            should_insert_user = True
            if last and (last.get('message') or '').strip() == message.strip():
                # If last message is identical and within the last 10s, skip inserting duplicate
                try:
                    from datetime import datetime as _dt
                    if isinstance(last.get('created_at'), _dt):
                        delta = datetime.now() - last['created_at']
                        if delta.total_seconds() <= 10:
                            should_insert_user = False
                except Exception:
                    pass
            if should_insert_user:
                cursor.execute("INSERT INTO chat_messages (user_id, message, is_bot, channel_type, channel_id) VALUES (%s, %s, 0, %s, %s)", (user_id, message, channel_type, channel_id))
        except Exception:
            # On any failure of dedup logic, fallback to inserting
            try:
                cursor.execute("INSERT INTO chat_messages (user_id, message, is_bot) VALUES (%s, %s, 0)", (user_id, message))
            except Exception:
                pass
            cursor.execute("INSERT INTO chat_messages (user_id, message, is_bot, channel_type, channel_id) VALUES (NULL, %s, 1, %s, %s)", (reply, channel_type, channel_id))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'ok': True, 'reply': reply})
    except Exception as e:
        log_error(f"Erreur chat_assistant: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/chat/clear', methods=['POST'])
def chat_clear():
    """Effacer l'historique du chat (réservé admin)."""
    try:
        role = session.get('user_role')
        if role != 'admin':
            return jsonify({'error': 'Forbidden'}), 403

        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()

        # Ensure table exists
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                message TEXT NOT NULL,
                is_bot TINYINT(1) DEFAULT 0,
                channel_type VARCHAR(64) DEFAULT 'global',
                channel_id INT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        # Optionally accept channel filter to clear only a specific channel
        channel_type = request.args.get('channel_type') or None
        channel_id = request.args.get('channel_id', type=int)
        if channel_type:
            # count and delete for that channel
            qcount = "SELECT COUNT(*) AS c FROM chat_messages WHERE channel_type=%s" + (" AND channel_id=%s" if channel_id else "")
            params = [channel_type] + ([channel_id] if channel_id else [])
            cursor.execute(qcount, params)
            before = (cursor.fetchone() or {}).get('c') or 0
            qdel = "DELETE FROM chat_messages WHERE channel_type=%s" + (" AND channel_id=%s" if channel_id else "")
            cursor.execute(qdel, params)
        else:
            cursor.execute("SELECT COUNT(*) AS c FROM chat_messages")
            before = (cursor.fetchone() or {}).get('c') or 0
            cursor.execute("DELETE FROM chat_messages")
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'ok': True, 'deleted': int(before)})
    except Exception as e:
        log_error(f"Erreur chat_clear: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/departments', methods=['GET'])
def departments_list():
    """List departments (id, name, description)"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS departments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.execute("SELECT id, name, description FROM departments ORDER BY name ASC")
        rows = cursor.fetchall() or []
        cursor.close()
        conn.close()
        return jsonify({'departments': rows})
    except Exception as e:
        log_error(f"Erreur departments_list: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/departments', methods=['POST'])
def departments_create():
    """Create a department (admin only)"""
    try:
        role = session.get('user_role')
        if role != 'admin':
            return jsonify({'error': 'Forbidden'}), 403
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        description = data.get('description')
        if not name:
            return jsonify({'error': 'Name required'}), 400
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS departments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.execute("INSERT INTO departments (name, description) VALUES (%s, %s)", (name, description))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({'ok': True, 'id': new_id})
    except Exception as e:
        log_error(f"Erreur departments_create: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/departments/<int:dept_id>', methods=['PUT'])
def departments_update(dept_id):
    """Update department (admin only)"""
    try:
        role = session.get('user_role')
        if role != 'admin':
            return jsonify({'error': 'Forbidden'}), 403
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        description = data.get('description')
        if not name:
            return jsonify({'error': 'Name required'}), 400
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()
        cursor.execute("UPDATE departments SET name=%s, description=%s WHERE id=%s", (name, description, dept_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        log_error(f"Erreur departments_update: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/departments/<int:dept_id>', methods=['DELETE'])
def departments_delete(dept_id):
    """Delete department (admin only)"""
    try:
        role = session.get('user_role')
        if role != 'admin':
            return jsonify({'error': 'Forbidden'}), 403
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()
        cursor.execute("DELETE FROM departments WHERE id=%s", (dept_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        log_error(f"Erreur departments_delete: {e}")
        return jsonify({'error': 'Internal server error'}), 500
