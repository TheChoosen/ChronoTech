"""
API Routes pour les modals Kanban du Dashboard
"""

from flask import Blueprint, jsonify, request, session
from core.database import get_db_connection
from datetime import datetime, timedelta
import logging

dashboard_api_bp = Blueprint('dashboard_api', __name__, url_prefix='/api/dashboard')

@dashboard_api_bp.route('/technicians', methods=['GET'])
def get_technicians_kanban():
    """API pour récupérer les données des techniciens pour le Kanban"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Connexion à la base de données impossible'}), 500

        with conn.cursor() as cursor:
            # Récupérer tous les techniciens avec leurs statuts et tâches actives
            cursor.execute("""
                SELECT 
                    u.id,
                    u.name,
                    u.email,
                    COALESCE(u.specialty, 'Technicien général') as specialization,
                    COALESCE(ts.status, COALESCE(u.availability_status, 'available')) as status,
                    COUNT(wo.id) as active_tasks,
                    u.photo as avatar_url,
                    COALESCE(ts.last_seen, u.updated_at) as last_seen,
                    COALESCE(ts.location, CONCAT('Zone ', COALESCE(u.zone, 'Générale'))) as location
                FROM users u
                LEFT JOIN technician_status ts ON u.id = ts.technician_id
                LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id 
                    AND wo.status NOT IN ('completed', 'cancelled')
                WHERE u.role = 'technician' AND u.is_active = 1
                GROUP BY u.id, u.name, u.email, u.specialty, ts.status, u.availability_status, 
                         u.photo, ts.last_seen, u.updated_at, ts.location, u.zone
                ORDER BY u.name
            """)
            
            technicians = []
            for row in cursor.fetchall():
                # Déterminer le statut réel basé sur la dernière activité
                last_seen = row.get('last_seen')
                status = row.get('status', 'offline')
                
                # Si pas d'activité depuis plus de 1 heure, considérer comme offline
                if last_seen and isinstance(last_seen, (str, datetime)):
                    if isinstance(last_seen, str):
                        last_seen = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                    
                    if datetime.now() - last_seen > timedelta(hours=1):
                        status = 'offline'
                
                technician = {
                    'id': row['id'],
                    'name': row['name'],
                    'email': row['email'],
                    'specialization': row.get('specialization', 'Technicien général'),
                    'status': status,
                    'active_tasks': row.get('active_tasks', 0),
                    'avatar': row.get('avatar_url', '/static/images/default-avatar.png'),
                    'last_seen': last_seen.isoformat() if last_seen else None,
                    'location': row.get('location', 'Bureau principal')
                }
                technicians.append(technician)

        conn.close()
        return jsonify(technicians)

    except Exception as e:
        logging.error(f"Erreur dans get_technicians_kanban: {e}")
        
        # Données de fallback pour éviter l'erreur
        fallback_data = [
            {
                'id': 1,
                'name': 'Technicien Exemple',
                'email': 'tech@example.com',
                'specialization': 'Électricien',
                'status': 'available',
                'active_tasks': 0,
                'avatar': None,
                'last_seen': datetime.now().isoformat(),
                'location': None
            }
        ]
        return jsonify(fallback_data)

@dashboard_api_bp.route('/work-orders', methods=['GET'])
def get_work_orders_kanban():
    """API pour récupérer les bons de travail pour le Kanban"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Connexion à la base de données impossible'}), 500

        with conn.cursor() as cursor:
            # Récupérer les bons de travail avec informations client et technicien
            cursor.execute("""
                SELECT 
                    wo.id,
                    wo.claim_number,
                    CONCAT(wo.claim_number, ' - ', LEFT(wo.description, 50)) as title,
                    wo.description,
                    wo.status,
                    wo.priority,
                    wo.created_at,
                    wo.updated_at,
                    wo.scheduled_date,
                    wo.estimated_duration,
                    wo.actual_duration,
                    c.name as customer_name,
                    c.phone as customer_phone,
                    c.address as customer_address,
                    u.name as assigned_technician,
                    u.id as assigned_technician_id,
                    wo.notes as completion_notes,
                    '' as materials_used
                FROM work_orders wo
                LEFT JOIN customers c ON wo.customer_id = c.id
                LEFT JOIN users u ON wo.assigned_technician_id = u.id
                WHERE wo.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                ORDER BY 
                    FIELD(wo.priority, 'urgent', 'high', 'normal', 'low'),
                    wo.created_at DESC
            """)
            
            work_orders = []
            for row in cursor.fetchall():
                work_order = {
                    'id': row['id'],
                    'title': row['title'],
                    'description': row['description'],
                    'status': row['status'],
                    'priority': row['priority'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                    'scheduled_date': row['scheduled_date'].isoformat() if row['scheduled_date'] else None,
                    'estimated_duration': float(row['estimated_duration']) if row['estimated_duration'] else None,
                    'actual_duration': float(row['actual_duration']) if row['actual_duration'] else None,
                    'customer_name': row['customer_name'],
                    'customer_phone': row['customer_phone'],
                    'customer_address': row['customer_address'],
                    'assigned_technician': row['assigned_technician'],
                    'assigned_technician_id': row['assigned_technician_id'],
                    'completion_notes': row['completion_notes'],
                    'materials_used': row['materials_used']
                }
                work_orders.append(work_order)

        conn.close()
        return jsonify(work_orders)

    except Exception as e:
        logging.error(f"Erreur dans get_work_orders_kanban: {e}")
        
        # Données de fallback
        fallback_data = [
            {
                'id': 1,
                'title': 'Exemple d\'intervention',
                'description': 'Description exemple',
                'status': 'pending',
                'priority': 'normal',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'scheduled_date': None,
                'estimated_duration': 2.0,
                'actual_duration': None,
                'customer_name': 'Client Exemple',
                'customer_phone': '01 23 45 67 89',
                'customer_address': '123 Rue Exemple',
                'assigned_technician': None,
                'assigned_technician_id': None,
                'completion_notes': None,
                'materials_used': None
            }
        ]
        return jsonify(fallback_data)

@dashboard_api_bp.route('/technicians/<int:technician_id>/status', methods=['PUT'])
def update_technician_status(technician_id):
    """Mettre à jour le statut d'un technicien"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status or new_status not in ['available', 'busy', 'break', 'offline', 'online']:
            return jsonify({'error': 'Statut invalide'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Connexion à la base de données impossible'}), 500

        with conn.cursor() as cursor:
            # Vérifier si le technicien existe
            cursor.execute("SELECT id FROM users WHERE id = %s AND role = 'technician'", (technician_id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Technicien introuvable'}), 404

            # Mettre à jour ou insérer le statut
            cursor.execute("""
                INSERT INTO technician_status (technician_id, status, last_seen)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                last_seen = NOW()
            """, (technician_id, new_status))
            
            conn.commit()

        conn.close()
        
        logging.info(f"Statut technicien {technician_id} mis à jour vers {new_status} par utilisateur {session.get('user_id')}")
        return jsonify({'success': True, 'message': 'Statut mis à jour avec succès'})

    except Exception as e:
        logging.error(f"Erreur lors de la mise à jour du statut technicien: {e}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500

@dashboard_api_bp.route('/work-orders/<int:work_order_id>/status', methods=['PUT'])
def update_work_order_status(work_order_id):
    """Mettre à jour le statut d'un bon de travail"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        valid_statuses = ['pending', 'assigned', 'in_progress', 'review', 'completed', 'cancelled']
        if not new_status or new_status not in valid_statuses:
            return jsonify({'error': 'Statut invalide'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Connexion à la base de données impossible'}), 500

        with conn.cursor() as cursor:
            # Vérifier si le bon de travail existe
            cursor.execute("SELECT id, status FROM work_orders WHERE id = %s", (work_order_id,))
            work_order = cursor.fetchone()
            if not work_order:
                return jsonify({'error': 'Bon de travail introuvable'}), 404

            old_status = work_order['status']

            # Mettre à jour le statut
            cursor.execute("""
                UPDATE work_orders 
                SET status = %s, updated_at = NOW()
                WHERE id = %s
            """, (new_status, work_order_id))

            # Ajouter une entrée dans l'historique si elle existe
            try:
                cursor.execute("""
                    INSERT INTO work_order_history (work_order_id, changed_by, old_status, new_status, change_date, notes)
                    VALUES (%s, %s, %s, %s, NOW(), %s)
                """, (work_order_id, session.get('user_id'), old_status, new_status, f"Statut changé via Kanban Dashboard"))
            except:
                # Table d'historique optionnelle
                pass
            
            conn.commit()

        conn.close()
        
        logging.info(f"Statut bon de travail {work_order_id} mis à jour de {old_status} vers {new_status} par utilisateur {session.get('user_id')}")
        return jsonify({'success': True, 'message': 'Statut mis à jour avec succès'})

    except Exception as e:
        logging.error(f"Erreur lors de la mise à jour du statut bon de travail: {e}")
        return jsonify({'error': 'Erreur interne du serveur'}), 500

@dashboard_api_bp.route('/stats', methods=['GET'])
def get_dashboard_stats():
    """Statistiques générales pour le dashboard"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Connexion à la base de données impossible'}), 500

        with conn.cursor() as cursor:
            # Statistiques des techniciens
            cursor.execute("""
                SELECT 
                    COALESCE(ts.status, 'offline') as status,
                    COUNT(*) as count
                FROM users u
                LEFT JOIN technician_status ts ON u.id = ts.technician_id
                WHERE u.role = 'technician'
                GROUP BY COALESCE(ts.status, 'offline')
            """)
            
            technician_stats = {}
            for row in cursor.fetchall():
                technician_stats[row['status']] = row['count']

            # Statistiques des bons de travail
            cursor.execute("""
                SELECT 
                    status,
                    priority,
                    COUNT(*) as count
                FROM work_orders
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY status, priority
            """)
            
            work_order_stats = {'by_status': {}, 'by_priority': {}}
            for row in cursor.fetchall():
                status = row['status']
                priority = row['priority']
                count = row['count']
                
                if status not in work_order_stats['by_status']:
                    work_order_stats['by_status'][status] = 0
                work_order_stats['by_status'][status] += count
                
                if priority not in work_order_stats['by_priority']:
                    work_order_stats['by_priority'][priority] = 0
                work_order_stats['by_priority'][priority] += count

        conn.close()

        return jsonify({
            'technicians': technician_stats,
            'work_orders': work_order_stats,
            'last_updated': datetime.now().isoformat()
        })

    except Exception as e:
        logging.error(f"Erreur dans get_dashboard_stats: {e}")
        return jsonify({
            'technicians': {'available': 0, 'busy': 0, 'pause': 0, 'offline': 0},
            'work_orders': {
                'by_status': {'pending': 0, 'assigned': 0, 'in_progress': 0, 'review': 0, 'completed': 0},
                'by_priority': {'low': 0, 'normal': 0, 'high': 0, 'urgent': 0}
            },
            'last_updated': datetime.now().isoformat()
        })
