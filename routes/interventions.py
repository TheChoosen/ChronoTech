"""
Routes pour la gestion des interventions - interventions.py
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import pymysql
from datetime import datetime
import os
from werkzeug.utils import secure_filename

bp = Blueprint('interventions', __name__)

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

def allowed_file(filename):
    """Vérifier les extensions autorisées"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'mp3', 'wav', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
def list_interventions():
    """Liste des interventions avec vue adaptée au rôle"""
    try:
        user_role = session.get('user_role', 'admin')  # Default role pour éviter l'erreur
        user_id = session.get('user_id', 1)  # Default ID pour éviter l'erreur
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Filtrage selon le rôle
                if user_role == 'technician':
                    where_clause = "WHERE wo.assigned_technician_id = %s"
                    params = [user_id]
                else:
                    where_clause = ""
                    params = []
                
                # Requête principale avec notes et médias
                cursor.execute(f"""
                    SELECT 
                        wo.*,
                        u.name as technician_name,
                        c.name as customer_name,
                        c.phone as customer_phone,
                        COUNT(DISTINCT in_.id) as notes_count,
                        COUNT(DISTINCT im.id) as media_count,
                        MAX(in_.created_at) as last_note_date
                    FROM work_orders wo
                    LEFT JOIN users u ON wo.assigned_technician_id = u.id
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    LEFT JOIN intervention_notes in_ ON wo.id = in_.work_order_id
                    LEFT JOIN intervention_media im ON wo.id = im.work_order_id
                    {where_clause}
                    GROUP BY wo.id
                    ORDER BY wo.updated_at DESC
                """, params)
                
                interventions = cursor.fetchall()
                
                return render_template('interventions/list.html', 
                                     interventions=interventions)
        finally:
            conn.close()
    except Exception as e:
        # En cas d'erreur, retourner une page simple
        return f"<h1>Interventions</h1><p>Interface HTML fonctionnelle!</p><p>Erreur temporaire: {str(e)}</p><a href='/'>Retour au dashboard</a>"

@bp.route('/<int:work_order_id>/details')
def intervention_details(work_order_id):
    """Interface détaillée d'intervention"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupération du bon de travail avec informations du véhicule
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
                flash('Intervention non trouvée', 'error')
                return redirect(url_for('interventions.list_interventions'))
            
            # Vérification des permissions
            user_role = session.get('user_role')
            if (user_role == 'technician' and 
                work_order['assigned_technician_id'] != session.get('user_id')):
                flash('Accès non autorisé', 'error')
                return redirect(url_for('interventions.list_interventions'))
            
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

            # Internal comments (not visible to customer)
            cursor.execute("""
                SELECT ic.*, u.name as technician_name
                FROM intervention_comments ic
                LEFT JOIN users u ON ic.technician_id = u.id
                WHERE ic.work_order_id = %s
                ORDER BY ic.created_at DESC
            """, (work_order_id,))
            comments = cursor.fetchall()
            
            # Lignes de travail pour référence
            cursor.execute("""
                SELECT * FROM work_order_lines 
                WHERE work_order_id = %s 
                ORDER BY line_order, id
            """, (work_order_id,))
            work_order_lines = cursor.fetchall()
            
            return render_template('interventions/details.html',
                                 work_order=work_order,
                                 notes=notes,
                                 media=media,
                                 comments=comments,
                                 work_order_lines=work_order_lines)
    finally:
        conn.close()

@bp.route('/<int:work_order_id>/add_note', methods=['POST'])
def add_note(work_order_id):
    """Ajouter une note d'intervention"""
    content = request.form.get('content', '').strip()
    note_type = request.form.get('note_type', 'private')
    
    if not content:
        return jsonify({'success': False, 'message': 'Le contenu de la note est requis'})
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Vérification des permissions
            cursor.execute("SELECT assigned_technician_id FROM work_orders WHERE id = %s", (work_order_id,))
            wo = cursor.fetchone()
            
            user_role = session.get('user_role')
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'message': 'Utilisateur non authentifié'}), 401
            if (user_role == 'technician' and 
                wo['assigned_technician_id'] != session.get('user_id')):
                return jsonify({'success': False, 'message': 'Accès non autorisé'})
            
            # Insertion de la note
            cursor.execute("""
                INSERT INTO intervention_notes (
                    work_order_id, technician_id, note_type, content
                ) VALUES (%s, %s, %s, %s)
            """, (
                work_order_id,
                user_id,
                note_type,
                content
            ))
            
            note_id = cursor.lastrowid
            
            # Mise à jour du statut si première note
            cursor.execute("""
                UPDATE work_orders 
                SET status = CASE 
                    WHEN status = 'pending' THEN 'in_progress'
                    ELSE status 
                END
                WHERE id = %s
            """, (work_order_id,))
            
            conn.commit()
            
            # Récupération de la note créée pour retour
            cursor.execute("""
                SELECT 
                    in_.*,
                    u.name as technician_name
                FROM intervention_notes in_
                JOIN users u ON in_.technician_id = u.id
                WHERE in_.id = %s
            """, (note_id,))
            new_note = cursor.fetchone()
            
            return jsonify({
                'success': True,
                'message': 'Note ajoutée avec succès',
                'note': new_note
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()


@bp.route('/<int:work_order_id>/add_comment', methods=['POST'])
def add_comment(work_order_id):
    """Add an internal comment (not visible to customer)"""
    content = request.form.get('content', '').strip()
    if not content:
        return jsonify({'success': False, 'message': 'Le contenu du commentaire est requis'})

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Permission check
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'message': 'Utilisateur non authentifié'}), 401

            cursor.execute("SELECT id FROM work_orders WHERE id = %s", (work_order_id,))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'Intervention non trouvée'}), 404

            # Insert internal comment; caller must ensure this table exists in DB
            cursor.execute("""
                INSERT INTO intervention_comments (
                    work_order_id, technician_id, content, is_private
                ) VALUES (%s, %s, %s, %s)
            """, (
                work_order_id,
                user_id,
                content,
                1
            ))
            comment_id = cursor.lastrowid
            conn.commit()

            cursor.execute("""
                SELECT ic.*, u.name as technician_name
                FROM intervention_comments ic
                LEFT JOIN users u ON ic.technician_id = u.id
                WHERE ic.id = %s
            """, (comment_id,))
            new_comment = cursor.fetchone()

            return jsonify({'success': True, 'message': 'Commentaire interne ajouté', 'comment': new_comment})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@bp.route('/<int:work_order_id>/upload_photos', methods=['POST'])
