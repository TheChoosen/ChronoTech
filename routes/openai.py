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
        # Determine a company short-code (letters like NOR, BDM, FRA) in preference order:
        # 1) value from form (first path segment) if it looks like letters
        # 2) session company_code if it looks like letters
        # 3) fallback: derive via get_user_company_code(session.user_id)
        company_raw = request.form.get('company')
        company = "BDM"
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

        return jsonify({'transcription': text, 'translation': translated_text, 'drive_file_id': drive_file_id, 'db_saved': db_saved})

    except Exception as e:
        current_app.logger.exception('Error handling audio upload')
        return jsonify({'error': str(e)}), 500


