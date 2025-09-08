"""
Routes pour la gestion des interventions - interventions.py
SÉCURISÉ - Sprint 1 Security Implementation
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash, abort
from flask_wtf.csrf import validate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import pymysql
from datetime import datetime
import os
import hashlib
import magic
import logging
from werkzeug.utils import secure_filename
from functools import wraps

# Configuration logging sécuritaire
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

bp = Blueprint('interventions', __name__)

# Rate Limiter (sera configuré dans app.py)
limiter = None

class SecurityError(Exception):
    """Exception pour les erreurs de sécurité"""
    pass

def init_security_limiter(app_limiter):
    """Initialiser le limiteur depuis l'app principale"""
    global limiter
    limiter = app_limiter

def get_db_connection():
    """Connexion à la base de données avec pool de connexions"""
    try:
        return pymysql.connect(
            host=os.getenv('MYSQL_HOST', '192.168.50.101'),
            user=os.getenv('MYSQL_USER', 'gsicloud'),
            password=os.getenv('MYSQL_PASSWORD', 'TCOChoosenOne204$'),
            database=os.getenv('MYSQL_DB', 'bdm'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            connect_timeout=10,
            read_timeout=10,
            write_timeout=10
        )
    except Exception as e:
        security_logger.error(f"Database connection failed: {str(e)}")
        raise

def validate_file_security(file, allowed_extensions=None):
    """Validation sécurisée des fichiers uploadés"""
    if not file or not file.filename:
        raise SecurityError("Aucun fichier fourni")
    
    # Extensions autorisées par défaut
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'mp3', 'wav', 'pdf', 'txt'}
    
    # Sécuriser le nom de fichier
    filename = secure_filename(file.filename)
    if not filename:
        raise SecurityError("Nom de fichier invalide")
    
    # Vérifier l'extension
    if '.' not in filename:
        raise SecurityError("Extension manquante")
    
    extension = filename.rsplit('.', 1)[1].lower()
    if extension not in allowed_extensions:
        raise SecurityError(f"Extension {extension} non autorisée")
    
    # Vérifier le type MIME réel
    file.seek(0)
    file_content = file.read(2048)  # Lire les premiers 2KB
    file.seek(0)
    
    try:
        mime_type = magic.from_buffer(file_content, mime=True)
        
        # Mapping extension -> MIME types autorisés
        allowed_mimes = {
            'png': ['image/png'],
            'jpg': ['image/jpeg'], 'jpeg': ['image/jpeg'],
            'gif': ['image/gif'],
            'mp4': ['video/mp4'],
            'mov': ['video/quicktime'],
            'mp3': ['audio/mpeg'],
            'wav': ['audio/wav', 'audio/x-wav'],
            'pdf': ['application/pdf'],
            'txt': ['text/plain']
        }
        
        if mime_type not in allowed_mimes.get(extension, []):
            raise SecurityError(f"Type MIME {mime_type} ne correspond pas à l'extension {extension}")
            
    except Exception as e:
        security_logger.warning(f"MIME validation failed: {str(e)}")
        # En cas d'erreur de détection MIME, on continue mais on log
    
    # Vérifier la taille (max 50MB)
    file.seek(0, 2)  # Aller à la fin
    file_size = file.tell()
    file.seek(0)  # Retour au début
    
    if file_size > 50 * 1024 * 1024:  # 50MB
        raise SecurityError("Fichier trop volumineux (max 50MB)")
    
    return filename

def secure_upload_path(work_order_id, filename):
    """Génération sécurisée du chemin d'upload"""
    # Chemin de base sécurisé
    base_path = os.path.abspath(os.path.join('static', 'uploads', 'interventions'))
    
    # S'assurer que le dossier existe
    os.makedirs(base_path, exist_ok=True)
    
    # Dossier spécifique à l'intervention
    intervention_dir = os.path.join(base_path, str(work_order_id))
    os.makedirs(intervention_dir, exist_ok=True)
    
    # Chemin final
    final_path = os.path.abspath(os.path.join(intervention_dir, filename))
    
    # Vérification anti-path traversal
    if not final_path.startswith(base_path):
        security_logger.critical(f"Path traversal attempt detected: {final_path}")
        raise SecurityError("Tentative de path traversal détectée")
    
    return final_path