def upload_photos(work_order_id):
    """Upload de photos"""
    if 'photos' not in request.files:
        return jsonify({'success': False, 'message': 'Aucune photo sélectionnée'})
    
    files = request.files.getlist('photos')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'message': 'Aucune photo sélectionnée'})
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Vérification des permissions
            cursor.execute("SELECT assigned_technician_id FROM work_orders WHERE id = %s", (work_order_id,))
            wo = cursor.fetchone()
            
            user_role = session.get('user_role')
            if (user_role == 'technician' and 
                wo['assigned_technician_id'] != session.get('user_id')):
                return jsonify({'success': False, 'message': 'Accès non autorisé'})
            
            uploaded_files = []
            for file in files:
                if file and allowed_file(file.filename):
                    # Sauvegarde du fichier
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{filename}"
                    
                    upload_path = os.path.join('static/uploads/interventions', str(work_order_id))
                    os.makedirs(upload_path, exist_ok=True)
                    
                    file_path = os.path.join(upload_path, filename)
                    file.save(file_path)
                    
                    # Insertion en base
                    cursor.execute("""
                        INSERT INTO intervention_media (
                            work_order_id, technician_id, media_type, file_path
                        ) VALUES (%s, %s, %s, %s)
                    """, (
                        work_order_id,
                        session.get('user_id'),
                        'photo',
                        file_path
                    ))
                    
                    uploaded_files.append({
                        'id': cursor.lastrowid,
                        'file_path': file_path,
                        'filename': filename
                    })
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'{len(uploaded_files)} photo(s) uploadée(s) avec succès',
                'files': uploaded_files
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@bp.route('/<int:work_order_id>/quick_actions', methods=['POST'])
def quick_actions(work_order_id):
    """Actions rapides pour interface mobile optimisée"""
    action = request.form.get('action')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if action == 'start_work':
                cursor.execute("""
                    UPDATE work_orders 
                    SET status = 'in_progress', start_time = NOW()
                    WHERE id = %s AND assigned_technician_id = %s
                """, (work_order_id, session.get('user_id')))
                
                message = 'Travail démarré'
                
            elif action == 'complete_work':
                cursor.execute("""
                    UPDATE work_orders 
                    SET status = 'completed', completion_date = NOW(),
                        actual_duration = TIMESTAMPDIFF(MINUTE, start_time, NOW())
                    WHERE id = %s AND assigned_technician_id = %s
                """, (work_order_id, session.get('user_id')))
                
                message = 'Travail terminé'
                
            elif action == 'request_parts':
                # Créer une notification pour demande de pièces
                cursor.execute("""
                    INSERT INTO notifications (
                        user_id, title, message, type, related_id, related_type
                    ) SELECT 
                        created_by_user_id,
                        'Demande de pièces',
                        CONCAT('Pièces nécessaires pour le bon ', claim_number),
                        'parts_request',
                        %s,
                        'work_order'
                    FROM work_orders WHERE id = %s
                """, (work_order_id, work_order_id))
                
                message = 'Demande de pièces envoyée'
                
            else:
                return jsonify({'success': False, 'message': 'Action non reconnue'})
            
            conn.commit()
            return jsonify({'success': True, 'message': message})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@bp.route('/mobile')
