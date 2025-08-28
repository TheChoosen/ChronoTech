"""
Routes Supervisor Dashboard - Sprint 3  
Interface Kanban avec drag & drop pour gestion des tâches
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from datetime import datetime, date, timedelta
from functools import wraps
import os
import pymysql

# Blueprint supervisor
supervisor_bp = Blueprint('supervisor', __name__, url_prefix='/supervisor')

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

def require_supervisor(f):
    """Décorateur pour vérifier le rôle superviseur/admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth_login'))
        if session.get('user_role') not in ['supervisor', 'admin']:
            flash('Accès réservé aux superviseurs et administrateurs', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@supervisor_bp.route('/dashboard')
@require_supervisor
def supervisor_dashboard():
    """
    Dashboard superviseur avec vue Kanban
    Gestion globale des tâches et assignations
    """
    # Filtres de la requête
    technician_filter = request.args.get('technician', 'all')
    priority_filter = request.args.get('priority', 'all')
    date_filter = request.args.get('date', 'today')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Construire les filtres WHERE
            where_conditions = ['1=1']
            params = []
            
            if technician_filter != 'all':
                where_conditions.append('wot.technician_id = %s')
                params.append(technician_filter)
            
            if priority_filter != 'all':
                where_conditions.append('wot.priority = %s')
                params.append(priority_filter)
            
            # Filtre de date
            if date_filter == 'today':
                where_conditions.append('(DATE(wot.scheduled_start) = CURDATE() OR (wot.scheduled_start IS NULL AND wot.status IN ("pending", "assigned", "in_progress")))')
            elif date_filter == 'week':
                where_conditions.append('(WEEK(wot.scheduled_start) = WEEK(CURDATE()) OR (wot.scheduled_start IS NULL AND wot.status IN ("pending", "assigned", "in_progress")))')
            elif date_filter == 'month':
                where_conditions.append('(MONTH(wot.scheduled_start) = MONTH(CURDATE()) OR (wot.scheduled_start IS NULL AND wot.status IN ("pending", "assigned", "in_progress")))')
            
            where_clause = ' AND '.join(where_conditions)
            
            # Récupérer toutes les tâches avec contexte complet
            cursor.execute(f"""
                SELECT 
                    wot.*,
                    wo.title as wo_title,
                    wo.claim_number,
                    wo.customer_id,
                    wo.vehicle_id,
                    c.name as customer_name,
                    c.phone as customer_phone,
                    v.make, v.model, v.license_plate,
                    t.name as technician_name,
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
                LEFT JOIN users t ON wot.technician_id = t.id
                LEFT JOIN interventions i ON wot.id = i.task_id
                WHERE {where_clause}
                ORDER BY 
                    FIELD(wot.priority, 'urgent', 'high', 'medium', 'low'),
                    wot.scheduled_start ASC,
                    wot.created_at ASC
            """, params)
            
            all_tasks = cursor.fetchall()
            
            # Organiser les tâches par statut pour Kanban
            kanban_data = {
                'pending': [],
                'assigned': [],
                'in_progress': [],
                'done': []
            }
            
            for task in all_tasks:
                status = task['status']
                if status in kanban_data:
                    kanban_data[status].append(task)
            
            # Récupérer la liste des techniciens pour les filtres
            cursor.execute("""
                SELECT id, name 
                FROM users 
                WHERE role IN ('technician', 'supervisor') 
                AND is_active = 1
                ORDER BY name
            """)
            technicians = cursor.fetchall()
            
            # Statistiques globales
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_tasks,
                    COUNT(CASE WHEN wot.status = 'pending' THEN 1 END) as pending_count,
                    COUNT(CASE WHEN wot.status = 'assigned' THEN 1 END) as assigned_count,
                    COUNT(CASE WHEN wot.status = 'in_progress' THEN 1 END) as in_progress_count,
                    COUNT(CASE WHEN wot.status = 'done' THEN 1 END) as done_count,
                    COUNT(CASE WHEN wot.priority = 'urgent' THEN 1 END) as urgent_count,
                    COUNT(CASE WHEN i.started_at IS NOT NULL AND i.ended_at IS NULL THEN 1 END) as active_interventions,
                    COALESCE(AVG(CASE 
                        WHEN i.started_at IS NOT NULL AND i.ended_at IS NOT NULL 
                        THEN TIMESTAMPDIFF(MINUTE, i.started_at, i.ended_at)
                        ELSE NULL 
                    END), 0) as avg_duration_minutes
                FROM work_order_tasks wot
                JOIN work_orders wo ON wot.work_order_id = wo.id
                LEFT JOIN interventions i ON wot.id = i.task_id
                WHERE {where_clause}
            """, params)
            
            stats = cursor.fetchone()
            
            # Charge de travail par technicien
            cursor.execute(f"""
                SELECT 
                    u.id,
                    u.name,
                    COUNT(wot.id) as task_count,
                    COUNT(CASE WHEN wot.status = 'in_progress' THEN 1 END) as active_count,
                    COUNT(CASE WHEN wot.status = 'done' THEN 1 END) as completed_count,
                    COALESCE(SUM(CASE 
                        WHEN i.started_at IS NOT NULL AND i.ended_at IS NOT NULL 
                        THEN TIMESTAMPDIFF(MINUTE, i.started_at, i.ended_at)
                        ELSE 0 
                    END), 0) as total_minutes
                FROM users u
                LEFT JOIN work_order_tasks wot ON u.id = wot.technician_id
                    AND ({where_clause.replace('wot.', 'wot.')})
                LEFT JOIN interventions i ON wot.id = i.task_id
                WHERE u.role IN ('technician', 'supervisor') AND u.is_active = 1
                GROUP BY u.id, u.name
                ORDER BY task_count DESC
            """, params)
            
            workload_stats = cursor.fetchall()
            
            return render_template('supervisor/dashboard.html',
                                 kanban_data=kanban_data,
                                 stats=stats,
                                 technicians=technicians,
                                 workload_stats=workload_stats,
                                 current_filters={
                                     'technician': technician_filter,
                                     'priority': priority_filter,
                                     'date': date_filter
                                 })
                                 
    except Exception as e:
        flash(f'Erreur lors du chargement du dashboard: {str(e)}', 'error')
        return render_template('supervisor/dashboard.html', 
                             kanban_data={'pending': [], 'assigned': [], 'in_progress': [], 'done': []},
                             stats={}, technicians=[], workload_stats=[])
    finally:
        conn.close()

@supervisor_bp.route('/assign_task', methods=['POST'])
@require_supervisor
def assign_task():
    """Assigner ou réassigner une tâche à un technicien"""
    data = request.get_json()
    task_id = data.get('task_id')
    technician_id = data.get('technician_id')
    
    if not task_id:
        return jsonify({'success': False, 'message': 'Task ID requis'}), 400
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Vérifier que la tâche existe
            cursor.execute("SELECT * FROM work_order_tasks WHERE id = %s", (task_id,))
            task = cursor.fetchone()
            if not task:
                return jsonify({'success': False, 'message': 'Tâche non trouvée'}), 404
            
            # Si technician_id est None ou vide, désassigner
            if not technician_id:
                cursor.execute("""
                    UPDATE work_order_tasks 
                    SET technician_id = NULL, status = 'pending'
                    WHERE id = %s
                """, (task_id,))
                action = 'désassignée'
            else:
                # Vérifier que le technicien existe
                cursor.execute("SELECT name FROM users WHERE id = %s AND role IN ('technician', 'supervisor')", (technician_id,))
                technician = cursor.fetchone()
                if not technician:
                    return jsonify({'success': False, 'message': 'Technicien non trouvé'}), 404
                
                # Assigner la tâche
                cursor.execute("""
                    UPDATE work_order_tasks 
                    SET technician_id = %s, status = 'assigned'
                    WHERE id = %s
                """, (technician_id, task_id))
                action = f'assignée à {technician["name"]}'
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'Tâche {action}',
                'task_id': task_id,
                'technician_id': technician_id
            })
            
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500
    finally:
        conn.close()

@supervisor_bp.route('/update_task_status', methods=['POST'])
@require_supervisor
def update_task_status():
    """Mettre à jour le statut d'une tâche"""
    data = request.get_json()
    task_id = data.get('task_id')
    new_status = data.get('status')
    
    if not task_id or not new_status:
        return jsonify({'success': False, 'message': 'Task ID et statut requis'}), 400
    
    if new_status not in ['pending', 'assigned', 'in_progress', 'done', 'cancelled']:
        return jsonify({'success': False, 'message': 'Statut invalide'}), 400
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupérer la tâche
            cursor.execute("SELECT * FROM work_order_tasks WHERE id = %s", (task_id,))
            task = cursor.fetchone()
            if not task:
                return jsonify({'success': False, 'message': 'Tâche non trouvée'}), 404
            
            # Logique de validation selon le nouveau statut
            update_fields = {'status': new_status}
            
            if new_status == 'in_progress' and not task['started_at']:
                update_fields['started_at'] = datetime.now()
            elif new_status == 'done' and not task['completed_at']:
                update_fields['completed_at'] = datetime.now()
            
            # Construire la requête UPDATE
            set_clause = ', '.join([f'{key} = %s' for key in update_fields.keys()])
            values = list(update_fields.values()) + [task_id]
            
            cursor.execute(f"""
                UPDATE work_order_tasks 
                SET {set_clause}
                WHERE id = %s
            """, values)
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'Statut mis à jour: {new_status}',
                'task_id': task_id,
                'status': new_status
            })
            
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500
    finally:
        conn.close()

