"""
Routes API sécurisées Sprint 2 - Interventions
Gestion des interventions avec validation IA et upload médias
"""
import os
import pymysql
import logging
import uuid
from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from services.ai_guards import ai_guards, ValidationResult

logger = logging.getLogger(__name__)

# Blueprint pour les routes API des interventions
api_interventions_bp = Blueprint('api_interventions', __name__)

# Configuration upload
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads', 'interventions')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'mp3', 'wav', 'pdf', 'doc', 'docx'}

# Créer le dossier d'upload s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

def check_intervention_access(intervention_id: int) -> tuple[bool, dict]:
    """Vérifier l'accès à une intervention selon le rôle"""
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    i.*,
                    wot.title as task_title,
                    wot.work_order_id,
                    wo.claim_number as wo_title,
                    wo.assigned_technician_id as wo_technician_id,
                    u.name as technician_name
                FROM interventions i
                JOIN work_order_tasks wot ON i.task_id = wot.id
                JOIN work_orders wo ON i.work_order_id = wo.id
                LEFT JOIN users u ON i.technician_id = u.id
                WHERE i.id = %s
            """, (intervention_id,))
            
            intervention = cursor.fetchone()
            if not intervention:
                return False, {'error': 'Intervention not found'}
            
            # Vérification des permissions selon le rôle
            if user_role == 'technician':
                # Technicien : accès seulement à ses interventions
                if intervention['technician_id'] != user_id and intervention['wo_technician_id'] != user_id:
                    return False, {'error': 'Access denied: not your intervention'}
            elif user_role == 'supervisor':
                # Superviseur : accès complet
                pass
            elif user_role == 'admin':
                # Admin : accès complet
                pass
            else:
                return False, {'error': 'Invalid role'}
            
            return True, intervention
    finally:
        conn.close()

def allowed_file(filename: str) -> bool:
    """Vérifier si l'extension de fichier est autorisée"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_media_type(filename: str) -> str:
    """Déterminer le type de média selon l'extension"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if ext in ['png', 'jpg', 'jpeg', 'gif']:
        return 'photo'
    elif ext in ['mp4', 'mov']:
        return 'video'
    elif ext in ['mp3', 'wav']:
        return 'audio'
    elif ext in ['pdf', 'doc', 'docx']:
        return 'doc'
    else:
        return 'other'

def generate_secure_filename(original_filename: str, intervention_id: int) -> str:
    """Générer un nom de fichier sécurisé et unique"""
    # Nettoyer le nom original
    clean_name = secure_filename(original_filename)
    
    # Générer un UUID pour éviter les conflits
    unique_id = str(uuid.uuid4())[:8]
    
    # Garder l'extension originale
    ext = clean_name.rsplit('.', 1)[1] if '.' in clean_name else 'bin'
    
    # Format: intervention_ID_UUID_original.ext
    return f"intervention_{intervention_id}_{unique_id}_{clean_name[:50]}.{ext}"

# ========================================
# ROUTES API INTERVENTIONS
# ========================================

@api_interventions_bp.route('/interventions', methods=['GET'])
@require_auth
def list_interventions():
    """
    Lister les interventions selon le rôle utilisateur
    Technicien: seulement ses interventions
    Superviseur/Admin: toutes les interventions
    """
    try:
        user_role = session.get('user_role')
        user_id = session.get('user_id')
        
        # Filtres optionnels
        status_filter = request.args.get('status')
        technician_filter = request.args.get('technician_id')
        wo_filter = request.args.get('work_order_id')
        limit = min(int(request.args.get('limit', 50)), 100)
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Construction de la requête selon le rôle
                where_conditions = []
                params = []
                
                # Filtre par rôle
                if user_role == 'technician':
                    where_conditions.append("(i.technician_id = %s OR wo.assigned_technician_id = %s)")
                    params.extend([user_id, user_id])
                
                # Filtres additionnels
                if status_filter:
                    where_conditions.append("i.result_status = %s")
                    params.append(status_filter)
                
                if technician_filter:
                    where_conditions.append("i.technician_id = %s")
                    params.append(technician_filter)
                
                if wo_filter:
                    where_conditions.append("i.work_order_id = %s")
                    params.append(wo_filter)
                
                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                
                cursor.execute(f"""
                    SELECT 
                        i.*,
                        wot.title as task_title,
                        wot.task_source,
                        wot.priority as task_priority,
                        wo.claim_number as wo_title,
                        wo.status as wo_status,
                        u.name as technician_name,
                        c.name as customer_name,
                        COUNT(DISTINCT in_.id) as notes_count,
                        COUNT(DISTINCT im.id) as media_count,
                        TIMESTAMPDIFF(MINUTE, i.started_at, COALESCE(i.ended_at, NOW())) as duration_minutes
                    FROM interventions i
                    JOIN work_order_tasks wot ON i.task_id = wot.id
                    JOIN work_orders wo ON i.work_order_id = wo.id
                    LEFT JOIN users u ON i.technician_id = u.id
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    LEFT JOIN intervention_notes in_ ON i.id = in_.intervention_id
                    LEFT JOIN intervention_media im ON i.id = im.intervention_id
                    {where_clause}
                    GROUP BY i.id
                    ORDER BY i.started_at DESC
                    LIMIT %s
                """, params + [limit])
                
                interventions = cursor.fetchall()
                
                # Formatage des données
                formatted_interventions = []
                for intervention in interventions:
                    formatted_intervention = dict(intervention)
                    
                    # Conversion des timestamps
                    for field in ['started_at', 'ended_at', 'created_at']:
                        if formatted_intervention.get(field):
                            formatted_intervention[field] = formatted_intervention[field].isoformat()
                    
                    # Ajout des métadonnées
                    formatted_intervention['is_active'] = not bool(intervention['ended_at'])
                    formatted_intervention['has_notes'] = intervention['notes_count'] > 0
                    formatted_intervention['has_media'] = intervention['media_count'] > 0
                    formatted_intervention['duration_hours'] = round(intervention['duration_minutes'] / 60, 2) if intervention['duration_minutes'] else 0
                    
                    formatted_interventions.append(formatted_intervention)
                
                return jsonify({
                    'success': True,
                    'interventions': formatted_interventions,
                    'total_count': len(formatted_interventions),
                    'filters_applied': {
                        'role_filter': user_role,
                        'status_filter': status_filter,
                        'technician_filter': technician_filter,
                        'wo_filter': wo_filter
                    }
                })
                
        except pymysql.Error as e:
            logger.error(f"Erreur récupération interventions: {e}")
            return jsonify({'success': False, 'message': 'Database error'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Erreur listing interventions: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@api_interventions_bp.route('/interventions/<int:intervention_id>/details', methods=['GET'])
@require_auth
def get_intervention_details(intervention_id):
    """Récupérer les détails complets d'une intervention"""
    try:
        # Vérification de l'accès
        has_access, intervention_data = check_intervention_access(intervention_id)
        if not has_access:
            return jsonify({'success': False, 'message': intervention_data.get('error', 'Access denied')}), 403
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Récupération des notes
                cursor.execute("""
                    SELECT in_.*, u.name as author_name
                    FROM intervention_notes in_
                    JOIN users u ON in_.author_user_id = u.id
                    WHERE in_.intervention_id = %s
                    ORDER BY in_.created_at DESC
                """, (intervention_id,))
                notes = cursor.fetchall()
                
                # Récupération des médias
                cursor.execute("""
                    SELECT * FROM intervention_media
                    WHERE intervention_id = %s
                    ORDER BY created_at DESC
                """, (intervention_id,))
                media = cursor.fetchall()
                
                # Formatage des données
                formatted_intervention = dict(intervention_data)
                
                # Conversion des timestamps
                for field in ['started_at', 'ended_at', 'created_at']:
                    if formatted_intervention.get(field):
                        formatted_intervention[field] = formatted_intervention[field].isoformat()
                
                # Ajout des notes et médias
                formatted_intervention['notes'] = [
                    {
                        **dict(note),
                        'created_at': note['created_at'].isoformat()
                    } for note in notes
                ]
                
                formatted_intervention['media'] = [
                    {
                        **dict(medium),
                        'created_at': medium['created_at'].isoformat()
                    } for medium in media
                ]
                
                # Calcul de la durée
                if formatted_intervention.get('started_at') and formatted_intervention.get('ended_at'):
                    start = datetime.fromisoformat(formatted_intervention['started_at'])
                    end = datetime.fromisoformat(formatted_intervention['ended_at'])
                    duration = end - start
                    formatted_intervention['duration_minutes'] = int(duration.total_seconds() / 60)
                    formatted_intervention['duration_hours'] = round(duration.total_seconds() / 3600, 2)
                
                return jsonify({
                    'success': True,
                    'intervention': formatted_intervention
                })
                
        except pymysql.Error as e:
            logger.error(f"Erreur récupération détails intervention {intervention_id}: {e}")
            return jsonify({'success': False, 'message': 'Database error'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Erreur détails intervention {intervention_id}: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@api_interventions_bp.route('/interventions/<int:intervention_id>/add_note', methods=['POST'])
@require_auth
def add_note(intervention_id):
    """Ajouter une note à une intervention"""
    try:
        # Vérification de l'accès
        has_access, intervention_data = check_intervention_access(intervention_id)
        if not has_access:
            return jsonify({'success': False, 'message': intervention_data.get('error', 'Access denied')}), 403
        
        # Récupération des données
        data = request.get_json(force=True)
        note_content = data.get('note', '').strip()
        
        if not note_content:
            return jsonify({'success': False, 'message': 'Note content is required'}), 400
        
        if len(note_content) < 3:
            return jsonify({'success': False, 'message': 'Note must be at least 3 characters long'}), 400
        
        if len(note_content) > 5000:
            return jsonify({'success': False, 'message': 'Note must not exceed 5000 characters'}), 400
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Insertion de la note
                cursor.execute("""
                    INSERT INTO intervention_notes 
                    (intervention_id, author_user_id, note)
                    VALUES (%s, %s, %s)
                """, (intervention_id, session.get('user_id'), note_content))
                
                note_id = cursor.lastrowid
                
                # Mise à jour du timestamp de l'intervention
                cursor.execute("""
                    UPDATE interventions SET updated_at = NOW()
                    WHERE id = %s
                """, (intervention_id,))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Note ajoutée avec succès',
                    'note_id': note_id,
                    'intervention_id': intervention_id,
                    'note_content': note_content[:100] + ('...' if len(note_content) > 100 else '')
                }), 201
                
        except pymysql.Error as e:
            conn.rollback()
            logger.error(f"Erreur ajout note intervention {intervention_id}: {e}")
            return jsonify({'success': False, 'message': 'Database error'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Erreur ajout note intervention {intervention_id}: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@api_interventions_bp.route('/interventions/<int:intervention_id>/upload_media', methods=['POST'])
@require_auth
def upload_media(intervention_id):
    """
    Upload de médias (photos, vidéos, documents) pour une intervention
    Gestion sécurisée des fichiers avec métadonnées complètes
    """
    try:
        # Vérification de l'accès
        has_access, intervention_data = check_intervention_access(intervention_id)
        if not has_access:
            return jsonify({'success': False, 'message': intervention_data.get('error', 'Access denied')}), 403
        
        # Vérification des fichiers
        if 'files' not in request.files:
            return jsonify({'success': False, 'message': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'message': 'No files selected'}), 400
        
        uploaded_files = []
        errors = []
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                for file in files:
                    if file and file.filename:
                        try:
                            # Validation du fichier
                            if not allowed_file(file.filename):
                                errors.append(f"File type not allowed: {file.filename}")
                                continue
                            
                            # Vérification de la taille
                            file.seek(0, 2)  # Aller à la fin du fichier
                            file_size = file.tell()
                            file.seek(0)  # Retourner au début
                            
                            if file_size > MAX_CONTENT_LENGTH:
                                errors.append(f"File too large: {file.filename} ({file_size} bytes)")
                                continue
                            
                            # Génération du nom de fichier sécurisé
                            secure_name = generate_secure_filename(file.filename, intervention_id)
                            file_path = os.path.join(UPLOAD_FOLDER, secure_name)
                            
                            # Sauvegarde du fichier
                            file.save(file_path)
                            
                            # Détermination du type de média
                            media_type = get_media_type(file.filename)
                            
                            # Insertion en base de données
                            cursor.execute("""
                                INSERT INTO intervention_media 
                                (intervention_id, file_path, media_type, original_filename, file_size)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (intervention_id, secure_name, media_type, file.filename, file_size))
                            
                            media_id = cursor.lastrowid
                            
                            uploaded_files.append({
                                'media_id': media_id,
                                'original_filename': file.filename,
                                'secure_filename': secure_name,
                                'media_type': media_type,
                                'file_size': file_size
                            })
                            
                        except Exception as e:
                            errors.append(f"Error processing {file.filename}: {str(e)}")
                            logger.error(f"Erreur upload fichier {file.filename}: {e}")
                
                if uploaded_files:
                    # Mise à jour du timestamp de l'intervention
                    cursor.execute("""
                        UPDATE interventions SET updated_at = NOW()
                        WHERE id = %s
                    """, (intervention_id,))
                    
                    conn.commit()
                
                return jsonify({
                    'success': len(uploaded_files) > 0,
                    'message': f'{len(uploaded_files)} file(s) uploaded successfully',
                    'uploaded_files': uploaded_files,
                    'errors': errors,
                    'intervention_id': intervention_id
                }), 201 if uploaded_files else 400
                
        except pymysql.Error as e:
            conn.rollback()
            logger.error(f"Erreur DB upload média intervention {intervention_id}: {e}")
            return jsonify({'success': False, 'message': 'Database error'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Erreur upload média intervention {intervention_id}: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@api_interventions_bp.route('/interventions/<int:intervention_id>/quick_actions', methods=['POST'])
@require_auth
def quick_actions(intervention_id):
    """
    Actions rapides pour les interventions
    - start: Démarrer (si pas encore démarré)
    - stop: Terminer l'intervention  
    - pause: Mettre en pause
    - request_parts: Demander des pièces
    """
    try:
        # Vérification de l'accès
        has_access, intervention_data = check_intervention_access(intervention_id)
        if not has_access:
            return jsonify({'success': False, 'message': intervention_data.get('error', 'Access denied')}), 403
        
        # Récupération de l'action
        data = request.get_json(force=True)
        action = data.get('action')
        
        valid_actions = ['start', 'stop', 'pause', 'request_parts']
        if action not in valid_actions:
            return jsonify({'success': False, 'message': f'Invalid action. Must be one of: {", ".join(valid_actions)}'}), 400
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Récupération des informations actuelles de l'intervention
                cursor.execute("""
                    SELECT i.*, wot.status as task_status
                    FROM interventions i
                    JOIN work_order_tasks wot ON i.task_id = wot.id
                    WHERE i.id = %s
                """, (intervention_id,))
                
                intervention = cursor.fetchone()
                if not intervention:
                    return jsonify({'success': False, 'message': 'Intervention not found'}), 404
                
                response_data = {
                    'success': True,
                    'intervention_id': intervention_id,
                    'action': action
                }
                
                # Traitement selon l'action
                if action == 'start':
                    if intervention['started_at']:
                        return jsonify({'success': False, 'message': 'Intervention already started'}), 400
                    
                    cursor.execute("""
                        UPDATE interventions SET started_at = NOW()
                        WHERE id = %s
                    """, (intervention_id,))
                    
                    cursor.execute("""
                        UPDATE work_order_tasks SET status = 'in_progress', started_at = NOW()
                        WHERE id = %s
                    """, (intervention['task_id']))
                    
                    response_data['message'] = 'Intervention démarrée'
                    response_data['started_at'] = datetime.now().isoformat()
                
                elif action == 'stop':
                    if intervention['ended_at']:
                        return jsonify({'success': False, 'message': 'Intervention already stopped'}), 400
                    
                    if not intervention['started_at']:
                        return jsonify({'success': False, 'message': 'Cannot stop intervention that was never started'}), 400
                    
                    # Récupération du résultat optionnel
                    result_status = data.get('result_status', 'ok')
                    summary = data.get('summary', '')
                    
                    cursor.execute("""
                        UPDATE interventions 
                        SET ended_at = NOW(), result_status = %s, summary = %s
                        WHERE id = %s
                    """, (result_status, summary, intervention_id))
                    
                    cursor.execute("""
                        UPDATE work_order_tasks SET status = 'done', completed_at = NOW()
                        WHERE id = %s
                    """, (intervention['task_id']))
                    
                    response_data['message'] = 'Intervention terminée'
                    response_data['ended_at'] = datetime.now().isoformat()
                    response_data['result_status'] = result_status
                
                elif action == 'pause':
                    # Pour l'instant, on ajoute juste une note
                    cursor.execute("""
                        INSERT INTO intervention_notes 
                        (intervention_id, author_user_id, note)
                        VALUES (%s, %s, 'Intervention mise en pause')
                    """, (intervention_id, session.get('user_id')))
                    
                    response_data['message'] = 'Intervention mise en pause'
                
                elif action == 'request_parts':
                    parts_needed = data.get('parts_needed', [])
                    urgent = data.get('urgent', False)
                    
                    # Ajouter une note avec la demande de pièces
                    note_content = f"DEMANDE DE PIÈCES {'(URGENT)' if urgent else ''}: {', '.join(parts_needed) if parts_needed else 'Voir détails'}"
                    
                    cursor.execute("""
                        INSERT INTO intervention_notes 
                        (intervention_id, author_user_id, note)
                        VALUES (%s, %s, %s)
                    """, (intervention_id, session.get('user_id'), note_content))
                    
                    response_data['message'] = 'Demande de pièces enregistrée'
                    response_data['parts_requested'] = parts_needed
                
                conn.commit()
                return jsonify(response_data)
                
        except pymysql.Error as e:
            conn.rollback()
            logger.error(f"Erreur action rapide intervention {intervention_id}: {e}")
            return jsonify({'success': False, 'message': 'Database error'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Erreur action rapide intervention {intervention_id}: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@api_interventions_bp.route('/interventions/<int:intervention_id>/media/<int:media_id>', methods=['DELETE'])
@require_auth
def delete_media(intervention_id, media_id):
    """Supprimer un média d'intervention"""
    try:
        # Vérification de l'accès
        has_access, intervention_data = check_intervention_access(intervention_id)
        if not has_access:
            return jsonify({'success': False, 'message': intervention_data.get('error', 'Access denied')}), 403
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Vérifier que le média appartient à l'intervention
                cursor.execute("""
                    SELECT file_path FROM intervention_media
                    WHERE id = %s AND intervention_id = %s
                """, (media_id, intervention_id))
                
                media = cursor.fetchone()
                if not media:
                    return jsonify({'success': False, 'message': 'Media not found'}), 404
                
                # Suppression du fichier physique
                file_path = os.path.join(UPLOAD_FOLDER, media['file_path'])
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        logger.warning(f"Impossible de supprimer le fichier {file_path}: {e}")
                
                # Suppression de l'enregistrement en base
                cursor.execute("""
                    DELETE FROM intervention_media
                    WHERE id = %s AND intervention_id = %s
                """, (media_id, intervention_id))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Média supprimé avec succès',
                    'media_id': media_id,
                    'intervention_id': intervention_id
                })
                
        except pymysql.Error as e:
            conn.rollback()
            logger.error(f"Erreur suppression média {media_id}: {e}")
            return jsonify({'success': False, 'message': 'Database error'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Erreur suppression média {media_id}: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@api_interventions_bp.route('/interventions/suggestions/<int:work_order_id>', methods=['GET'])
@require_auth
def get_intervention_suggestions(work_order_id):
    """Suggestions d'intervention basées sur l'IA pour un work order"""
    try:
        section = request.args.get('section')
        suggestion_type = request.args.get('type', 'general')
        
        # Utilisation du service AI Guards
        if suggestion_type == 'parts':
            # Récupérer une tâche du WO pour les suggestions de pièces
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id FROM work_order_tasks 
                        WHERE work_order_id = %s 
                        LIMIT 1
                    """, (work_order_id,))
                    
                    task = cursor.fetchone()
                    if task:
                        suggestions = ai_guards.suggest_parts_for_task(task['id'])
                    else:
                        suggestions = []
            finally:
                conn.close()
        else:
            # Suggestions générales d'intervention
            suggestions = [
                {
                    'title': 'Diagnostic initial',
                    'items': [
                        'Vérifier l\'état général du véhicule',
                        'Documenter les symptômes observés',
                        'Prendre des photos de référence'
                    ]
                },
                {
                    'title': 'Contrôles de sécurité',
                    'items': [
                        'Tester tous les systèmes de sécurité',
                        'Vérifier les niveaux de fluides',
                        'Contrôler l\'usure des éléments critiques'
                    ]
                }
            ]
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'work_order_id': work_order_id
        })
        
    except Exception as e:
        logger.error(f"Erreur suggestions intervention WO {work_order_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de la récupération des suggestions'
        }), 500

@api_interventions_bp.route('/interventions/suggestions/search', methods=['POST'])
@require_auth
def search_intervention_suggestions():
    """Recherche de suggestions d'intervention"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Requête de recherche requise'
            }), 400
        
        # Simulation de recherche dans une base de connaissances
        # En production, intégrer avec Elasticsearch ou service similaire
        mock_results = [
            {
                'title': f'Procédure pour: {query}',
                'description': f'Guide détaillé pour traiter les cas liés à "{query}"',
                'relevance': 0.9,
                'category': 'Diagnostic'
            },
            {
                'title': f'Problèmes fréquents: {query}',
                'description': f'Solutions courantes pour les problèmes de type "{query}"',
                'relevance': 0.8,
                'category': 'Réparation'
            }
        ]
        
        return jsonify({
            'success': True,
            'results': mock_results,
            'query': query,
            'total': len(mock_results)
        })
        
    except Exception as e:
        logger.error(f"Erreur recherche suggestions: {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de la recherche'
        }), 500

