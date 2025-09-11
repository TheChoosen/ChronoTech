"""
API Routes sécurisées Sprint 2 - Work Orders Tasks
Architecture imbriquée /work_orders/<id>/tasks/* 
Aucune création de tâche orpheline possible
"""
import os
import pymysql
import logging
import uuid
from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime
from services.ai_guards import ai_guards, ValidationResult

logger = logging.getLogger(__name__)

# Blueprint pour les routes API des tâches
api_tasks_bp = Blueprint('api_tasks', __name__)

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

def require_auth(f):
    """Décorateur pour vérifier l'authentification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def check_work_order_access(wo_id: int, required_role: str = None) -> tuple[bool, dict]:
    """
    Vérifier l'accès à un work order selon le rôle
    Returns: (has_access, work_order_data)
    """
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT wo.*, u.name as technician_name
                FROM work_orders wo
                LEFT JOIN users u ON wo.assigned_technician_id = u.id
                WHERE wo.id = %s
            """, (wo_id,))
            
            wo = cursor.fetchone()
            if not wo:
                return False, {'error': 'Work order not found'}
            
            # Vérification des permissions selon le rôle
            if user_role == 'technician':
                # Technicien : accès seulement à ses work orders
                if wo['assigned_technician_id'] != user_id:
                    return False, {'error': 'Access denied: not assigned to you'}
            elif user_role == 'supervisor':
                # Superviseur : accès complet
                pass
            elif user_role == 'admin':
                # Admin : accès complet
                pass
            else:
                return False, {'error': 'Invalid role'}
            
            # Vérification du rôle requis pour l'action
            if required_role and user_role != required_role and user_role != 'admin':
                return False, {'error': f'Role {required_role} required'}
            
            return True, wo
    finally:
        conn.close()

def validate_task_data(data: dict) -> ValidationResult:
    """Valider les données d'une tâche"""
    required_fields = ['title', 'task_source']
    
    for field in required_fields:
        if field not in data or not data[field]:
            return ValidationResult(False, f"Field '{field}' is required")
    
    # Valider task_source
    valid_sources = ['requested', 'suggested', 'preventive']
    if data['task_source'] not in valid_sources:
        return ValidationResult(False, f"task_source must be one of: {', '.join(valid_sources)}")
    
    # Valider priority si fournie
    if 'priority' in data:
        valid_priorities = ['low', 'medium', 'high', 'urgent']
        if data['priority'] not in valid_priorities:
            return ValidationResult(False, f"priority must be one of: {', '.join(valid_priorities)}")
    
    # Valider title longueur
    if len(data['title'].strip()) < 3:
        return ValidationResult(False, "title must be at least 3 characters long")
    
    if len(data['title']) > 200:
        return ValidationResult(False, "title must not exceed 200 characters")
    
    return ValidationResult(True, "Task data is valid")

# ========================================
# ROUTES IMBRIQUÉES SÉCURISÉES
# ========================================