@supervisor_bp.route('/task_details/<int:task_id>')
@require_supervisor
def task_details(task_id):
    """Récupérer les détails d'une tâche pour la modal"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupérer la tâche avec contexte complet
            cursor.execute("""
                SELECT 
                    wot.*,
                    wo.title as wo_title,
                    wo.claim_number,
                    c.name as customer_name,
                    c.phone as customer_phone,
                    c.email as customer_email,
                    v.make, v.model, v.license_plate,
                    t.name as technician_name,
                    i.id as intervention_id,
                    i.started_at as intervention_started,
                    i.ended_at as intervention_ended,
                    COUNT(DISTINCT in_.id) as notes_count,
                    COUNT(DISTINCT im.id) as media_count
                FROM work_order_tasks wot
                JOIN work_orders wo ON wot.work_order_id = wo.id
                JOIN customers c ON wo.customer_id = c.id
                LEFT JOIN vehicles v ON wo.vehicle_id = v.id
                LEFT JOIN users t ON wot.technician_id = t.id
                LEFT JOIN interventions i ON wot.id = i.task_id
                LEFT JOIN intervention_notes in_ ON i.id = in_.intervention_id
                LEFT JOIN intervention_media im ON i.id = im.intervention_id
                WHERE wot.id = %s
                GROUP BY wot.id
            """, (task_id,))
            
            task = cursor.fetchone()
            if not task:
                return jsonify({'success': False, 'message': 'Tâche non trouvée'}), 404
            
            # Récupérer les notes récentes
            if task['intervention_id']:
                cursor.execute("""
                    SELECT in_.note, in_.created_at, u.name as author_name
                    FROM intervention_notes in_
                    JOIN users u ON in_.author_user_id = u.id
                    WHERE in_.intervention_id = %s
                    ORDER BY in_.created_at DESC
                    LIMIT 5
                """, (task['intervention_id'],))
                recent_notes = cursor.fetchall()
            else:
                recent_notes = []
            
            # Formater les données pour JSON
            task_data = dict(task)
            for key, value in task_data.items():
                if isinstance(value, datetime):
                    task_data[key] = value.isoformat()
                elif value is None:
                    task_data[key] = None
            
            return jsonify({
                'success': True,
                'task': task_data,
                'recent_notes': [dict(note) for note in recent_notes]
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500
    finally:
        conn.close()

@supervisor_bp.route('/analytics')
@require_supervisor 
def analytics():
    """Vue analytique avancée pour superviseurs"""
    period = request.args.get('period', 'week')  # day, week, month
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Définir la période
            if period == 'day':
                date_condition = 'DATE(wot.created_at) = CURDATE()'
                date_group = 'HOUR(wot.created_at)'
            elif period == 'week':
                date_condition = 'WEEK(wot.created_at) = WEEK(CURDATE())'
                date_group = 'DAYOFWEEK(wot.created_at)'
            else:  # month
                date_condition = 'MONTH(wot.created_at) = MONTH(CURDATE())'
                date_group = 'DAY(wot.created_at)'
            
            # Métriques générales
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_tasks,
                    COUNT(CASE WHEN wot.status = 'done' THEN 1 END) as completed_tasks,
                    COUNT(CASE WHEN wot.priority = 'urgent' THEN 1 END) as urgent_tasks,
                    AVG(CASE 
                        WHEN i.started_at IS NOT NULL AND i.ended_at IS NOT NULL 
                        THEN TIMESTAMPDIFF(MINUTE, i.started_at, i.ended_at)
                        ELSE NULL 
                    END) as avg_duration_minutes,
                    COUNT(DISTINCT wot.technician_id) as active_technicians
                FROM work_order_tasks wot
                LEFT JOIN interventions i ON wot.id = i.task_id
                WHERE {date_condition}
            """)
            
            metrics = cursor.fetchone()
            
            # Performance par technicien
            cursor.execute(f"""
                SELECT 
                    u.name,
                    COUNT(wot.id) as task_count,
                    COUNT(CASE WHEN wot.status = 'done' THEN 1 END) as completed_count,
                    AVG(CASE 
                        WHEN i.started_at IS NOT NULL AND i.ended_at IS NOT NULL 
                        THEN TIMESTAMPDIFF(MINUTE, i.started_at, i.ended_at)
                        ELSE NULL 
                    END) as avg_duration
                FROM users u
                LEFT JOIN work_order_tasks wot ON u.id = wot.technician_id AND {date_condition}
                LEFT JOIN interventions i ON wot.id = i.task_id
                WHERE u.role IN ('technician', 'supervisor') AND u.is_active = 1
                GROUP BY u.id, u.name
                HAVING task_count > 0
                ORDER BY completed_count DESC
            """)
            
            technician_performance = cursor.fetchall()
            
            return render_template('supervisor/analytics.html',
                                 metrics=metrics,
                                 technician_performance=technician_performance,
                                 period=period)
                                 
    except Exception as e:
        flash(f'Erreur lors du chargement des analytics: {str(e)}', 'error')
        return render_template('supervisor/analytics.html', metrics={}, technician_performance=[])
    finally:
        conn.close()

