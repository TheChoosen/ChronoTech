"""
Routes Mobile pour Techniciens - Sprint 3
Interface optimisée mobile avec actions rapides
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from datetime import datetime, date, timedelta
from functools import wraps
import os
import pymysql

# Blueprint mobile
mobile_bp = Blueprint('mobile', __name__, url_prefix='/mobile')

def get_db_connection():
    """Connexion à la base de données"""
    return pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DB', 'chronotech'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def require_technician(f):
    """Décorateur pour vérifier le rôle technicien"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth_login'))
        if session.get('user_role') != 'technician':
            flash('Accès réservé aux techniciens', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@mobile_bp.route('/today')
@require_technician
def mobile_today():
    """
    Vue mobile "À faire aujourd'hui" pour techniciens
    Interface optimisée mobile avec actions rapides
    """
    technician_id = session.get('user_id')
    today = date.today()
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupérer les tâches du technicien pour aujourd'hui
            cursor.execute("""
                SELECT 
                    wot.*,
                    wo.description as wo_title,
                    wo.claim_number,
                    wo.customer_id,
                    c.name as customer_name,
                    c.phone as customer_phone,
                    v.make, v.model, v.license_plate,
                    i.id as intervention_id,
                    i.started_at as intervention_started,
                    i.ended_at as intervention_ended,
                    CASE 
                        WHEN i.started_at IS NOT NULL AND i.ended_at IS NULL THEN 'active'
                        WHEN i.ended_at IS NOT NULL THEN 'completed'
                        ELSE 'pending'
                    END as intervention_status,
                    CASE 
                        WHEN i.started_at IS NOT NULL AND i.ended_at IS NULL 
                        THEN TIMESTAMPDIFF(MINUTE, i.started_at, NOW())
                        WHEN i.started_at IS NOT NULL AND i.ended_at IS NOT NULL
                        THEN TIMESTAMPDIFF(MINUTE, i.started_at, i.ended_at)
                        ELSE 0
                    END as elapsed_minutes
                FROM work_order_tasks wot
                JOIN work_orders wo ON wot.work_order_id = wo.id
                JOIN customers c ON wo.customer_id = c.id
                LEFT JOIN vehicles v ON wo.vehicle_id = v.id
                LEFT JOIN interventions i ON wot.id = i.task_id
                WHERE wot.technician_id = %s
                AND (
                    DATE(wot.scheduled_start) = %s
                    OR (wot.scheduled_start IS NULL AND wot.status IN ('pending', 'assigned', 'in_progress'))
                    OR (i.started_at IS NOT NULL AND i.ended_at IS NULL)
                )
                ORDER BY 
                    FIELD(wot.priority, 'urgent', 'high', 'medium', 'low'),
                    FIELD(wot.status, 'in_progress', 'assigned', 'pending', 'done'),
                    wot.scheduled_start ASC,
                    wot.created_at ASC
            """, (technician_id, today))
            
            tasks = cursor.fetchall()
            
            # Statistiques rapides
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_tasks,
                    COUNT(CASE WHEN wot.status = 'done' THEN 1 END) as completed_tasks,
                    COUNT(CASE WHEN i.started_at IS NOT NULL AND i.ended_at IS NULL THEN 1 END) as active_interventions,
                    COALESCE(SUM(CASE 
                        WHEN i.started_at IS NOT NULL AND i.ended_at IS NOT NULL 
                        THEN TIMESTAMPDIFF(MINUTE, i.started_at, i.ended_at)
                        ELSE 0 
                    END), 0) as total_minutes_today
                FROM work_order_tasks wot
                LEFT JOIN interventions i ON wot.id = i.task_id
                WHERE wot.technician_id = %s
                AND (
                    DATE(wot.scheduled_start) = %s
                    OR (wot.scheduled_start IS NULL AND wot.status IN ('pending', 'assigned', 'in_progress'))
                    OR (i.started_at IS NOT NULL AND DATE(i.started_at) = %s)
                )
            """, (technician_id, today, today))
            
            stats = cursor.fetchone()
            
            return render_template('mobile/technician_today.html', 
                                 tasks=tasks, 
                                 stats=stats,
                                 today=today)
                                 
    except Exception as e:
        flash(f'Erreur lors du chargement des tâches: {str(e)}', 'error')
        return render_template('mobile/technician_today.html', tasks=[], stats={})
    finally:
        conn.close()

@mobile_bp.route('/task/<int:task_id>/start', methods=['POST'])
@require_technician
def start_task(task_id):
    """Démarrer une intervention pour une tâche"""
    technician_id = session.get('user_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Vérifier que la tâche appartient au technicien
            cursor.execute("""
                SELECT wot.*, wo.id as work_order_id 
                FROM work_order_tasks wot
                JOIN work_orders wo ON wot.work_order_id = wo.id
                WHERE wot.id = %s AND wot.technician_id = %s
            """, (task_id, technician_id))
            
            task = cursor.fetchone()
            if not task:
                return jsonify({'success': False, 'message': 'Tâche non trouvée ou non assignée'}), 404
            
            # Vérifier si intervention existe déjà
            cursor.execute("SELECT id FROM interventions WHERE task_id = %s", (task_id,))
            existing = cursor.fetchone()
            
            if existing:
                return jsonify({'success': False, 'message': 'Intervention déjà existante'}), 409
            
            # Arrêter toute intervention en cours pour ce technicien
            cursor.execute("""
                UPDATE interventions i
                JOIN work_order_tasks wot ON i.task_id = wot.id
                SET i.ended_at = NOW()
                WHERE wot.technician_id = %s 
                AND i.started_at IS NOT NULL 
                AND i.ended_at IS NULL
            """, (technician_id,))
            
            # Créer nouvelle intervention
            cursor.execute("""
                INSERT INTO interventions (work_order_id, task_id, technician_id, started_at)
                VALUES (%s, %s, %s, NOW())
            """, (task['work_order_id'], task_id, technician_id))
            
            intervention_id = cursor.lastrowid
            
            # Mettre à jour statut tâche
            cursor.execute("""
                UPDATE work_order_tasks 
                SET status = 'in_progress', started_at = NOW()
                WHERE id = %s
            """, (task_id,))
            
            conn.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Intervention démarrée',
                'intervention_id': intervention_id,
                'started_at': datetime.now().isoformat()
            })
            
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500
    finally:
        conn.close()

@mobile_bp.route('/task/<int:task_id>/stop', methods=['POST'])
@require_technician
def stop_task(task_id):
    """Arrêter une intervention"""
    technician_id = session.get('user_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupérer l'intervention active
            cursor.execute("""
                SELECT i.*, wot.technician_id
                FROM interventions i
                JOIN work_order_tasks wot ON i.task_id = wot.id
                WHERE i.task_id = %s 
                AND wot.technician_id = %s
                AND i.started_at IS NOT NULL 
                AND i.ended_at IS NULL
            """, (task_id, technician_id))
            
            intervention = cursor.fetchone()
            if not intervention:
                return jsonify({'success': False, 'message': 'Aucune intervention active trouvée'}), 404
            
            # Arrêter l'intervention
            cursor.execute("""
                UPDATE interventions 
                SET ended_at = NOW()
                WHERE id = %s
            """, (intervention['id'],))
            
            # Mettre à jour statut tâche
            cursor.execute("""
                UPDATE work_order_tasks 
                SET status = 'done', completed_at = NOW()
                WHERE id = %s
            """, (task_id,))
            
            conn.commit()
            
            # Calculer durée
            cursor.execute("""
                SELECT TIMESTAMPDIFF(MINUTE, started_at, ended_at) as duration_minutes
                FROM interventions WHERE id = %s
            """, (intervention['id'],))
            
            duration = cursor.fetchone()
            
            return jsonify({
                'success': True,
                'message': 'Intervention terminée',
                'duration_minutes': duration['duration_minutes'],
                'ended_at': datetime.now().isoformat()
            })
            
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500
    finally:
        conn.close()

@mobile_bp.route('/task/<int:task_id>/add_note', methods=['POST'])
@require_technician
def add_quick_note(task_id):
    """Ajouter une note rapide à une intervention"""
    technician_id = session.get('user_id')
    note_content = request.form.get('note', '').strip()
    
    if not note_content:
        return jsonify({'success': False, 'message': 'Contenu de la note requis'}), 400
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupérer l'intervention
            cursor.execute("""
                SELECT i.id
                FROM interventions i
                JOIN work_order_tasks wot ON i.task_id = wot.id
                WHERE i.task_id = %s AND wot.technician_id = %s
            """, (task_id, technician_id))
            
            intervention = cursor.fetchone()
            if not intervention:
                return jsonify({'success': False, 'message': 'Intervention non trouvée'}), 404
            
            # Ajouter la note
            cursor.execute("""
                INSERT INTO intervention_notes (intervention_id, author_user_id, note)
                VALUES (%s, %s, %s)
            """, (intervention['id'], technician_id, note_content))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Note ajoutée',
                'note_id': cursor.lastrowid
            })
            
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500
    finally:
        conn.close()

@mobile_bp.route('/intervention/<int:intervention_id>/details')
@require_technician  
def intervention_mobile_details(intervention_id):
    """Vue détaillée mobile d'une intervention"""
    technician_id = session.get('user_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupérer intervention avec contexte
            cursor.execute("""
                SELECT 
                    i.*,
                    wot.title as task_title,
                    wot.description as task_description,
                    wot.priority,
                    wot.status as task_status,
                    wo.claim_number,
                    wo.description as wo_title,
                    c.name as customer_name,
                    c.phone as customer_phone,
                    v.make, v.model, v.license_plate,
                    CASE 
                        WHEN i.started_at IS NOT NULL AND i.ended_at IS NULL 
                        THEN TIMESTAMPDIFF(MINUTE, i.started_at, NOW())
                        WHEN i.started_at IS NOT NULL AND i.ended_at IS NOT NULL
                        THEN TIMESTAMPDIFF(MINUTE, i.started_at, i.ended_at)
                        ELSE 0
                    END as elapsed_minutes
                FROM interventions i
                JOIN work_order_tasks wot ON i.task_id = wot.id
                JOIN work_orders wo ON i.work_order_id = wo.id
                JOIN customers c ON wo.customer_id = c.id
                LEFT JOIN vehicles v ON wo.vehicle_id = v.id
                WHERE i.id = %s AND wot.technician_id = %s
            """, (intervention_id, technician_id))
            
            intervention = cursor.fetchone()
            if not intervention:
                flash('Intervention non trouvée', 'error')
                return redirect(url_for('mobile.mobile_today'))
            
            # Récupérer les notes
            cursor.execute("""
                SELECT in_.*, u.name as author_name
                FROM intervention_notes in_
                JOIN users u ON in_.author_user_id = u.id
                WHERE in_.intervention_id = %s
                ORDER BY in_.created_at DESC
            """, (intervention_id,))
            notes = cursor.fetchall()
            
            # Récupérer les médias
            cursor.execute("""
                SELECT * FROM intervention_media
                WHERE intervention_id = %s
                ORDER BY created_at DESC
            """, (intervention_id,))
            media = cursor.fetchall()
            
            return render_template('mobile/intervention_details.html',
                                 intervention=intervention,
                                 notes=notes,
                                 media=media)
                                 
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
        return redirect(url_for('mobile.mobile_today'))
    finally:
        conn.close()

@mobile_bp.route('/stats')
@require_technician
def mobile_stats():
    """Statistiques mobiles pour le technicien"""
    technician_id = session.get('user_id')
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Stats du jour
            cursor.execute("""
                SELECT 
                    COUNT(*) as tasks_today,
                    COUNT(CASE WHEN wot.status = 'done' THEN 1 END) as completed_today,
                    COALESCE(SUM(CASE 
                        WHEN i.started_at IS NOT NULL AND i.ended_at IS NOT NULL 
                        THEN TIMESTAMPDIFF(MINUTE, i.started_at, i.ended_at)
                        ELSE 0 
                    END), 0) as minutes_today
                FROM work_order_tasks wot
                LEFT JOIN interventions i ON wot.id = i.task_id
                WHERE wot.technician_id = %s
                AND (
                    DATE(wot.scheduled_start) = %s
                    OR (i.started_at IS NOT NULL AND DATE(i.started_at) = %s)
                )
            """, (technician_id, today, today))
            
            today_stats = cursor.fetchone()
            
            # Stats de la semaine
            cursor.execute("""
                SELECT 
                    COUNT(*) as tasks_week,
                    COUNT(CASE WHEN wot.status = 'done' THEN 1 END) as completed_week,
                    COALESCE(SUM(CASE 
                        WHEN i.started_at IS NOT NULL AND i.ended_at IS NOT NULL 
                        THEN TIMESTAMPDIFF(MINUTE, i.started_at, i.ended_at)
                        ELSE 0 
                    END), 0) as minutes_week
                FROM work_order_tasks wot
                LEFT JOIN interventions i ON wot.id = i.task_id
                WHERE wot.technician_id = %s
                AND (
                    DATE(wot.scheduled_start) >= %s
                    OR (i.started_at IS NOT NULL AND DATE(i.started_at) >= %s)
                )
            """, (technician_id, week_start, week_start))
            
            week_stats = cursor.fetchone()
            
            return jsonify({
                'today': today_stats,
                'week': week_stats,
                'week_start': week_start.isoformat()
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
