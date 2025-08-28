#openai.py
import datetime
import os
import io
import json
import requests
from flask import Blueprint, render_template, request, jsonify, current_app, session
from drive_helpers.google_drive_helper import get_drive_helper
from utils import get_db_connection

# googleapiclient helpers
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Import de la fonction de connexion DB depuis core
from core.database import db_manager

openai_bp = Blueprint('openai', __name__, template_folder='../templates')

OPENAI_API_BASE = os.environ.get('OPENAI_API_BASE', 'https://api.openai.com')


@openai_bp.route('/openai/audio')
def openai_audio_page():
    """Render audio upload page"""
    return render_template('openai/audio_upload.html')


@openai_bp.route('/api/openai/audio', methods=['POST'])
def handle_audio_upload():
    """Accept audio upload, send to OpenAI for transcription then optionally translate."""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return jsonify({'error': 'OpenAI API key not configured (OPENAI_API_KEY)'}), 500

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    mode = request.form.get('mode', 'transcribe')  # 'transcribe' or 'translate'
    target_lang = request.form.get('target_lang')  # optional
    
    # Basic validation
    filename = file.filename or 'audio'
    if filename == '':
        return jsonify({'error': 'Invalid file name'}), 400

    try:
        # Read file bytes into memory so we can reuse for Drive upload and OpenAI
        file_bytes = file.read()
        # reset file stream pointer for potential future reads
        try:
            file.stream.seek(0)
        except Exception:
            pass
            
        # Optionally save original upload to Google Drive
        drive_file_id = None
        company_raw = request.form.get('company')
        company = company_raw or "BDM"
        bon_id = request.form.get('bon_id') or request.form.get('id_bon_de_travail')
        save_to_drive = request.form.get('save_to_drive') in ('1', 'true', 'yes') or (company and bon_id)
        
        if save_to_drive:
            try:
                # Use the project's Drive helper which manages credentials/token safely
                drive_helper = get_drive_helper()
                if not drive_helper or not drive_helper.is_authenticated():
                    current_app.logger.warning('No Google Drive credentials available; skipping Drive upload')
                else:
                    # Build or reuse the Drive service
                    drive_service = getattr(drive_helper, 'service', None) or drive_helper._build_service()
                    if not drive_service:
                        current_app.logger.warning('Google Drive service unavailable; skipping Drive upload')
                    else:
                        # ensure folder structure and upload into Documents
                        def find_folder(service, name, parent_id=None):
                            q = f"name='{name.replace("'","\\'")}' and mimeType='application/vnd.google-apps.folder'"
                            if parent_id:
                                q += f" and '{parent_id}' in parents"
                            resp = service.files().list(q=q, spaces='drive', fields='files(id,name)').execute()
                            files = resp.get('files', [])
                            return files[0] if files else None

                        def create_folder(service, name, parent_id=None):
                            meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
                            if parent_id:
                                meta['parents'] = [parent_id]
                            f = service.files().create(body=meta, fields='id').execute()
                            return f

                        # Company folder under 'My Drive' root
                        company_name = company or 'UnknownCompany'
                        # Force parent to 'root' so the folder lives under My Drive
                        company_folder = find_folder(drive_service, company_name, 'root')
                        if not company_folder:
                            company_folder = create_folder(drive_service, company_name, 'root')
                        company_id = company_folder.get('id') if isinstance(company_folder, dict) else company_folder

                        # BonTravail folder
                        bt_folder = find_folder(drive_service, 'BonTravail', company_id)
                        if not bt_folder:
                            bt_folder = create_folder(drive_service, 'BonTravail', company_id)
                        bt_id = bt_folder.get('id') if isinstance(bt_folder, dict) else bt_folder

                        # Specific bon id folder
                        if not bon_id:
                            target_parent = bt_id
                        else:
                            bon_folder = find_folder(drive_service, str(bon_id), bt_id)
                            if not bon_folder:
                                bon_folder = create_folder(drive_service, str(bon_id), bt_id)
                            target_parent = bon_folder.get('id') if isinstance(bon_folder, dict) else bon_folder

                        # Ensure subfolders Notes, Documents, Photos
                        def ensure_subfolder(name):
                            fobj = find_folder(drive_service, name, target_parent)
                            if not fobj:
                                fobj = create_folder(drive_service, name, target_parent)
                            return fobj.get('id') if isinstance(fobj, dict) else fobj

                        notes_id = ensure_subfolder('Notes')
                        docs_id = ensure_subfolder('Documents')
                        photos_id = ensure_subfolder('Photos')

                        # Upload into Documents
                        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=file.mimetype or 'application/octet-stream', resumable=False)
                        metadata = {'name': filename, 'parents': [docs_id]}
                        uploaded = drive_service.files().create(body=metadata, media_body=media, fields='id,name,parents').execute()
                        drive_file_id = uploaded.get('id')
                        current_app.logger.info('Uploaded file to Drive id=%s', drive_file_id)
            except Exception:
                current_app.logger.exception('Drive upload failed')

        # Send file to OpenAI transcription endpoint (Whisper)
        transcribe_url = f"{OPENAI_API_BASE}/v1/audio/transcriptions"
        files = {
            'file': (filename, io.BytesIO(file_bytes), file.mimetype or 'application/octet-stream')
        }
        data = {
            'model': 'whisper-1'
        }

        headers = {
            'Authorization': f'Bearer {api_key}'
        }

        resp = requests.post(transcribe_url, headers=headers, data=data, files=files, timeout=120)
        if resp.status_code != 200:
            current_app.logger.error('OpenAI transcription error: %s %s', resp.status_code, resp.text)
            return jsonify({'error': 'Transcription failed', 'details': resp.text}), 500

        transcription_result = resp.json()
        text = transcription_result.get('text') or transcription_result.get('transcription') or ''

        translated_text = None
        if mode == 'translate' and target_lang:
            # Use OpenAI chat completions to translate the transcribed text to target language
            chat_url = f"{OPENAI_API_BASE}/v1/chat/completions"
            prompt = f"Translate the following text into {target_lang}. Preserve meaning and formatting:\n\n{text}"
            payload = {
                'model': 'gpt-4o-mini',
                'messages': [
                    {'role': 'system', 'content': 'You are a helpful translator.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.2,
                'max_tokens': 2000
            }
            headers_chat = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            resp2 = requests.post(chat_url, headers=headers_chat, json=payload, timeout=120)
            if resp2.status_code == 200:
                jr = resp2.json()
                # Attempt to extract assistant message
                translated_text = None
                choices = jr.get('choices') or []
                if len(choices):
                    translated_text = choices[0].get('message', {}).get('content') or choices[0].get('text')
                if translated_text is None:
                    translated_text = ''
            else:
                current_app.logger.error('OpenAI translation error: %s %s', resp2.status_code, resp2.text)
                return jsonify({'error': 'Translation failed', 'details': resp2.text}), 500

        # Optionally save a DB record if configured (use project's DB util)
        db_saved = False
        try:
            audio_table = os.environ.get('OPENAI_AUDIO_TABLE')
            audio_schema = os.environ.get('OPENAI_AUDIO_SCHEMA')
            if audio_table and audio_schema:
                # Build a DB record matching the `enregistrements_vocaux` schema
                nom_fichier = filename
                taille_fichier = len(file_bytes) if file_bytes is not None else None
                type_mime = file.mimetype or None
                langue_originale = request.form.get('lang_original') or request.form.get('langue_originale') or None
                langue_cible = target_lang or request.form.get('langue_cible') or None
                duree_secondes = None  # not computed here
                drive_chemin_dossier = None
                if drive_file_id and company:
                    # Use sanitized company value and prefix with 'My Drive' to reflect Drive UI
                    safe_company = company.split('/')[0] if isinstance(company, str) and '/' in company else company
                    if bon_id:
                        drive_chemin_dossier = f"My Drive/{safe_company}/BonTravail/{bon_id}/Documents"
                    else:
                        drive_chemin_dossier = f"My Drive/{safe_company}/Documents"

                statut_val = 'complete'
                cree_par = session.get('email') or session.get('user_id')

                db_record = {
                    'bon_travail_id': bon_id,
                    'compagnie': company or session.get('company_code'),
                    'employe_id': session.get('user_id'),
                    'employe_nom': session.get('nom_complet'),
                    'nom_fichier': nom_fichier,
                    'drive_fichier_id': drive_file_id,
                    'drive_chemin_dossier': drive_chemin_dossier,
                    'transcription': text,
                    'traduction': translated_text,
                    'langue_originale': langue_originale,
                    'langue_cible': langue_cible,
                    'taille_fichier': taille_fichier,
                    'duree_secondes': duree_secondes,
                    'type_mime': type_mime,
                    'statut': statut_val,
                    'message_erreur': None,
                    'cree_par': cree_par
                }

                # Insert directly using get_db_connection
                conn = None
                cursor = None
                try:
                    conn = get_db_connection(audio_schema)
                    cursor = conn.cursor()
                    cols = ', '.join(db_record.keys())
                    placeholders = ', '.join(['%s'] * len(db_record))
                    sql = f"INSERT INTO {audio_table} ({cols}) VALUES ({placeholders})"
                    cursor.execute(sql, list(db_record.values()))
                    conn.commit()
                    db_saved = True
                    try:
                        last_id = cursor.lastrowid
                    except Exception:
                        last_id = None
                    current_app.logger.info('Saved audio record id=%s', last_id)
                finally:
                    try:
                        if cursor:
                            cursor.close()
                    except Exception:
                        pass
                    try:
                        if conn and getattr(conn, 'is_connected', lambda: True)():
                            conn.close()
                    except Exception:
                        pass
        except Exception:
            current_app.logger.exception('Failed to save audio record to DB')

        return jsonify({
            'transcription': text, 
            'translation': translated_text, 
            'drive_file_id': drive_file_id, 
            'db_saved': db_saved,
            'success': True
        })

    except Exception as e:
        current_app.logger.exception('Error handling audio upload')
        return jsonify({'error': str(e)}), 500


@openai_bp.route('/interventions/<int:work_order_id>/process_audio', methods=['POST'])
def process_intervention_audio(work_order_id):
    """Process audio for specific intervention - uses the main audio handler"""
    # Add work_order_id to the form data for context
    # This route acts as a bridge to the main audio handler with intervention context
    return handle_audio_upload()


@openai_bp.route('/interventions/ai/generate_summary/<int:work_order_id>', methods=['POST'])
def generate_summary_route(work_order_id):
    """Enhanced route to generate AI summary with conversation support"""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return jsonify({'success': False, 'error': 'OpenAI API key not configured'}), 500
    
    try:
        data = request.get_json() or {}
        summary_type = data.get('summary_type', 'technical')
        language = data.get('language', 'fr')
        custom_instructions = data.get('custom_instructions', '')
        conversation_history = data.get('conversation_history', [])

        # Get work order context from database
        conn = db_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                # Get comprehensive work order details
                cursor.execute("""
                    SELECT 
                        wo.*,
                        c.name as customer_name,
                        c.phone as customer_phone,
                        c.email as customer_email,
                        c.address as customer_address,
                        u.name as technician_name
                    FROM work_orders wo
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    LEFT JOIN users u ON wo.assigned_technician_id = u.id
                    WHERE wo.id = %s
                """, (work_order_id,))
                work_order = cursor.fetchone()

                if not work_order:
                    return jsonify({'success': False, 'error': 'Work order not found'}), 404

                # Get all notes with details
                cursor.execute("""
                    SELECT 
                        in_.*,
                        u.name as technician_name
                    FROM intervention_notes in_
                    LEFT JOIN users u ON in_.technician_id = u.id
                    WHERE in_.work_order_id = %s
                    ORDER BY in_.created_at ASC
                """, (work_order_id,))
                notes = cursor.fetchall()

                # Get media with transcriptions if available
                cursor.execute("""
                    SELECT 
                        im.*,
                        u.name as technician_name
                    FROM intervention_media im
                    LEFT JOIN users u ON im.technician_id = u.id
                    WHERE im.work_order_id = %s
                    ORDER BY im.created_at ASC
                """, (work_order_id,))
                media = cursor.fetchall()

                # Get work order lines (parts/labor)
                cursor.execute("""
                    SELECT * FROM work_order_lines 
                    WHERE work_order_id = %s 
                    ORDER BY line_order, id
                """, (work_order_id,))
                work_order_lines = cursor.fetchall()
        finally:
            try:
                conn.close()
            except Exception:
                pass

        # Build comprehensive context for AI
        context = build_intervention_context(work_order, notes, media, work_order_lines)

        # Generate prompt based on summary type and language
        prompt = generate_summary_prompt(summary_type, language, custom_instructions, context)

        # Prepare conversation for OpenAI
        messages = [
            {
                'role': 'system', 
                'content': get_system_prompt(summary_type, language)
            }
        ]

        # Add conversation history if this is a follow-up
        if conversation_history:
            messages.extend(conversation_history[-10:])  # Keep last 10 messages for context

        messages.append({
            'role': 'user',
            'content': prompt
        })

        # Call OpenAI API
        chat_url = f"{OPENAI_API_BASE}/v1/chat/completions"

        payload = {
            'model': 'gpt-4o-mini',
            'messages': messages,
            'temperature': 0.3,
            'max_tokens': 2000
        }

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        resp = requests.post(chat_url, headers=headers, json=payload, timeout=120)
        if resp.status_code != 200:
            return jsonify({
                'success': False, 
                'error': 'AI summary generation failed', 
                'details': resp.text
            }), 500

        result = resp.json()
        choices = result.get('choices', [])
        if not choices:
            return jsonify({'success': False, 'error': 'No summary generated'}), 500

        summary = choices[0].get('message', {}).get('content', '')

        # Save the AI interaction to database for audit trail (best-effort)
        try:
            conn2 = db_manager.get_connection()
            try:
                with conn2.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO intervention_notes (
                            work_order_id, technician_id, note_type, content
                        ) VALUES (%s, %s, %s, %s)
                    """, (
                        work_order_id,
                        session.get('user_id'),
                        'ai_summary',
                        f"🤖 Résumé IA ({summary_type}):\n\n{summary}"
                    ))
                    conn2.commit()
            finally:
                try:
                    conn2.close()
                except Exception:
                    pass
        except Exception as e:
            # Log but don't fail the request if note saving fails
            current_app.logger.warning('Failed to save AI summary to notes: %s', str(e))

        return jsonify({
            'success': True,
            'summary': summary,
            'work_order_id': work_order_id,
            'summary_type': summary_type
        })
    except Exception as e:
        current_app.logger.exception('Error generating AI summary')
        return jsonify({'success': False, 'error': str(e)}), 500


@openai_bp.route('/interventions/ai/chat/<int:work_order_id>', methods=['POST'])
def ai_chat_followup(work_order_id):
    """Handle follow-up questions in AI chat"""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return jsonify({'success': False, 'error': 'OpenAI API key not configured'}), 500
    
    try:
        data = request.get_json() or {}
        question = data.get('question', '').strip()
        conversation_history = data.get('conversation_history', [])
        
        if not question:
            return jsonify({'success': False, 'error': 'Question is required'}), 400
        
        # Get current work order context (lighter version for follow-ups)
        conn = db_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT claim_number, c.name as customer_name, 
                           wo.vehicle_make, wo.vehicle_model, wo.vehicle_year
                    FROM work_orders wo
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    WHERE wo.id = %s
                """, (work_order_id,))
                work_order = cursor.fetchone()
                
                if not work_order:
                    return jsonify({'success': False, 'error': 'Work order not found'}), 404
        finally:
            try:
                conn.close()
            except Exception:
                pass
        
        # Prepare conversation for OpenAI
        messages = [
            {
                'role': 'system',
                'content': f"""Tu es un assistant technique expert en automobile. Tu aides avec l'intervention {work_order['claim_number']} pour le véhicule {work_order.get('vehicle_make', '')} {work_order.get('vehicle_model', '')} {work_order.get('vehicle_year', '')}.

Réponds de manière concise et précise aux questions de suivi. Base tes réponses sur le contexte de la conversation précédente et tes connaissances techniques."""
            }
        ]
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history[-8:])  # Keep recent context
        
        # Add the new question
        messages.append({
            'role': 'user',
            'content': question
        })
        
        # Call OpenAI API
        chat_url = f"{OPENAI_API_BASE}/v1/chat/completions"
        
        payload = {
            'model': 'gpt-4o-mini',
            'messages': messages,
            'temperature': 0.4,
            'max_tokens': 1000
        }
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        resp = requests.post(chat_url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            return jsonify({
                'success': False,
                'error': 'AI chat failed',
                'details': resp.text
            }), 500
        
        result = resp.json()
        choices = result.get('choices', [])
        if not choices:
            return jsonify({'success': False, 'error': 'No response generated'}), 500
        
        response = choices[0].get('message', {}).get('content', '')
        
        return jsonify({
            'success': True,
            'response': response,
            'work_order_id': work_order_id
        })
        
    except Exception as e:
        current_app.logger.exception('Error in AI chat follow-up')
        return jsonify({'success': False, 'error': str(e)}), 500


@openai_bp.route('/api/openai/generate_summary', methods=['POST'])
def generate_ai_summary():
    """Generate AI summary for intervention context (legacy route)"""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return jsonify({'error': 'OpenAI API key not configured'}), 500
    try:
        data = request.get_json() or {}
        work_order_id = data.get('work_order_id')
        extra_instructions = data.get('extra', '')

        if not work_order_id:
            return jsonify({'error': 'work_order_id required'}), 400

        # Query minimal needed data
        conn = db_manager.get_connection()
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
                    return jsonify({'error': 'Work order not found'}), 404

                cursor.execute("""
                    SELECT content, created_at, note_type
                    FROM intervention_notes
                    WHERE work_order_id = %s
                    ORDER BY created_at DESC
                    LIMIT 20
                """, (work_order_id,))
                notes = cursor.fetchall()

                cursor.execute("""
                    SELECT media_type, file_path, transcription
                    FROM intervention_media
                    WHERE work_order_id = %s
                    ORDER BY created_at DESC
                    LIMIT 20
                """, (work_order_id,))
                media = cursor.fetchall()
        finally:
            try:
                conn.close()
            except Exception:
                pass

        # Build context and prompt
        context = build_intervention_context(work_order, notes, media, [])
        if extra_instructions:
            context += f"\nAdditional instructions: {extra_instructions}\n"

        chat_url = f"{OPENAI_API_BASE}/v1/chat/completions"
        prompt = f"""Based on the following intervention data, provide a concise technical summary (French):\n\n{context}"""

        payload = {
            'model': 'gpt-4o-mini',
            'messages': [
                {'role': 'system', 'content': 'You are a technical expert assistant helping with automotive intervention summaries.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3,
            'max_tokens': 1000
        }

        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        resp = requests.post(chat_url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            current_app.logger.error('OpenAI summary error: %s %s', resp.status_code, resp.text)
            return jsonify({'error': 'Summary generation failed', 'details': resp.text}), 500

        result = resp.json()
        choices = result.get('choices', [])
        if not choices:
            return jsonify({'error': 'No summary generated'}), 500

        summary = choices[0].get('message', {}).get('content', '')
        return jsonify({'success': True, 'summary': summary, 'work_order_id': work_order_id})
    except Exception as e:
        current_app.logger.exception('Error generating AI summary')
        return jsonify({'error': str(e)}), 500


def build_intervention_context(work_order, notes, media, work_order_lines):
    """Build comprehensive context string for AI"""
    context = f"""
=== INFORMATIONS INTERVENTION ===
Numéro: {work_order['claim_number']}
Statut: {work_order['status']}
Priorité: {work_order.get('priority', 'Normal')}
Description: {work_order['description']}

=== CLIENT ===
Nom: {work_order['customer_name']}
Téléphone: {work_order.get('customer_phone', 'N/A')}
Email: {work_order.get('customer_email', 'N/A')}
Adresse: {work_order.get('customer_address', 'N/A')}

=== VÉHICULE ===
Marque: {work_order.get('vehicle_make', 'N/A')}
Modèle: {work_order.get('vehicle_model', 'N/A')}
Année: {work_order.get('vehicle_year', 'N/A')}
Immatriculation: {work_order.get('vehicle_registration', 'N/A')}
VIN: {work_order.get('vehicle_vin', 'N/A')}
Kilométrage: {work_order.get('vehicle_mileage', 'N/A')}

=== TECHNICIEN ===
Assigné à: {work_order.get('technician_name', 'Non assigné')}
Date programmée: {work_order.get('scheduled_date', 'Non définie')}
"""

    if work_order_lines:
        context += f"\n=== LIGNES DE TRAVAIL ===\n"
        for line in work_order_lines:
            context += f"- {line.get('description', 'N/A')} | Quantité: {line.get('quantity', 0)} | Prix: {line.get('unit_price', 0)}€\n"

    if notes:
        context += f"\n=== NOTES D'INTERVENTION ({len(notes)} notes) ===\n"
        for note in notes:
            timestamp = note['created_at'].strftime('%d/%m/%Y %H:%M') if note.get('created_at') else 'N/A'
            technician = note.get('technician_name', 'Inconnu')
            note_type = note.get('note_type', 'private')
            content = note.get('content', '')
            context += f"[{timestamp}] {technician} ({note_type}): {content}\n"

    if media:
        context += f"\n=== MÉDIAS ({len(media)} fichiers) ===\n"
        for m in media:
            timestamp = m['created_at'].strftime('%d/%m/%Y %H:%M') if m.get('created_at') else 'N/A'
            technician = m.get('technician_name', 'Inconnu')
            media_type = m.get('media_type', 'unknown')
            file_path = m.get('file_path', 'N/A')
            context += f"[{timestamp}] {technician} - {media_type}: {file_path}\n"
            
            # Add transcription if available (from audio processing)
            if m.get('transcription'):
                context += f"  Transcription: {m['transcription']}\n"
            if m.get('translation'):
                context += f"  Traduction: {m['translation']}\n"

    return context


def generate_summary_prompt(summary_type, language, custom_instructions, context):
    """Generate appropriate prompt based on summary type and language"""
    
    language_names = {
        'fr': 'français',
        'en': 'anglais', 
        'es': 'espagnol',
        'de': 'allemand'
    }
    
    lang_instruction = f" Réponds en {language_names.get(language, 'français')}."
    
    base_prompts = {
        'technical': f"""Analyse les informations suivantes et génère un résumé technique complet de cette intervention automobile.

Le résumé doit inclure:
1. **Diagnostic principal** - Problème(s) identifié(s)
2. **Travaux effectués** - Actions réalisées par le technicien
3. **Pièces utilisées/nécessaires** - Liste avec références si disponibles
4. **Observations techniques** - Points importants notés
5. **Recommandations** - Prochaines étapes ou maintenance préventive
6. **Temps estimé/réel** - Durée des travaux
7. **Points de sécurité** - Précautions importantes

Format: Structure claire avec sections distinctes.{lang_instruction}

DONNÉES INTERVENTION:
{context}""",

        'customer': f"""Crée un rapport client simplifié et compréhensible pour cette intervention automobile.

Le rapport doit inclure:
1. **Résumé du problème** - En termes simples
2. **Travaux réalisés** - Ce qui a été fait
3. **Pièces remplacées** - Si applicable
4. **Coût** - Estimation ou réel
5. **Garantie** - Informations sur la garantie
6. **Conseils d'entretien** - Recommandations pour le client
7. **Prochaine visite** - Si nécessaire

Ton: Professionnel mais accessible, évite le jargon technique.{lang_instruction}

DONNÉES INTERVENTION:
{context}""",

        'parts': f"""Analyse les besoins en pièces détachées pour cette intervention automobile.

L'analyse doit inclure:
1. **Pièces nécessaires** - Liste complète avec références
2. **Disponibilité** - Estimation des délais
3. **Coûts estimés** - Prix approximatifs
4. **Alternatives** - Pièces compatibles ou génériques
5. **Priorités** - Urgent vs. préventif
6. **Fournisseurs recommandés** - Si pertinent
7. **Stock à maintenir** - Pour interventions futures

Format: Liste structurée avec détails techniques.{lang_instruction}

DONNÉES INTERVENTION:
{context}""",

        'time': f"""Analyse le temps et les coûts de cette intervention automobile.

L'estimation doit inclure:
1. **Temps de diagnostic** - Heures passées/estimées
2. **Temps de travail** - Main-d'œuvre par tâche
3. **Temps d'attente** - Pièces, outils, etc.
4. **Coût main-d'œuvre** - Calcul détaillé
5. **Coût pièces** - Total matériel
6. **Coût total** - Estimation finale
7. **Comparaison budget** - Vs. devis initial
8. **Optimisations** - Suggestions d'amélioration

Format: Tableau détaillé avec justifications.{lang_instruction}

DONNÉES INTERVENTION:
{context}""",

        'custom': f"""{custom_instructions if custom_instructions else 'Génère un résumé personnalisé de cette intervention automobile.'}

{lang_instruction}

DONNÉES INTERVENTION:
{context}"""
    }
    
    return base_prompts.get(summary_type, base_prompts['technical'])


def get_system_prompt(summary_type, language):
    """Get system prompt based on summary type and language"""
    
    base_system = {
        'fr': "Tu es un expert technique automobile avec plus de 15 ans d'expérience. Tu génères des rapports précis et professionnels basés sur les données d'interventions. Tes analyses sont détaillées, pratiques et orientées solutions.",
        'en': "You are an automotive technical expert with over 15 years of experience. You generate accurate and professional reports based on intervention data. Your analyses are detailed, practical and solution-oriented.",
        'es': "Eres un experto técnico automotriz con más de 15 años de experiencia. Generas informes precisos y profesionales basados en datos de intervenciones. Tus análisis son detallados, prácticos y orientados a soluciones.",
        'de': "Sie sind ein Kfz-Techniker mit über 15 Jahren Erfahrung. Sie erstellen präzise und professionelle Berichte basierend auf Interventionsdaten. Ihre Analysen sind detailliert, praktisch und lösungsorientiert."
    }
    
    specializations = {
        'technical': " Tu te spécialises dans les diagnostics techniques approfondis et les recommandations de réparation.",
        'customer': " Tu excelles dans la communication client et la vulgarisation technique.",
        'parts': " Tu es expert en pièces détachées, compatibilités et approvisionnement.",
        'time': " Tu es spécialisé dans l'estimation de temps et l'analyse des coûts.",
        'custom': " Tu adaptes ton expertise selon les besoins spécifiques."
    }
    
    system_msg = base_system.get(language, base_system['fr'])
    system_msg += specializations.get(summary_type, specializations['technical'])
    
    return system_msg

@openai_bp.route('/interventions/suggestions/<int:work_order_id>', methods=['GET'])
def get_intelligent_suggestions(work_order_id):
    """Generate intelligent suggestions based on intervention context and web research"""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return jsonify({'success': False, 'error': 'OpenAI API key not configured'}), 500
    
    try:
        # Get work order context
        conn = db_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        wo.*,
                        c.name as customer_name,
                        u.name as technician_name
                    FROM work_orders wo
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    LEFT JOIN users u ON wo.assigned_technician_id = u.id
                    WHERE wo.id = %s
                """, (work_order_id,))
                work_order = cursor.fetchone()

                if not work_order:
                    return jsonify({'success': False, 'error': 'Work order not found'}), 404

                # Get recent notes for context
                cursor.execute("""
                    SELECT content, created_at, note_type
                    FROM intervention_notes
                    WHERE work_order_id = %s
                    ORDER BY created_at DESC LIMIT 5
                """, (work_order_id,))
                recent_notes = cursor.fetchall()
        finally:
            try:
                conn.close()
            except Exception:
                pass

        # Perform web research and generate suggestions
        suggestions = generate_contextual_suggestions(work_order, recent_notes, api_key)

        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'work_order_id': work_order_id
        })
    except Exception as e:
        current_app.logger.exception('Error generating suggestions')
        return jsonify({'success': False, 'error': str(e)}), 500


@openai_bp.route('/interventions/suggestions/search', methods=['POST'])
def search_technical_info():
    """Search for specific technical information with web lookup"""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return jsonify({'success': False, 'error': 'OpenAI API key not configured'}), 500
    
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        vehicle_info = data.get('vehicle_info', {})
        context = data.get('context', '')
        
        if not query:
            return jsonify({'success': False, 'error': 'Search query is required'}), 400
        # Perform targeted web search and analysis
        search_results = perform_technical_search(query, vehicle_info, context, api_key)

        return jsonify({
            'success': True,
            'results': search_results,
            'query': query
        })
    except Exception as e:
        current_app.logger.exception('Error in technical search')
        return jsonify({'success': False, 'error': str(e)}), 500


def generate_contextual_suggestions(work_order, recent_notes, api_key):
    """Generate intelligent suggestions based on intervention context"""
    
    # Build vehicle context
    vehicle_context = {
        'make': work_order.get('vehicle_make', ''),
        'model': work_order.get('vehicle_model', ''),
        'year': work_order.get('vehicle_year', ''),
        'mileage': work_order.get('vehicle_mileage', ''),
        'vin': work_order.get('vehicle_vin', '')
    }
    
    # Build problem context
    problem_description = work_order.get('description', '')
    notes_context = '\n'.join([note['content'] for note in recent_notes[:3]])
    
    # Perform web research for common issues
    web_research = research_common_issues(vehicle_context, problem_description, api_key)
    
    # Generate comprehensive suggestions
    suggestions = {
        'diagnostic_steps': generate_diagnostic_suggestions(vehicle_context, problem_description, web_research, api_key),
        'common_parts': get_common_parts_for_issue(vehicle_context, problem_description, api_key),
        'repair_procedures': get_repair_procedures(vehicle_context, problem_description, web_research, api_key),
        'safety_warnings': get_safety_warnings(vehicle_context, problem_description, api_key),
        'time_estimates': get_time_estimates(vehicle_context, problem_description, api_key),
        'preventive_maintenance': get_preventive_suggestions(vehicle_context, api_key)
    }
    
    return suggestions


def research_common_issues(vehicle_context, problem_description, api_key):
    """Research common issues for this vehicle model and problem"""
    
    vehicle_query = f"{vehicle_context['year']} {vehicle_context['make']} {vehicle_context['model']}"
    search_query = f"{vehicle_query} {problem_description} common problems solutions"
    
    # Use OpenAI to generate and analyze web search queries
    chat_url = f"{OPENAI_API_BASE}/v1/chat/completions"
    
    prompt = f"""As an automotive expert, analyze this vehicle and problem to suggest specific web research queries:

Vehicle: {vehicle_query}
Problem: {problem_description}

Generate 3 specific search queries that would help find:
1. Common issues for this vehicle model
2. Technical service bulletins (TSB)
3. Repair procedures and part recommendations

Return only the search queries, one per line."""

    payload = {
        'model': 'gpt-4o-mini',
        'messages': [
            {'role': 'system', 'content': 'You are an expert automotive technician who knows how to research vehicle problems effectively.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.3,
        'max_tokens': 200
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        resp = requests.post(chat_url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            search_queries = result['choices'][0]['message']['content'].strip().split('\n')
            
            # Simulate web research results (in production, you'd use actual web search)
            research_results = []
            for query in search_queries[:2]:  # Limit to 2 queries for performance
                research_results.append({
                    'query': query.strip(),
                    'findings': f"Research findings for: {query.strip()}"
                })
            
            return research_results
        else:
            return []
    except Exception:
        return []


def generate_diagnostic_suggestions(vehicle_context, problem_description, web_research, api_key):
    """Generate step-by-step diagnostic suggestions"""
    
    vehicle_info = f"{vehicle_context['year']} {vehicle_context['make']} {vehicle_context['model']}"
    research_context = '\n'.join([r['findings'] for r in web_research])
    
    prompt = f"""As an expert automotive diagnostician, provide a step-by-step diagnostic procedure for:

Vehicle: {vehicle_info}
Problem: {problem_description}
Mileage: {vehicle_context.get('mileage', 'Unknown')}

Web Research Context:
{research_context}

Provide a logical diagnostic sequence with:
1. Initial visual inspection steps
2. Specific tests to perform
3. Tools/equipment needed
4. Expected readings/values
5. Decision points for next steps

Format as numbered steps, be specific and practical."""

    return call_openai_for_suggestions(prompt, api_key, 'diagnostic expert')


def get_common_parts_for_issue(vehicle_context, problem_description, api_key):
    """Get commonly needed parts for this type of issue"""
    
    vehicle_info = f"{vehicle_context['year']} {vehicle_context['make']} {vehicle_context['model']}"
    
    prompt = f"""Based on the vehicle and problem description, list the most commonly needed parts:

Vehicle: {vehicle_info}
Problem: {problem_description}

Provide:
1. Most likely parts that need replacement
2. OEM part numbers if possible
3. Alternative/aftermarket options
4. Estimated costs (ranges)
5. Difficulty level for replacement

Focus on parts with highest failure rates for this vehicle/problem combination."""

    return call_openai_for_suggestions(prompt, api_key, 'parts specialist')


def get_repair_procedures(vehicle_context, problem_description, web_research, api_key):
    """Get specific repair procedures and tips"""
    
    vehicle_info = f"{vehicle_context['year']} {vehicle_context['make']} {vehicle_context['model']}"
    research_context = '\n'.join([r['findings'] for r in web_research])
    
    prompt = f"""Provide specific repair procedures and technical tips for:

Vehicle: {vehicle_info}
Problem: {problem_description}

Research Context:
{research_context}

Include:
1. Step-by-step repair procedure
2. Special tools required
3. Torque specifications
4. Common mistakes to avoid
5. Pro tips and shortcuts
6. Quality check procedures

Be specific to this vehicle model and year."""

    return call_openai_for_suggestions(prompt, api_key, 'repair specialist')


def get_safety_warnings(vehicle_context, problem_description, api_key):
    """Generate safety warnings specific to this repair"""
    
    vehicle_info = f"{vehicle_context['year']} {vehicle_context['make']} {vehicle_context['model']}"
    
    prompt = f"""Identify critical safety considerations for this repair:

Vehicle: {vehicle_info}
Problem: {problem_description}

Provide:
1. Personal safety hazards and precautions
2. Vehicle system safety (airbags, fuel, electrical)
3. Environmental hazards
4. Required safety equipment
5. Emergency procedures
6. Post-repair safety checks

Prioritize by risk level - list most critical first."""

    return call_openai_for_suggestions(prompt, api_key, 'safety expert')


def get_time_estimates(vehicle_context, problem_description, api_key):
    """Get realistic time estimates for diagnosis and repair"""
    
    vehicle_info = f"{vehicle_context['year']} {vehicle_context['make']} {vehicle_context['model']}"
    
    prompt = f"""Provide realistic time estimates for:

Vehicle: {vehicle_info}
Problem: {problem_description}

Break down timing for:
1. Initial diagnosis (min/max)
2. Parts procurement time
3. Actual repair time (experienced vs novice)
4. Quality testing and verification
5. Total customer turnaround time

Consider:
- Vehicle accessibility
- Part availability
- Complexity level
- Potential complications

Provide time ranges and factors that could extend work."""

    return call_openai_for_suggestions(prompt, api_key, 'time estimation expert')


def get_preventive_suggestions(vehicle_context, api_key):
    """Get preventive maintenance suggestions"""
    
    vehicle_info = f"{vehicle_context['year']} {vehicle_context['make']} {vehicle_context['model']}"
    mileage = vehicle_context.get('mileage', 'Unknown')
    
    prompt = f"""Suggest preventive maintenance for:

Vehicle: {vehicle_info}
Current Mileage: {mileage}

Provide:
1. Due/overdue maintenance items
2. Upcoming maintenance (next 6 months)
3. Common failure points for this model/year
4. Recommended inspection intervals
5. Cost-effective maintenance bundles

Focus on items that prevent future breakdowns and maintain reliability."""

    return call_openai_for_suggestions(prompt, api_key, 'maintenance specialist')


def call_openai_for_suggestions(prompt, api_key, specialist_role):
    """Helper function to call OpenAI API for suggestions"""
    
    chat_url = f"{OPENAI_API_BASE}/v1/chat/completions"
    
    payload = {
        'model': 'gpt-4o-mini',
        'messages': [
            {
                'role': 'system', 
                'content': f'You are an expert automotive {specialist_role} with 20+ years of experience. Provide practical, actionable advice.'
            },
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.3,
        'max_tokens': 1000
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        resp = requests.post(chat_url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            result = resp.json()
            return result['choices'][0]['message']['content'].strip()
        else:
            return f"Error generating {specialist_role} suggestions"
    except Exception as e:
        return f"Failed to generate {specialist_role} suggestions: {str(e)}"


async def perform_technical_search(query, vehicle_info, context, api_key):
    """Perform targeted technical search with AI analysis"""
    
    # Enhanced query with vehicle context
    enhanced_query = f"{vehicle_info.get('year', '')} {vehicle_info.get('make', '')} {vehicle_info.get('model', '')} {query}"
    
    # Use AI to analyze and provide comprehensive answer
    chat_url = f"{OPENAI_API_BASE}/v1/chat/completions"
    
    prompt = f"""Research and provide comprehensive technical information about:

Search Query: {enhanced_query}
Vehicle Context: {vehicle_info}
Additional Context: {context}

Provide:
1. Technical explanation
2. Common causes and solutions
3. Diagnostic procedures
4. Part recommendations
5. Repair tips and tricks
6. Potential complications
7. Related issues to check

Use your automotive knowledge to provide detailed, practical information."""

    payload = {
        'model': 'gpt-4o-mini',
        'messages': [
            {
                'role': 'system', 
                'content': 'You are an automotive technical research expert. Provide comprehensive, accurate information based on extensive automotive knowledge.'
            },
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.3,
        'max_tokens': 1500
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        resp = requests.post(chat_url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            result = resp.json()
            return {
                'analysis': result['choices'][0]['message']['content'].strip(),
                'query': enhanced_query,
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {'error': 'Search failed', 'query': enhanced_query}
    except Exception as e:
        return {'error': str(e), 'query': enhanced_query}