@api_interventions_bp.route('/interventions/ai/chat/<int:work_order_id>', methods=['POST'])
@require_auth
def ai_chat_intervention(work_order_id):
    """Chat IA spécifique à une intervention"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({
                'success': False,
                'message': 'Message requis'
            }), 400
        
        # Récupérer le contexte de l'intervention
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT wo.*, c.name as customer_name
                    FROM work_orders wo
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    WHERE wo.id = %s
                """, (work_order_id,))
                
                work_order = cursor.fetchone()
                
                if not work_order:
                    return jsonify({
                        'success': False,
                        'message': 'Bon de travail non trouvé'
                    }), 404
        finally:
            conn.close()
        
        # Simulation de réponse IA contextuelle
        ai_response = {
            'success': True,
            'response': f"Pour l'intervention sur le véhicule de {work_order.get('customer_name', 'Client')} (WO #{work_order['claim_number']}): {message}. En production, cette réponse serait générée par un modèle IA contextualisé.",
            'confidence': 0.85,
            'context': {
                'work_order_id': work_order_id,
                'claim_number': work_order['claim_number'],
                'customer': work_order.get('customer_name', 'Client')
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(ai_response)
        
    except Exception as e:
        logger.error(f"Erreur chat IA intervention WO {work_order_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors du traitement du chat IA'
        }), 500