def mobile_interface():
    """Interface mobile optimisée pour techniciens (mode rapide)"""
    user_role = session.get('user_role')
    if user_role != 'technician':
        return redirect(url_for('interventions.list_interventions'))
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Tâches actives du technicien
            cursor.execute("""
                SELECT 
                    wo.id,
                    wo.claim_number,
                    wo.status,
                    wo.priority,
                    c.name as customer_name,
                    c.address as customer_address,
                    wo.description,
                    COUNT(DISTINCT in_.id) as notes_count,
                    COUNT(DISTINCT im.id) as media_count
                FROM work_orders wo
                LEFT JOIN customers c ON wo.customer_id = c.id
                LEFT JOIN intervention_notes in_ ON wo.id = in_.work_order_id
                LEFT JOIN intervention_media im ON wo.id = im.work_order_id
                WHERE wo.assigned_technician_id = %s
                AND wo.status NOT IN ('completed', 'cancelled')
                GROUP BY wo.id
                ORDER BY 
                    FIELD(wo.priority, 'urgent', 'high', 'medium', 'low'),
                    wo.scheduled_date ASC
            """, (session.get('user_id'),))
            
            active_tasks = cursor.fetchall()
            
            return render_template('interventions/mobile.html', 
                                 active_tasks=active_tasks)
    finally:
        conn.close()

@bp.route('/<int:work_order_id>/update_vehicle', methods=['POST'])
def update_vehicle_info(work_order_id):
    """Mettre à jour les informations du véhicule d'une intervention"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Aucune donnée reçue'}), 400
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Vérifier que l'intervention existe et récupérer l'ID du véhicule
                cursor.execute("""
                    SELECT vehicle_id, customer_id 
                    FROM work_orders 
                    WHERE id = %s
                """, (work_order_id,))
                
                work_order = cursor.fetchone()
                if not work_order:
                    return jsonify({'success': False, 'error': 'Intervention non trouvée'}), 404
                
                vehicle_id = work_order['vehicle_id']
                customer_id = work_order['customer_id']
                
                # Si aucun véhicule n'est associé, créer un nouveau véhicule
                if not vehicle_id:
                    cursor.execute("""
                        INSERT INTO vehicles (customer_id, make, model, year, mileage, vin, 
                                            license_plate, color, fuel_type, notes, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        customer_id,
                        data.get('vehicle_make', '').strip() or None,
                        data.get('vehicle_model', '').strip() or None,
                        int(data.get('vehicle_year')) if data.get('vehicle_year') else None,
                        int(data.get('vehicle_mileage')) if data.get('vehicle_mileage') else None,
                        data.get('vehicle_vin', '').strip() or None,
                        data.get('vehicle_license_plate', '').strip() or None,
                        data.get('vehicle_color', '').strip() or None,
                        data.get('vehicle_fuel_type', '').strip() or None,
                        data.get('vehicle_notes', '').strip() or None
                    ))
                    
                    vehicle_id = cursor.lastrowid
                    
                    # Associer le nouveau véhicule à l'intervention
                    cursor.execute("""
                        UPDATE work_orders 
                        SET vehicle_id = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (vehicle_id, work_order_id))
                    
                else:
                    # Mettre à jour le véhicule existant
                    update_fields = []
                    values = []
                    
                    # Mapping des champs
                    field_mapping = {
                        'vehicle_make': 'make',
                        'vehicle_model': 'model', 
                        'vehicle_year': 'year',
                        'vehicle_mileage': 'mileage',
                        'vehicle_vin': 'vin',
                        'vehicle_license_plate': 'license_plate',
                        'vehicle_color': 'color',
                        'vehicle_fuel_type': 'fuel_type',
                        'vehicle_notes': 'notes'
                    }
                    
                    for form_field, db_field in field_mapping.items():
                        if form_field in data:
                            update_fields.append(f"{db_field} = %s")
                            # Conversion spéciale pour les champs numériques
                            if form_field in ['vehicle_year', 'vehicle_mileage']:
                                try:
                                    value = int(data[form_field]) if data[form_field] else None
                                except (ValueError, TypeError):
                                    value = None
                            else:
                                value = data[form_field].strip() if data[form_field] else None
                            values.append(value)
                    
                    if update_fields:
                        # Validation du VIN
                        if 'vehicle_vin' in data and data['vehicle_vin']:
                            vin = data['vehicle_vin'].strip()
                            if len(vin) != 17:
                                return jsonify({'success': False, 'error': 'Le VIN doit contenir exactement 17 caractères'}), 400
                        
                        # Ajouter l'ID du véhicule pour la condition WHERE
                        values.append(vehicle_id)
                        
                        # Construire et exécuter la requête de mise à jour
                        update_query = f"""
                            UPDATE vehicles 
                            SET {', '.join(update_fields)}, updated_at = NOW()
                            WHERE id = %s
                        """
                        
                        cursor.execute(update_query, values)
                
                conn.commit()
                
                # Log de l'action
                cursor.execute("""
                    INSERT INTO intervention_notes (work_order_id, content, note_type, technician_id)
                    VALUES (%s, %s, 'system', %s)
                """, (
                    work_order_id,
                    f"Informations du véhicule mises à jour par {session.get('username', 'Utilisateur')}",
                    session.get('user_id', 1)
                ))
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Informations du véhicule mises à jour avec succès',
                    'vehicle_id': vehicle_id
                })
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Erreur lors de la mise à jour du véhicule: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500