@supervisor_bp.route('/planning')
@require_supervisor
def planning():
    """Vue planning / calendrier pour superviseurs"""
    view_type = request.args.get('view', 'week')  # day, week, month
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupérer les tâches planifiées
            cursor.execute("""
                SELECT 
                    wot.*,
                    wo.title as wo_title,
                    wo.claim_number,
                    c.name as customer_name,
                    t.name as technician_name,
                    i.started_at,
                    i.ended_at
                FROM work_order_tasks wot
                JOIN work_orders wo ON wot.work_order_id = wo.id
                JOIN customers c ON wo.customer_id = c.id
                LEFT JOIN users t ON wot.technician_id = t.id
                LEFT JOIN interventions i ON wot.id = i.task_id
                WHERE wot.scheduled_start IS NOT NULL 
                AND DATE(wot.scheduled_start) BETWEEN DATE_SUB(CURDATE(), INTERVAL 7 DAY) AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
                ORDER BY wot.scheduled_start ASC
            """)
            
            planned_tasks = cursor.fetchall()
            
            return render_template('supervisor/planning.html',
                                 planned_tasks=planned_tasks,
                                 view_type=view_type)
                                 
    except Exception as e:
        flash(f'Erreur lors du chargement du planning: {str(e)}', 'error')
        return render_template('supervisor/planning.html', planned_tasks=[])
    finally:
        conn.close()