@api_tasks_bp.route('/work_orders/<int:wo_id>/tasks', methods=['POST'])
@require_auth
def create_task(wo_id):
    """
    Création sécurisée d'une tâche sous un Work Order existant
    IMPOSSIBLE de créer une tâche orpheline
    """
    try:
        # Vérification accès au Work Order
        has_access, wo_data = check_work_order_access(wo_id, required_role='supervisor')
        if not has_access:
            return jsonify({'success': False, 'message': wo_data.get('error', 'Access denied')}), 403
        
        # Récupération et validation des données
        data = request.get_json(force=True)
        if not data:
            return jsonify({'success': False, 'message': 'JSON data required'}), 400
        
        validation = validate_task_data(data)
        if not validation.is_valid:
            return jsonify({'success': False, 'message': validation.message}), 400
        
        # Préparation des données pour insertion
        task_data = {
            'work_order_id': wo_id,
            'title': data['title'].strip(),
            'description': data.get('description', '').strip(),
            'task_source': data['task_source'],
            'created_by': data.get('created_by', 'operator'),
            'priority': data.get('priority', 'medium'),
            'technician_id': data.get('technician_id'),
            'estimated_minutes': data.get('estimated_minutes'),
            'scheduled_start': data.get('scheduled_start'),
            'scheduled_end': data.get('scheduled_end')
        }
        
        # Insertion en base
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Insertion de la tâche
                cursor.execute("""
                    INSERT INTO work_order_tasks 
                    (work_order_id, title, description, task_source, created_by, 
                     priority, technician_id, estimated_minutes, scheduled_start, scheduled_end)
                    VALUES (%(work_order_id)s, %(title)s, %(description)s, %(task_source)s, 
                           %(created_by)s, %(priority)s, %(technician_id)s, %(estimated_minutes)s,
                           %(scheduled_start)s, %(scheduled_end)s)
                """, task_data)
                
                task_id = cursor.lastrowid
                
                # Mise à jour du statut WO si c'est la première tâche
                cursor.execute("""
                    UPDATE work_orders SET status = 'assigned', updated_at = NOW()
                    WHERE id = %s AND status = 'pending'
                """, (wo_id,))
                
                # Historisation
                cursor.execute("""
                    INSERT INTO work_order_status_history 
                    (work_order_id, old_status, new_status, changed_by_user_id)
                    VALUES (%s, 'pending', 'assigned', %s)
                """, (wo_id, session.get('user_id')))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Tâche créée avec succès',
                    'task_id': task_id,
                    'task_source': data['task_source']
                }), 201
                
        except pymysql.Error as e:
            conn.rollback()
            logger.error(f"Erreur DB création tâche WO {wo_id}: {e}")
            return jsonify({'success': False, 'message': 'Database error'}), 500
        finally:
            conn.close()
            
    except pymysql.Error as e:
        logger.error(f"Erreur MySQL création tâche: {e}")
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    except Exception as e:
        logger.error(f"Erreur création tâche WO {wo_id}: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@api_tasks_bp.route('/work_orders/<int:wo_id>/tasks/<int:task_id>/assign', methods=['POST'])
@require_auth
def assign_task(wo_id, task_id):
    """Assigner une tâche à un technicien"""
    try:
        # Vérification accès au Work Order
        has_access, wo_data = check_work_order_access(wo_id, required_role='supervisor')
        if not has_access:
            return jsonify({'success': False, 'message': wo_data.get('error', 'Access denied')}), 403
        
        # Récupération des données
        data = request.get_json(force=True)
        technician_id = data.get('technician_id')
        
        if not technician_id:
            return jsonify({'success': False, 'message': 'technician_id is required'}), 400
        
        # Validation avec AI Guards
        validation = ai_guards.can_assign_task(task_id, technician_id)
        if not validation.is_valid:
            return jsonify({'success': False, 'message': validation.message}), 400
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Vérifier que la tâche appartient au WO
                cursor.execute("""
                    SELECT * FROM work_order_tasks 
                    WHERE id = %s AND work_order_id = %s
                """, (task_id, wo_id))
                
                task = cursor.fetchone()
                if not task:
                    return jsonify({'success': False, 'message': 'Task not found in this work order'}), 404
                
                # Assignation de la tâche
                cursor.execute("""
                    UPDATE work_order_tasks 
                    SET technician_id = %s, status = 'assigned', updated_at = NOW()
                    WHERE id = %s
                """, (technician_id, task_id))
                
                # Récupérer le nom du technicien
                cursor.execute("""
                    SELECT name FROM users WHERE id = %s
                """, (technician_id,))
                technician = cursor.fetchone()
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': f'Tâche assignée à {technician["name"] if technician else "Technicien"}',
                    'task_id': task_id,
                    'technician_id': technician_id,
                    'technician_name': technician["name"] if technician else None
                })
                
        except pymysql.Error as e:
            conn.rollback()
            logger.error(f"Erreur assignation tâche {task_id}: {e}")
            return jsonify({'success': False, 'message': 'Database error'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Erreur assignation tâche {task_id}: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@api_tasks_bp.route('/work_orders/<int:wo_id>/tasks/<int:task_id>/status', methods=['POST'])
@require_auth
def update_task_status(wo_id, task_id):
    """Mettre à jour le statut d'une tâche"""
    try:
        # Vérification accès au Work Order
        has_access, wo_data = check_work_order_access(wo_id)
        if not has_access:
            return jsonify({'success': False, 'message': wo_data.get('error', 'Access denied')}), 403
        
        # Récupération des données
        data = request.get_json(force=True)
        new_status = data.get('status')
        
        valid_statuses = ['pending', 'assigned', 'in_progress', 'done', 'cancelled']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Vérifier que la tâche appartient au WO
                cursor.execute("""
                    SELECT * FROM work_order_tasks 
                    WHERE id = %s AND work_order_id = %s
                """, (task_id, wo_id))
                
                task = cursor.fetchone()
                if not task:
                    return jsonify({'success': False, 'message': 'Task not found in this work order'}), 404
                
                # Préparer les champs à mettre à jour
                update_fields = {
                    'status': new_status,
                    'updated_at': datetime.now()
                }
                
                # Gestion des timestamps selon le statut
                if new_status == 'in_progress' and not task.get('started_at'):
                    update_fields['started_at'] = datetime.now()
                elif new_status == 'done' and not task.get('completed_at'):
                    update_fields['completed_at'] = datetime.now()
                elif new_status == 'cancelled':
                    update_fields['completed_at'] = datetime.now()
                
                # Mise à jour de la tâche
                cursor.execute("""
                    UPDATE work_order_tasks 
                    SET status = %(status)s, updated_at = %(updated_at)s,
                        started_at = COALESCE(%(started_at)s, started_at),
                        completed_at = COALESCE(%(completed_at)s, completed_at)
                    WHERE id = %(task_id)s
                """, {
                    **update_fields,
                    'started_at': update_fields.get('started_at'),
                    'completed_at': update_fields.get('completed_at'),
                    'task_id': task_id
                })
                
                # Mise à jour automatique du statut WO si toutes les tâches sont terminées
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_tasks,
                        COUNT(CASE WHEN status = 'done' THEN 1 END) as completed_tasks
                    FROM work_order_tasks
                    WHERE work_order_id = %s
                """, (wo_id,))
                
                task_stats = cursor.fetchone()
                
                if task_stats['total_tasks'] > 0 and task_stats['completed_tasks'] == task_stats['total_tasks']:
                    cursor.execute("""
                        UPDATE work_orders SET status = 'completed', updated_at = NOW()
                        WHERE id = %s
                    """, (wo_id,))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': f'Statut mis à jour: {new_status}',
                    'task_id': task_id,
                    'new_status': new_status,
                    'timestamps': {
                        'started_at': update_fields.get('started_at').isoformat() if update_fields.get('started_at') else None,
                        'completed_at': update_fields.get('completed_at').isoformat() if update_fields.get('completed_at') else None
                    }
                })
                
        except pymysql.Error as e:
            conn.rollback()
            logger.error(f"Erreur mise à jour statut tâche {task_id}: {e}")
            return jsonify({'success': False, 'message': 'Database error'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Erreur mise à jour statut tâche {task_id}: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@api_tasks_bp.route('/work_orders/<int:wo_id>/tasks/<int:task_id>/start_intervention', methods=['POST'])
@require_auth
def start_intervention(wo_id, task_id):
    """
    Démarrer une intervention pour une tâche spécifique
    Crée la relation 1-1 intervention ↔ tâche
    """
    try:
        # Vérification accès au Work Order
        has_access, wo_data = check_work_order_access(wo_id)
        if not has_access:
            return jsonify({'success': False, 'message': wo_data.get('error', 'Access denied')}), 403
        
        # Récupération des données
        data = request.get_json(force=True) if request.get_json() else {}
        technician_id = data.get('technician_id', session.get('user_id'))
        
        # Validation avec AI Guards
        validation = ai_guards.can_start_intervention(wo_id, task_id, technician_id)
        if not validation.is_valid:
            return jsonify({'success': False, 'message': validation.message}), 400
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Vérifier que la tâche appartient au WO et récupérer ses infos
                cursor.execute("""
                    SELECT * FROM work_order_tasks 
                    WHERE id = %s AND work_order_id = %s
                """, (task_id, wo_id))
                
                task = cursor.fetchone()
                if not task:
                    return jsonify({'success': False, 'message': 'Task not found in this work order'}), 404
                
                # Vérifier qu'aucune intervention n'existe déjà
                cursor.execute("""
                    SELECT id FROM interventions WHERE task_id = %s
                """, (task_id,))
                
                existing_intervention = cursor.fetchone()
                if existing_intervention:
                    return jsonify({
                        'success': False, 
                        'message': 'Intervention already exists for this task',
                        'intervention_id': existing_intervention['id']
                    }), 409
                
                # Créer l'intervention
                cursor.execute("""
                    INSERT INTO interventions 
                    (work_order_id, task_id, technician_id, started_at)
                    VALUES (%s, %s, %s, NOW())
                """, (wo_id, task_id, technician_id))
                
                intervention_id = cursor.lastrowid
                
                # Mettre à jour le statut de la tâche
                cursor.execute("""
                    UPDATE work_order_tasks 
                    SET status = 'in_progress', started_at = NOW(), updated_at = NOW()
                    WHERE id = %s
                """, (task_id,))
                
                # Récupérer les recommandations IA
                recommendations = ai_guards.get_intervention_recommendations(task_id)
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Intervention démarrée avec succès',
                    'intervention_id': intervention_id,
                    'task_id': task_id,
                    'technician_id': technician_id,
                    'ai_recommendations': recommendations
                }), 201
                
        except pymysql.IntegrityError as e:
            conn.rollback()
            logger.error(f"Erreur intégrité démarrage intervention: {e}")
            return jsonify({'success': False, 'message': 'Intervention already exists or constraint violation'}), 409
        except pymysql.Error as e:
            conn.rollback()
            logger.error(f"Erreur DB démarrage intervention: {e}")
            return jsonify({'success': False, 'message': 'Database error'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Erreur démarrage intervention WO {wo_id}, task {task_id}: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@api_tasks_bp.route('/work_orders/<int:wo_id>/tasks', methods=['GET'])
@require_auth
def list_tasks(wo_id):
    """Lister les tâches d'un Work Order"""
    try:
        # Vérification accès au Work Order
        has_access, wo_data = check_work_order_access(wo_id)
        if not has_access:
            return jsonify({'success': False, 'message': wo_data.get('error', 'Access denied')}), 403
        
        # Récupération des paramètres de filtrage
        status_filter = request.args.get('status')
        technician_filter = request.args.get('technician_id')
        source_filter = request.args.get('task_source')
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Construction de la requête avec filtres
                where_conditions = ["wot.work_order_id = %s"]
                params = [wo_id]
                
                if status_filter:
                    where_conditions.append("wot.status = %s")
                    params.append(status_filter)
                
                if technician_filter:
                    where_conditions.append("wot.technician_id = %s")
                    params.append(technician_filter)
                
                if source_filter:
                    where_conditions.append("wot.task_source = %s")
                    params.append(source_filter)
                
                where_clause = " AND ".join(where_conditions)
                
                cursor.execute(f"""
                    SELECT 
                        wot.*,
                        u.name as technician_name,
                        i.id as intervention_id,
                        i.started_at as intervention_started,
                        i.ended_at as intervention_ended,
                        i.result_status as intervention_result,
                        COUNT(DISTINCT in_.id) as notes_count,
                        COUNT(DISTINCT im.id) as media_count
                    FROM work_order_tasks wot
                    LEFT JOIN users u ON wot.technician_id = u.id
                    LEFT JOIN interventions i ON wot.id = i.task_id
                    LEFT JOIN intervention_notes in_ ON i.id = in_.intervention_id
                    LEFT JOIN intervention_media im ON i.id = im.intervention_id
                    WHERE {where_clause}
                    GROUP BY wot.id
                    ORDER BY wot.priority DESC, wot.created_at ASC
                """, params)
                
                tasks = cursor.fetchall()
                
                # Formatage des données
                formatted_tasks = []
                for task in tasks:
                    formatted_task = dict(task)
                    
                    # Conversion des timestamps
                    for field in ['created_at', 'updated_at', 'scheduled_start', 'scheduled_end', 'started_at', 'completed_at']:
                        if formatted_task.get(field):
                            formatted_task[field] = formatted_task[field].isoformat()
                    
                    # Ajout des métadonnées
                    formatted_task['has_intervention'] = bool(task['intervention_id'])
                    formatted_task['is_completed'] = task['status'] == 'done'
                    formatted_task['has_notes'] = task['notes_count'] > 0
                    formatted_task['has_media'] = task['media_count'] > 0
                    
                    formatted_tasks.append(formatted_task)
                
                return jsonify({
                    'success': True,
                    'tasks': formatted_tasks,
                    'total_count': len(formatted_tasks),
                    'work_order_id': wo_id
                })
                
        except pymysql.Error as e:
            logger.error(f"Erreur récupération tâches WO {wo_id}: {e}")
            return jsonify({'success': False, 'message': 'Database error'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Erreur listing tâches WO {wo_id}: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@api_tasks_bp.route('/work_orders/<int:wo_id>/close', methods=['POST'])
@require_auth
def close_work_order(wo_id):
    """
    Fermer un Work Order avec validation IA complète
    Guards IA empêchent la fermeture si conditions non remplies
    """
    try:
        # Vérification accès au Work Order
        has_access, wo_data = check_work_order_access(wo_id, required_role='supervisor')
        if not has_access:
            return jsonify({'success': False, 'message': wo_data.get('error', 'Access denied')}), 403
        
        # Validation avec AI Guards
        validation = ai_guards.can_close_work_order(wo_id)
        if not validation.is_valid:
            return jsonify({
                'success': False, 
                'message': validation.message,
                'details': validation.details
            }), 400
        
        # Récupération des données optionnelles
        data = request.get_json(force=True) if request.get_json() else {}
        closing_notes = data.get('closing_notes', '')
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Fermeture du Work Order
                cursor.execute("""
                    UPDATE work_orders 
                    SET status = 'closed', 
                        closed_at = NOW(),
                        closing_notes = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (closing_notes, wo_id))
                
                # Historisation
                cursor.execute("""
                    INSERT INTO work_order_status_history 
                    (work_order_id, old_status, new_status, changed_by_user_id)
                    VALUES (%s, %s, 'closed', %s)
                """, (wo_id, wo_data['status'], session.get('user_id')))
                
                # Fermeture automatique des interventions non terminées
                cursor.execute("""
                    UPDATE interventions i
                    JOIN work_order_tasks wot ON i.task_id = wot.id
                    SET i.ended_at = NOW(), i.result_status = 'ok'
                    WHERE wot.work_order_id = %s AND i.ended_at IS NULL
                """, (wo_id,))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Work Order fermé avec succès',
                    'work_order_id': wo_id,
                    'closed_at': datetime.now().isoformat(),
                    'validation_details': validation.details
                })
                
        except pymysql.Error as e:
            conn.rollback()
            logger.error(f"Erreur fermeture WO {wo_id}: {e}")
            return jsonify({'success': False, 'message': 'Database error'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Erreur fermeture WO {wo_id}: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

# ========================================
# ROUTES INTERDITES (RETOURNENT 403)
# ========================================

@api_tasks_bp.route('/tasks/create', methods=['POST'])
@api_tasks_bp.route('/tasks', methods=['POST'])
def forbidden_global_task_creation():
    """
    Route volontairement interdite - Empêche création de tâches orphelines
    Sprint 2: AUCUN endpoint global pour créer des tâches
    """
    return jsonify({
        'success': False,
        'message': 'Forbidden: Tasks must be created under a Work Order. Use POST /work_orders/<id>/tasks instead.',
        'error_code': 'ORPHAN_TASK_PREVENTION'
    }), 403

@api_tasks_bp.route('/tasks/<int:task_id>', methods=['PUT', 'PATCH', 'DELETE'])
def forbidden_global_task_operations(task_id):
    """Routes globales interdites pour les tâches"""
    return jsonify({
        'success': False,
        'message': 'Forbidden: Task operations must be performed through Work Order endpoints.',
        'error_code': 'GLOBAL_TASK_OPERATION_FORBIDDEN'
    }), 403
