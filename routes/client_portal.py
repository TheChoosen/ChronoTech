"""
ChronoTech - Portail Client Sécurisé Sprint 3
Système de suivi temps réel pour les clients
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from core.database import get_db_connection
from core.security import generate_client_token, verify_client_token, token_required
import logging
from datetime import datetime, timedelta
import hashlib
import secrets

client_portal_bp = Blueprint('client_portal', __name__, url_prefix='/client')
logger = logging.getLogger(__name__)

@client_portal_bp.route('/view')
def client_view():
    """
    Portail client sécurisé - Point d'entrée principal
    URL: /client/view?id=<work_order_id>&token=<security_token>
    """
    work_order_id = request.args.get('id')
    token = request.args.get('token')
    
    if not work_order_id or not token:
        return render_template('client/error.html', 
                             error="Lien invalide ou expiré"), 400
    
    # Vérifier le token sécurisé
    if not verify_client_token(work_order_id, token):
        logger.warning(f"Token invalide pour work_order {work_order_id}")
        return render_template('client/error.html', 
                             error="Lien invalide ou expiré"), 403
    
    # Récupérer les informations du bon de travail
    work_order = get_work_order_for_client(work_order_id)
    if not work_order:
        return render_template('client/error.html', 
                             error="Intervention non trouvée"), 404
    
    # Marquer l'accès client
    log_client_access(work_order_id, request.remote_addr)
    
    return render_template('client/work_order_tracking.html', 
                         work_order=work_order, token=token)

@client_portal_bp.route('/api/progress/<int:work_order_id>')
def get_progress(work_order_id):
    """API pour récupérer le progrès en temps réel"""
    token = request.args.get('token')
    
    if not verify_client_token(work_order_id, token):
        return jsonify({'error': 'Token invalide'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Récupérer l'état actuel du bon de travail
        cursor.execute("""
            SELECT 
                wo.*,
                c.name as customer_name,
                c.email as customer_email,
                u.name as technician_name,
                u.phone as technician_phone,
                wo.status,
                wo.priority,
                wo.estimated_duration,
                wo.actual_start_time,
                wo.actual_end_time,
                wo.created_at,
                wo.updated_at
            FROM work_orders wo
            LEFT JOIN customers c ON wo.customer_id = c.id
            LEFT JOIN users u ON wo.technician_id = u.id
            WHERE wo.id = %s
        """, (work_order_id,))
        
        work_order = cursor.fetchone()
        if not work_order:
            return jsonify({'error': 'Bon de travail non trouvé'}), 404
        
        # Calculer le pourcentage de progression
        progress_percent = calculate_progress_percentage(work_order['status'])
        
        # Récupérer les tâches/étapes
        cursor.execute("""
            SELECT 
                task_name,
                description,
                status,
                completed_at,
                estimated_duration,
                actual_duration
            FROM work_order_tasks 
            WHERE work_order_id = %s 
            ORDER BY task_order ASC
        """, (work_order_id,))
        
        tasks = cursor.fetchall()
        
        # Récupérer les notes client (publiques)
        cursor.execute("""
            SELECT 
                content,
                created_at,
                created_by_name
            FROM work_order_notes 
            WHERE work_order_id = %s 
            AND is_client_visible = 1
            ORDER BY created_at DESC
            LIMIT 10
        """, (work_order_id,))
        
        notes = cursor.fetchall() or []
        
        # Calculer ETA
        eta = calculate_eta(work_order, tasks)
        
        return jsonify({
            'success': True,
            'progress_percent': progress_percent,
            'status': work_order['status'],
            'status_label': get_status_label(work_order['status']),
            'technician_name': work_order['technician_name'],
            'technician_phone': work_order['technician_phone'],
            'eta': eta.isoformat() if eta else None,
            'tasks': tasks,
            'notes': notes,
            'last_updated': work_order['updated_at'].isoformat() if work_order['updated_at'] else None
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération progrès: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@client_portal_bp.route('/api/generate-link/<int:work_order_id>', methods=['POST'])
@token_required
def generate_client_link(work_order_id):
    """
    Générer un lien sécurisé pour le client
    Utilisé par les techniciens/superviseurs
    """
    try:
        # Vérifier que le bon de travail existe
        work_order = get_work_order_for_client(work_order_id)
        if not work_order:
            return jsonify({'error': 'Bon de travail non trouvé'}), 404
        
        # Générer le token sécurisé
        token = generate_client_token(work_order_id)
        
        # Sauvegarder le token en base
        save_client_token(work_order_id, token)
        
        # Construire l'URL complète
        from flask import current_app
        base_url = current_app.config.get('BASE_URL', 'http://localhost:5020')
        client_url = f"{base_url}/client/view?id={work_order_id}&token={token}"
        
        return jsonify({
            'success': True,
            'client_url': client_url,
            'expires_at': (datetime.now() + timedelta(days=7)).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur génération lien client: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

def get_work_order_for_client(work_order_id):
    """Récupérer un bon de travail pour affichage client"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                wo.*,
                c.name as customer_name,
                c.email as customer_email,
                c.phone as customer_phone,
                v.make, v.model, v.year,
                v.license_plate
            FROM work_orders wo
            LEFT JOIN customers c ON wo.customer_id = c.id
            LEFT JOIN vehicles v ON wo.vehicle_id = v.id
            WHERE wo.id = %s
        """, (work_order_id,))
        
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"Erreur récupération work_order {work_order_id}: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def calculate_progress_percentage(status):
    """Calculer le pourcentage de progression selon le statut"""
    status_progress = {
        'draft': 5,
        'pending': 10,
        'assigned': 20,
        'in_progress': 60,
        'completed': 100,
        'cancelled': 0
    }
    return status_progress.get(status, 0)

def get_status_label(status):
    """Labels français pour les statuts"""
    labels = {
        'draft': 'Brouillon',
        'pending': 'En attente',
        'assigned': 'Assigné',
        'in_progress': 'En cours',
        'completed': 'Terminé',
        'cancelled': 'Annulé'
    }
    return labels.get(status, status)

def calculate_eta(work_order, tasks):
    """Calculer l'ETA basé sur les tâches et durée estimée"""
    try:
        if work_order['status'] == 'completed':
            return work_order['actual_end_time']
        
        if work_order['status'] in ['draft', 'pending']:
            return None
        
        if work_order['actual_start_time']:
            start_time = work_order['actual_start_time']
            estimated_duration = work_order['estimated_duration'] or 120  # 2h par défaut
            return start_time + timedelta(minutes=estimated_duration)
        
        return None
    except Exception:
        return None

def save_client_token(work_order_id, token):
    """Sauvegarder le token client en base"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO client_tokens (work_order_id, token, expires_at, created_at)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            token = VALUES(token),
            expires_at = VALUES(expires_at),
            updated_at = NOW()
        """, (
            work_order_id, 
            token, 
            datetime.now() + timedelta(days=7),
            datetime.now()
        ))
        
        conn.commit()
    except Exception as e:
        logger.error(f"Erreur sauvegarde token: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def log_client_access(work_order_id, ip_address):
    """Logger les accès clients pour audit"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO client_access_logs (work_order_id, ip_address, accessed_at)
            VALUES (%s, %s, %s)
        """, (work_order_id, ip_address, datetime.now()))
        
        conn.commit()
    except Exception as e:
        logger.error(f"Erreur log accès client: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
