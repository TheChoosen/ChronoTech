"""
Routes API étendues pour les bons de travail - Assignations, Temps, Notes
"""

from flask import Blueprint, request, jsonify, session
import pymysql
from datetime import datetime
import logging
import os

# Configuration de la base de données directement
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', '192.168.50.101'),
    'user': os.getenv('MYSQL_USER', 'gsicloud'),
    'password': os.getenv('MYSQL_PASSWORD', 'TCOChoosenOne204$'),
    'database': os.getenv('MYSQL_DB', 'bdm'),
    'charset': 'utf8mb4',
    'autocommit': True
}

def get_db_connection():
    """Connexion directe à la base de données"""
    try:
        return pymysql.connect(**MYSQL_CONFIG)
    except Exception as e:
        print(f"❌ Erreur connexion DB dans work_order_extensions: {e}")
        return None

bp = Blueprint('work_order_extensions', __name__)

@bp.route('/api/work-orders/<int:work_order_id>', methods=['GET'])
def get_work_order_details(work_order_id):
    """Récupérer les détails complets d'un bon de travail"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Récupérer le bon de travail avec les détails du client et du technicien
        query = """
            SELECT wo.*, 
                   c.name as customer_name, c.phone as customer_phone, c.email as customer_email,
                   c.address as customer_address,
                   u.name as technician_name
            FROM work_orders wo
            LEFT JOIN customers c ON wo.customer_id = c.id
            LEFT JOIN users u ON wo.assigned_technician_id = u.id
            WHERE wo.id = %s
        """
        
        cursor.execute(query, (work_order_id,))
        work_order = cursor.fetchone()
        
        if not work_order:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Work order not found'}), 404
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'work_order': work_order
        })
        
    except Exception as e:
        logging.error(f"Erreur récupération détails work order {work_order_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/work-orders/<int:work_order_id>', methods=['PUT'])
def update_work_order_details(work_order_id):
    """Mettre à jour les détails d'un bon de travail"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Construire la requête de mise à jour dynamiquement
        update_fields = []
        params = []
        
        allowed_fields = ['status', 'priority', 'scheduled_date', 'description', 
                         'location_address', 'estimated_duration', 'estimated_cost',
                         'notes', 'internal_notes']
        
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = %s")
                params.append(data[field])
        
        if not update_fields:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'No fields to update'}), 400
        
        # Ajouter la date de mise à jour
        update_fields.append("updated_at = %s")
        params.append(datetime.now())
        params.append(work_order_id)
        
        query = f"UPDATE work_orders SET {', '.join(update_fields)} WHERE id = %s"
        cursor.execute(query, params)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Work order updated successfully'})
        
    except Exception as e:
        logging.error(f"Erreur mise à jour work order {work_order_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/technicians/available', methods=['GET'])
def get_available_technicians():
    """Récupérer la liste des techniciens disponibles"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        query = """
            SELECT id, name, specialty, phone, status, hourly_rate
            FROM users 
            WHERE role = 'technician' AND is_active = 1
            ORDER BY name
        """
        
        cursor.execute(query)
        technicians = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'technicians': technicians
        })
        
    except Exception as e:
        logging.error(f"Erreur récupération techniciens: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/work-orders/<int:work_order_id>/assign', methods=['POST'])
def assign_technician(work_order_id):
    """Assigner un technicien à un bon de travail"""
    try:
        data = request.get_json()
        technician_id = data.get('technician_id')
        assignment_type = data.get('assignment_type', 'primary')
        notes = data.get('notes', '')
        
        if not technician_id:
            return jsonify({'success': False, 'error': 'Technician ID required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        user_id = session.get('user_id', 1)
        
        # Insérer l'assignation
        query = """
            INSERT INTO work_order_assignments 
            (work_order_id, user_id, assigned_by_user_id, assignment_type, notes, assigned_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            work_order_id, technician_id, user_id, assignment_type, notes, datetime.now()
        ))
        
        # Si c'est une assignation principale, mettre à jour le champ assigned_technician_id
        if assignment_type == 'primary':
            cursor.execute(
                "UPDATE work_orders SET assigned_technician_id = %s WHERE id = %s",
                (technician_id, work_order_id)
            )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Technician assigned successfully'})
        
    except Exception as e:
        logging.error(f"Erreur assignation technicien: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/work-orders/<int:work_order_id>/assignments', methods=['GET'])
def get_work_order_assignments(work_order_id):
    """Récupérer les assignations d'un bon de travail"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        query = """
            SELECT woa.*, u.name as technician_name, u.specialty
            FROM work_order_assignments woa
            JOIN users u ON woa.user_id = u.id
            WHERE woa.work_order_id = %s AND woa.status = 'active'
            ORDER BY woa.assigned_at DESC
        """
        
        cursor.execute(query, (work_order_id,))
        assignments = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'assignments': assignments
        })
        
    except Exception as e:
        logging.error(f"Erreur récupération assignations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/work-orders/assignments/<int:assignment_id>', methods=['DELETE'])
def remove_assignment(assignment_id):
    """Supprimer une assignation"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Marquer comme inactive au lieu de supprimer
        cursor.execute(
            "UPDATE work_order_assignments SET status = 'inactive' WHERE id = %s",
            (assignment_id,)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Assignment removed successfully'})
        
    except Exception as e:
        logging.error(f"Erreur suppression assignation: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/work-orders/<int:work_order_id>/time', methods=['POST'])
def add_time_entry(work_order_id):
    """Ajouter une entrée de temps"""
    try:
        data = request.get_json()
        
        required_fields = ['user_id', 'start_time', 'end_time', 'description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Calculer la durée si pas fournie
        start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        
        hourly_rate = float(data.get('hourly_rate', 0))
        total_cost = (duration_minutes / 60) * hourly_rate
        
        query = """
            INSERT INTO time_tracking 
            (work_order_id, user_id, start_time, end_time, duration_minutes, 
             description, hourly_rate, total_cost)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            work_order_id, data['user_id'], data['start_time'], data['end_time'],
            duration_minutes, data['description'], hourly_rate, total_cost
        ))
        
        # Mettre à jour les totaux dans work_orders
        cursor.execute("""
            UPDATE work_orders SET 
                actual_duration = (SELECT SUM(duration_minutes) FROM time_tracking WHERE work_order_id = %s),
                actual_cost = (SELECT SUM(total_cost) FROM time_tracking WHERE work_order_id = %s)
            WHERE id = %s
        """, (work_order_id, work_order_id, work_order_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Time entry added successfully'})
        
    except Exception as e:
        logging.error(f"Erreur ajout temps: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/work-orders/<int:work_order_id>/time', methods=['GET'])
def get_time_entries(work_order_id):
    """Récupérer les entrées de temps d'un bon de travail"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        query = """
            SELECT tt.*, u.name as technician_name
            FROM time_tracking tt
            JOIN users u ON tt.user_id = u.id
            WHERE tt.work_order_id = %s
            ORDER BY tt.start_time DESC
        """
        
        cursor.execute(query, (work_order_id,))
        entries = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'entries': entries
        })
        
    except Exception as e:
        logging.error(f"Erreur récupération temps: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/work-orders/<int:work_order_id>/notes', methods=['POST'])
def add_work_order_note(work_order_id):
    """Ajouter une note à un bon de travail"""
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'success': False, 'error': 'Note content is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        user_id = session.get('user_id', 1)
        
        query = """
            INSERT INTO work_order_notes 
            (work_order_id, user_id, note_type, content, is_private)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            work_order_id, user_id, data.get('note_type', 'general'),
            content, data.get('is_private', False)
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Note added successfully'})
        
    except Exception as e:
        logging.error(f"Erreur ajout note: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/work-orders/<int:work_order_id>/notes', methods=['GET'])
def get_work_order_notes(work_order_id):
    """Récupérer les notes d'un bon de travail"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        query = """
            SELECT won.*, u.name as user_name
            FROM work_order_notes won
            JOIN users u ON won.user_id = u.id
            WHERE won.work_order_id = %s
            ORDER BY won.created_at DESC
        """
        
        cursor.execute(query, (work_order_id,))
        notes = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'notes': notes
        })
        
    except Exception as e:
        logging.error(f"Erreur récupération notes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/work_orders/<int:work_order_id>/start', methods=['POST'])
def start_work_order(work_order_id):
    """Démarrer une intervention (changer le statut à 'in_progress')"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Utilisateur non authentifié'}), 401
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Vérifier que l'utilisateur peut démarrer cette intervention
        cursor.execute("""
            SELECT assigned_technician_id, status
            FROM work_orders 
            WHERE id = %s
        """, (work_order_id,))
        
        order = cursor.fetchone()
        if not order:
            return jsonify({'success': False, 'error': 'Bon de travail non trouvé'}), 404
        
        # Vérifier les permissions
        user_role = session.get('user_role')
        if user_role not in ['admin', 'supervisor'] and order[0] != user_id:
            return jsonify({'success': False, 'error': 'Permission refusée'}), 403
        
        # Vérifier que l'intervention peut être démarrée
        if order[1] in ['completed', 'cancelled']:
            return jsonify({'success': False, 'error': 'Cette intervention ne peut plus être démarrée'}), 400
        
        # Mettre à jour le statut
        cursor.execute("""
            UPDATE work_orders 
            SET status = 'in_progress', 
                time_status = 'in_progress',
                updated_at = NOW()
            WHERE id = %s
        """, (work_order_id,))
        
        # Ajouter une entrée dans le log des temps si elle n'existe pas
        cursor.execute("""
            INSERT IGNORE INTO intervention_time_tracking 
            (work_order_id, technician_id, action, action_time, notes)
            VALUES (%s, %s, 'start', NOW(), 'Intervention démarrée depuis le dashboard')
        """, (work_order_id, user_id))
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Intervention démarrée avec succès'
        })
        
    except Exception as e:
        logging.error(f"Erreur démarrage intervention: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/work_orders/<int:work_order_id>/status', methods=['POST'])
def update_work_order_status(work_order_id):
    """Mettre à jour le statut d'un bon de travail"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['pending', 'assigned', 'in_progress', 'completed', 'cancelled']:
            return jsonify({'success': False, 'error': 'Statut invalide'}), 400
            
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Utilisateur non authentifié'}), 401
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Mettre à jour le statut
        cursor.execute("""
            UPDATE work_orders 
            SET status = %s, 
                updated_at = NOW()
            WHERE id = %s
        """, (new_status, work_order_id))
        
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'error': 'Bon de travail non trouvé'}), 404
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Statut mis à jour vers {new_status}'
        })
        
    except Exception as e:
        logging.error(f"Erreur mise à jour statut: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