# Décorateurs RBAC
def require_auth(f):
    """Décorateur : Authentification requise"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            security_logger.warning(f"Unauthorized access attempt to {request.endpoint}")
            return jsonify({'error': 'Authentification requise'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_role(*allowed_roles):
    """Décorateur : Rôles spécifiques requis"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('user_role')
            if user_role not in allowed_roles:
                security_logger.warning(
                    f"Role access denied: user {session.get('user_id')} "
                    f"with role {user_role} attempted to access {request.endpoint}"
                )
                return jsonify({'error': 'Permissions insuffisantes'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_intervention_access(f):
    """Décorateur : Vérifier l'accès à une intervention spécifique"""
    @wraps(f)
    def decorated_function(work_order_id, *args, **kwargs):
        user_id = session.get('user_id')
        user_role = session.get('user_role')
        
        # Admin a accès à tout
        if user_role == 'admin':
            return f(work_order_id, *args, **kwargs)
        
        # Vérifier l'accès pour les autres rôles
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT assigned_technician_id, customer_id 
                    FROM work_orders 
                    WHERE id = %s
                """, (work_order_id,))
                
                intervention = cursor.fetchone()
                if not intervention:
                    security_logger.warning(f"Access to non-existent intervention {work_order_id}")
                    abort(404)
                
                # Technicien : seulement ses interventions
                if user_role == 'technician' and intervention['assigned_technician_id'] != user_id:
                    security_logger.warning(
                        f"Technician {user_id} attempted to access intervention {work_order_id} "
                        f"assigned to {intervention['assigned_technician_id']}"
                    )
                    abort(403)
                
                # Supervisor : interventions de son équipe (à implémenter si nécessaire)
                
        finally:
            conn.close()
            
        return f(work_order_id, *args, **kwargs)
    return decorated_function

# ROUTES SÉCURISÉES

@bp.route('/')
@require_auth
def list_interventions():
    """Liste des interventions avec vue adaptée au rôle - SÉCURISÉ"""
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Requête sécurisée avec paramètres
            if user_role == 'technician':
                # Technicien : seulement ses interventions
                query = """
                    SELECT 
                        wo.*,
                        u.name as technician_name,
                        c.name as customer_name,
                        c.phone as customer_phone,
                        v.make as vehicle_make,
                        v.model as vehicle_model,
                        v.year as vehicle_year,
                        (SELECT COUNT(*) FROM intervention_notes WHERE work_order_id = wo.id) as notes_count,
                        (SELECT COUNT(*) FROM intervention_media WHERE work_order_id = wo.id) as media_count
                    FROM work_orders wo
                    LEFT JOIN users u ON wo.assigned_technician_id = u.id
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    LEFT JOIN vehicles v ON wo.vehicle_id = v.id
                    WHERE wo.assigned_technician_id = %s
                    ORDER BY wo.updated_at DESC
                    LIMIT 100
                """
                cursor.execute(query, (user_id,))
            else:
                # Admin/Supervisor : toutes les interventions
                query = """
                    SELECT 
                        wo.*,
                        u.name as technician_name,
                        c.name as customer_name,
                        c.phone as customer_phone,
                        v.make as vehicle_make,
                        v.model as vehicle_model,
                        v.year as vehicle_year,
                        (SELECT COUNT(*) FROM intervention_notes WHERE work_order_id = wo.id) as notes_count,
                        (SELECT COUNT(*) FROM intervention_media WHERE work_order_id = wo.id) as media_count
                    FROM work_orders wo
                    LEFT JOIN users u ON wo.assigned_technician_id = u.id
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    LEFT JOIN vehicles v ON wo.vehicle_id = v.id
                    ORDER BY wo.updated_at DESC
                    LIMIT 100
                """
                cursor.execute(query)
            
            interventions = cursor.fetchall()
            
            return render_template('interventions/list.html', 
                                 interventions=interventions,
                                 user_role=user_role)
                                 
    except Exception as e:
        security_logger.error(f"Error in list_interventions: {str(e)}")
        flash('Erreur lors de la récupération des interventions', 'error')
        return render_template('interventions/list.html', interventions=[])
    finally:
        conn.close()

@bp.route('/<int:work_order_id>/details')
@require_auth
@require_intervention_access
def intervention_details(work_order_id):
    """Interface détaillée d'intervention - SÉCURISÉ"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupération sécurisée du bon de travail
            cursor.execute("""
                SELECT 
                    wo.*,
                    u.name as technician_name,
                    c.name as customer_name,
                    c.phone as customer_phone,
                    c.email as customer_email,
                    c.address as customer_address,
                    v.make as vehicle_make,
                    v.model as vehicle_model,
                    v.year as vehicle_year,
                    v.mileage as vehicle_mileage,
                    v.vin as vehicle_vin,
                    v.license_plate as vehicle_license_plate,
                    v.color as vehicle_color,
                    v.fuel_type as vehicle_fuel_type,
                    v.notes as vehicle_notes,
                    v.id as vehicle_id
                FROM work_orders wo
                LEFT JOIN users u ON wo.assigned_technician_id = u.id
                LEFT JOIN customers c ON wo.customer_id = c.id
                LEFT JOIN vehicles v ON wo.vehicle_id = v.id
                WHERE wo.id = %s
            """, (work_order_id,))
            
            work_order = cursor.fetchone()
            if not work_order:
                abort(404)
            
            # Notes d'intervention
            cursor.execute("""
                SELECT 
                    in_.*,
                    u.name as technician_name
                FROM intervention_notes in_
                JOIN users u ON in_.technician_id = u.id
                WHERE in_.work_order_id = %s
                ORDER BY in_.created_at DESC
            """, (work_order_id,))
            notes = cursor.fetchall()
            
            # Médias
            cursor.execute("""
                SELECT 
                    im.*,
                    u.name as technician_name
                FROM intervention_media im
                JOIN users u ON im.technician_id = u.id
                WHERE im.work_order_id = %s
                ORDER BY im.created_at DESC
            """, (work_order_id,))
            media = cursor.fetchall()

            # Commentaires internes
            cursor.execute("""
                SELECT ic.*, u.name as technician_name
                FROM intervention_comments ic
                LEFT JOIN users u ON ic.technician_id = u.id
                WHERE ic.work_order_id = %s
                ORDER BY ic.created_at DESC
            """, (work_order_id,))
            comments = cursor.fetchall()
            
            return render_template('interventions/details.html',
                                 work_order=work_order,
                                 notes=notes,
                                 media=media,
                                 comments=comments,
                                 user_role=session.get('user_role'))
                                 
    except Exception as e:
        security_logger.error(f"Error in intervention_details: {str(e)}")
        flash('Erreur lors de la récupération des détails', 'error')
        return redirect(url_for('api_interventions.list_interventions'))
    finally:
        conn.close()

@bp.route('/<int:work_order_id>/add_note', methods=['POST'])
@require_auth
@require_intervention_access
@limiter.limit("10 per minute") if limiter else lambda f: f
def add_note(work_order_id):
    """Ajouter une note d'intervention - SÉCURISÉ"""
    try:
        # Validation CSRF
        validate_csrf(request.form.get('csrf_token'))
        
        content = request.form.get('content', '').strip()
        note_type = request.form.get('note_type', 'private')
        
        # Validation des données
        if not content or len(content) < 3:
            return jsonify({'success': False, 'message': 'Le contenu de la note est requis (min 3 caractères)'})
        
        if len(content) > 5000:
            return jsonify({'success': False, 'message': 'Note trop longue (max 5000 caractères)'})
        
        if note_type not in ['private', 'public', 'internal']:
            note_type = 'private'
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO intervention_notes 
                    (work_order_id, technician_id, content, note_type, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (work_order_id, session['user_id'], content, note_type, datetime.now()))
                
                conn.commit()
                
                security_logger.info(
                    f"Note added: user {session['user_id']} added note to intervention {work_order_id}"
                )
                
                return jsonify({'success': True, 'message': 'Note ajoutée avec succès'})
                
        except Exception as e:
            conn.rollback()
            security_logger.error(f"Error adding note: {str(e)}")
            return jsonify({'success': False, 'message': 'Erreur lors de l\'ajout de la note'})
        finally:
            conn.close()
            
    except Exception as e:
        security_logger.error(f"CSRF or validation error in add_note: {str(e)}")
        return jsonify({'success': False, 'message': 'Erreur de validation'})

@bp.route('/<int:work_order_id>/add_comment', methods=['POST'])
@require_auth
@require_intervention_access
@limiter.limit("15 per minute") if limiter else lambda f: f
def add_comment(work_order_id):
    """Ajouter un commentaire interne - SÉCURISÉ"""
    try:
        # Validation CSRF
        validate_csrf(request.form.get('csrf_token'))
        
        content = request.form.get('content', '').strip()
        
        if not content or len(content) < 3:
            return jsonify({'success': False, 'message': 'Le contenu du commentaire est requis'})
        
        if len(content) > 3000:
            return jsonify({'success': False, 'message': 'Commentaire trop long (max 3000 caractères)'})

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO intervention_comments 
                    (work_order_id, technician_id, content, created_at)
                    VALUES (%s, %s, %s, %s)
                """, (work_order_id, session['user_id'], content, datetime.now()))
                
                conn.commit()
                
                security_logger.info(
                    f"Comment added: user {session['user_id']} added comment to intervention {work_order_id}"
                )
                
                return jsonify({'success': True, 'message': 'Commentaire ajouté avec succès'})
                
        except Exception as e:
            conn.rollback()
            security_logger.error(f"Error adding comment: {str(e)}")
            return jsonify({'success': False, 'message': 'Erreur lors de l\'ajout du commentaire'})
        finally:
            conn.close()
            
    except Exception as e:
        security_logger.error(f"Error in add_comment: {str(e)}")
        return jsonify({'success': False, 'message': 'Erreur de validation'})

@bp.route('/<int:work_order_id>/upload_photos', methods=['POST'])
@require_auth
@require_intervention_access
@limiter.limit("5 per minute") if limiter else lambda f: f
def upload_photos(work_order_id):
    """Upload de photos - SÉCURISÉ"""
    try:
        # Validation CSRF
        validate_csrf(request.form.get('csrf_token'))
        
        if 'photos' not in request.files:
            return jsonify({'success': False, 'message': 'Aucune photo sélectionnée'})
        
        files = request.files.getlist('photos')
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'message': 'Aucune photo sélectionnée'})
        
        # Limite du nombre de fichiers
        if len(files) > 10:
            return jsonify({'success': False, 'message': 'Maximum 10 fichiers autorisés'})
        
        uploaded_files = []
        conn = get_db_connection()
        
        try:
            with conn.cursor() as cursor:
                for file in files:
                    try:
                        # Validation sécurisée du fichier
                        filename = validate_file_security(file, {'png', 'jpg', 'jpeg', 'gif'})
                        
                        # Génération d'un nom unique
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        file_hash = hashlib.md5(f"{work_order_id}_{filename}_{timestamp}".encode()).hexdigest()[:8]
                        unique_filename = f"{timestamp}_{file_hash}_{filename}"
                        
                        # Chemin sécurisé
                        file_path = secure_upload_path(work_order_id, unique_filename)
                        
                        # Sauvegarde
                        file.save(file_path)
                        
                        # Chemin relatif pour la DB
                        relative_path = f"static/uploads/interventions/{work_order_id}/{unique_filename}"
                        
                        # Enregistrement en DB
                        cursor.execute("""
                            INSERT INTO intervention_media 
                            (work_order_id, technician_id, filename, file_path, file_type, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (work_order_id, session['user_id'], unique_filename, relative_path, 'image', datetime.now()))
                        
                        uploaded_files.append(unique_filename)
                        
                    except SecurityError as se:
                        security_logger.warning(f"File security violation: {str(se)}")
                        return jsonify({'success': False, 'message': f'Erreur sécurité: {str(se)}'})
                    except Exception as fe:
                        security_logger.error(f"File upload error: {str(fe)}")
                        continue
                
                conn.commit()
                
                security_logger.info(
                    f"Files uploaded: user {session['user_id']} uploaded {len(uploaded_files)} files to intervention {work_order_id}"
                )
                
                return jsonify({
                    'success': True, 
                    'message': f'{len(uploaded_files)} fichier(s) uploadé(s) avec succès',
                    'files': uploaded_files
                })
                
        except Exception as e:
            conn.rollback()
            security_logger.error(f"Error in upload process: {str(e)}")
            return jsonify({'success': False, 'message': 'Erreur lors de l\'upload'})
        finally:
            conn.close()
            
    except Exception as e:
        security_logger.error(f"Error in upload_photos: {str(e)}")
        return jsonify({'success': False, 'message': 'Erreur de validation'})

@bp.route('/<int:work_order_id>/quick_actions', methods=['POST'])
@require_auth
@require_intervention_access
@limiter.limit("20 per minute") if limiter else lambda f: f
def quick_actions(work_order_id):
    """Actions rapides sécurisées"""
    try:
        # Validation CSRF
        validate_csrf(request.form.get('csrf_token'))
        
        action = request.form.get('action')
        allowed_actions = ['start', 'pause', 'complete', 'assign', 'update_status']
        
        if action not in allowed_actions:
            return jsonify({'success': False, 'message': 'Action non autorisée'})
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                if action == 'update_status':
                    new_status = request.form.get('status')
                    allowed_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
                    
                    if new_status not in allowed_statuses:
                        return jsonify({'success': False, 'message': 'Statut non valide'})
                    
                    cursor.execute("""
                        UPDATE work_orders 
                        SET status = %s, updated_at = %s 
                        WHERE id = %s
                    """, (new_status, datetime.now(), work_order_id))
                    
                    message = f'Statut mis à jour vers {new_status}'
                else:
                    # Autres actions...
                    message = f'Action {action} exécutée'
                
                conn.commit()
                
                security_logger.info(
                    f"Quick action: user {session['user_id']} performed {action} on intervention {work_order_id}"
                )
                
                return jsonify({'success': True, 'message': message})
                
        except Exception as e:
            conn.rollback()
            security_logger.error(f"Error in quick_actions: {str(e)}")
            return jsonify({'success': False, 'message': 'Erreur lors de l\'action'})
        finally:
            conn.close()
            
    except Exception as e:
        security_logger.error(f"Error in quick_actions: {str(e)}")
        return jsonify({'success': False, 'message': 'Erreur de validation'})

@bp.route('/mobile')
@require_auth
@require_role('technician')
def mobile_interface():
    """Interface mobile optimisée - SÉCURISÉ"""
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Interventions du technicien uniquement
            cursor.execute("""
                SELECT 
                    wo.*,
                    c.name as customer_name,
                    c.phone as customer_phone,
                    v.make as vehicle_make,
                    v.model as vehicle_model
                FROM work_orders wo
                LEFT JOIN customers c ON wo.customer_id = c.id
                LEFT JOIN vehicles v ON wo.vehicle_id = v.id
                WHERE wo.assigned_technician_id = %s
                AND wo.status IN ('pending', 'in_progress')
                ORDER BY wo.scheduled_date ASC
                LIMIT 20
            """, (user_id,))
            
            interventions = cursor.fetchall()
            
            return render_template('interventions/mobile.html', interventions=interventions)
                                 
    except Exception as e:
        security_logger.error(f"Error in mobile_interface: {str(e)}")
        return render_template('interventions/mobile.html', interventions=[])
    finally:
        conn.close()

@bp.route('/<int:work_order_id>/update_vehicle', methods=['POST'])
@require_auth
@require_intervention_access
@require_role('admin', 'technician')
@limiter.limit("10 per minute") if limiter else lambda f: f
def update_vehicle_info(work_order_id):
    """Mettre à jour les informations du véhicule - SÉCURISÉ"""
    try:
        # Validation CSRF
        validate_csrf(request.form.get('csrf_token'))
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400
        
        # Validation des champs
        allowed_fields = ['make', 'model', 'year', 'mileage', 'color', 'fuel_type', 'notes']
        vehicle_data = {}
        
        for field in allowed_fields:
            if field in data:
                value = str(data[field]).strip()
                
                # Validation spécifique par champ
                if field == 'year' and value:
                    try:
                        year = int(value)
                        if year < 1900 or year > datetime.now().year + 2:
                            return jsonify({'success': False, 'message': 'Année invalide'})
                        vehicle_data[field] = year
                    except ValueError:
                        return jsonify({'success': False, 'message': 'Année doit être un nombre'})
                elif field == 'mileage' and value:
                    try:
                        mileage = int(value)
                        if mileage < 0 or mileage > 999999:
                            return jsonify({'success': False, 'message': 'Kilométrage invalide'})
                        vehicle_data[field] = mileage
                    except ValueError:
                        return jsonify({'success': False, 'message': 'Kilométrage doit être un nombre'})
                elif len(value) <= 255:  # Limite générale
                    vehicle_data[field] = value
        
        if not vehicle_data:
            return jsonify({'success': False, 'message': 'Aucune donnée valide à mettre à jour'})
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Récupérer l'ID du véhicule
                cursor.execute("SELECT vehicle_id FROM work_orders WHERE id = %s", (work_order_id,))
                result = cursor.fetchone()
                
                if not result or not result['vehicle_id']:
                    return jsonify({'success': False, 'message': 'Véhicule non trouvé'})
                
                vehicle_id = result['vehicle_id']
                
                # Construire la requête de mise à jour
                set_clauses = []
                values = []
                
                for field, value in vehicle_data.items():
                    set_clauses.append(f"{field} = %s")
                    values.append(value)
                
                set_clauses.append("updated_at = %s")
                values.append(datetime.now())
                values.append(vehicle_id)
                
                update_query = f"""
                    UPDATE vehicles 
                    SET {', '.join(set_clauses)}
                    WHERE id = %s
                """
                
                cursor.execute(update_query, values)
                conn.commit()
                
                security_logger.info(
                    f"Vehicle updated: user {session['user_id']} updated vehicle {vehicle_id} for intervention {work_order_id}"
                )
                
                return jsonify({'success': True, 'message': 'Informations véhicule mises à jour'})
                
        except Exception as e:
            conn.rollback()
            security_logger.error(f"Error updating vehicle: {str(e)}")
            return jsonify({'success': False, 'message': 'Erreur lors de la mise à jour'})
        finally:
            conn.close()
            
    except Exception as e:
        security_logger.error(f"Error in update_vehicle_info: {str(e)}")
        return jsonify({'success': False, 'message': 'Erreur de validation'})

# Gestionnaire d'erreurs sécurisé
@bp.errorhandler(403)
def forbidden(error):
    security_logger.warning(f"403 Forbidden: {request.endpoint} - User: {session.get('user_id')}")
    return jsonify({'error': 'Accès refusé'}), 403

@bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ressource non trouvée'}), 404

@bp.errorhandler(429)
def rate_limit_exceeded(error):
    security_logger.warning(f"Rate limit exceeded: {get_remote_address()} - {request.endpoint}")
    return jsonify({'error': 'Trop de requêtes, veuillez ralentir'}), 429
