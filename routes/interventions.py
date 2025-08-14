"""
Routes pour la gestion des interventions avec IA intégrée
Basé sur le PRD Fusionné v2.0 - Transcription, traduction, médias
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import pymysql
from datetime import datetime
import os
import json
from werkzeug.utils import secure_filename
import requests

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

def transcribe_audio(audio_path):
    """Transcription audio via OpenAI Whisper API (simulé)"""
    # TODO: Intégrer avec OpenAI Whisper API
    # Pour l'instant, retourne un texte simulé
    return {
        'text': '[Transcription simulée] Problème identifié sur le roulement avant droit, nécessite remplacement immédiat',
        'confidence': 0.95,
        'language': 'fr'
    }

def translate_text(text, target_languages=['en', 'es']):
    """Traduction via DeepL API (simulé)"""
    # TODO: Intégrer avec DeepL API
    translations = {}
    if 'en' in target_languages:
        translations['en'] = '[Simulated EN] Problem identified on right front bearing, requires immediate replacement'
    if 'es' in target_languages:
        translations['es'] = '[Simulado ES] Problema identificado en el rodamiento delantero derecho, requiere reemplazo inmediato'
    return translations

def get_ai_suggestions(work_order_id, context=''):
    """Suggestions contextuelles IA basées sur l'historique"""
    # TODO: Intégrer avec un modèle IA pour suggestions contextuelles
    suggestions = [
        {
            'type': 'part_recommendation',
            'title': 'Pièce recommandée',
            'content': 'Roulement avant droit - Référence: ROL-AVD-001',
            'confidence': 0.88
        },
        {
            'type': 'maintenance_tip',
            'title': 'Conseil de maintenance',
            'content': 'Vérifier également l\'état du roulement gauche lors du remplacement',
            'confidence': 0.72
        },
        {
            'type': 'time_estimate',
            'title': 'Estimation durée',
            'content': 'Temps estimé pour cette intervention: 2h30',
            'confidence': 0.91
        }
    ]
    return suggestions

@bp.route('/')
def list_interventions():
    """Liste des interventions avec vue adaptée au rôle"""
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    
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

@bp.route('/<int:work_order_id>/details')
def intervention_details(work_order_id):
    """Interface détaillée d'intervention avec outils IA"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupération du bon de travail
            cursor.execute("""
                SELECT 
                    wo.*,
                    u.name as technician_name,
                    c.name as customer_name,
                    c.phone as customer_phone,
                    c.email as customer_email,
                    c.address as customer_address
                FROM work_orders wo
                LEFT JOIN users u ON wo.assigned_technician_id = u.id
                LEFT JOIN customers c ON wo.customer_id = c.id
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
            
            # Notes d'intervention avec traductions
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
            
            # Médias avec transcriptions et traductions
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
            
            # Lignes de travail pour référence
            cursor.execute("""
                SELECT * FROM work_order_lines 
                WHERE work_order_id = %s 
                ORDER BY line_order, id
            """, (work_order_id,))
            work_order_lines = cursor.fetchall()
            
            # Suggestions IA contextuelles
            ai_suggestions = get_ai_suggestions(work_order_id)
            
            return render_template('interventions/details.html',
                                 work_order=work_order,
                                 notes=notes,
                                 media=media,
                                 work_order_lines=work_order_lines,
                                 ai_suggestions=ai_suggestions)
    finally:
        conn.close()

@bp.route('/<int:work_order_id>/add_note', methods=['POST'])
def add_note(work_order_id):
    """Ajouter une note d'intervention avec traduction automatique"""
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
            if (user_role == 'technician' and 
                wo['assigned_technician_id'] != session.get('user_id')):
                return jsonify({'success': False, 'message': 'Accès non autorisé'})
            
            # Traduction automatique si activée
            translations = {}
            if len(content) > 10:  # Traduction seulement pour les textes longs
                translations = translate_text(content)
            
            # Insertion de la note
            cursor.execute("""
                INSERT INTO intervention_notes (
                    work_order_id, technician_id, note_type, content,
                    translation_en, translation_es
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                work_order_id,
                session.get('user_id'),
                note_type,
                content,
                translations.get('en', ''),
                translations.get('es', '')
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
                'note': new_note,
                'translations': translations
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@bp.route('/<int:work_order_id>/upload_media', methods=['POST'])
def upload_media(work_order_id):
    """Upload de média avec transcription automatique pour l'audio"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Aucun fichier sélectionné'})
    
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Type de fichier non autorisé'})
    
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
            
            # Sauvegarde du fichier
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            
            upload_path = os.path.join('static/uploads/interventions', str(work_order_id))
            os.makedirs(upload_path, exist_ok=True)
            
            file_path = os.path.join(upload_path, filename)
            file.save(file_path)
            
            # Détermination du type de média
            ext = filename.rsplit('.', 1)[1].lower()
            if ext in ['mp3', 'wav', 'm4a']:
                media_type = 'audio'
            elif ext in ['mp4', 'mov', 'avi']:
                media_type = 'video'
            else:
                media_type = 'photo'
            
            # Transcription pour les fichiers audio
            transcription = ''
            translations = {}
            if media_type == 'audio':
                transcription_result = transcribe_audio(file_path)
                transcription = transcription_result.get('text', '')
                if transcription:
                    translations = translate_text(transcription)
            
            # Insertion en base
            cursor.execute("""
                INSERT INTO intervention_media (
                    work_order_id, technician_id, media_type, file_path,
                    transcription, translation_fr, translation_en, translation_es
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                work_order_id,
                session.get('user_id'),
                media_type,
                file_path,
                transcription,
                transcription,  # FR est la langue source
                translations.get('en', ''),
                translations.get('es', '')
            ))
            
            media_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'{media_type.title()} uploadé avec succès',
                'media_id': media_id,
                'file_path': file_path,
                'transcription': transcription,
                'translations': translations
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@bp.route('/<int:work_order_id>/voice_note', methods=['POST'])
def add_voice_note():
    """Interface pour dictée vocale avec transcription en temps réel"""
    # Cette route sera utilisée avec l'API Web Speech ou un upload audio
    audio_data = request.files.get('audio_data')
    
    if not audio_data:
        return jsonify({'success': False, 'message': 'Données audio manquantes'})
    
    # Traitement similaire à upload_media mais optimisé pour la dictée
    # TODO: Implémenter la transcription en temps réel
    
    return jsonify({
        'success': True,
        'transcription': '[Transcription en temps réel simulée] Le diagnostic initial montre un problème au niveau du système de freinage',
        'confidence': 0.87
    })

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

@bp.route('/ai/suggestions/<int:work_order_id>')
def get_suggestions(work_order_id):
    """API pour récupérer les suggestions IA contextuelles"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupération du contexte du bon de travail
            cursor.execute("""
                SELECT wo.*, c.vehicle_info, c.maintenance_history 
                FROM work_orders wo
                LEFT JOIN customers c ON wo.customer_id = c.id
                WHERE wo.id = %s
            """, (work_order_id,))
            
            work_order = cursor.fetchone()
            if not work_order:
                return jsonify({'suggestions': []})
            
            # Génération des suggestions basées sur le contexte
            suggestions = get_ai_suggestions(work_order_id, work_order['description'])
            
            return jsonify({
                'success': True,
                'suggestions': suggestions,
                'context': {
                    'work_order_id': work_order_id,
                    'description': work_order['description'],
                    'priority': work_order['priority']
                }
            })
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
