"""
Routes API pour le système de chat ChronoTech
Gestion des départements, messages et fichiers
"""
from flask import Blueprint, request, jsonify, send_from_directory, url_for
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from core.database import get_db_connection

# Blueprint pour les routes chat
chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

@chat_bp.route('/departments', methods=['GET'])
def get_departments():
    """Récupérer la liste des départements actifs"""
    try:
        db = get_db_connection()
        cursor = db.cursor()  # This will use DictCursor from utils.py
        
        cursor.execute("""
            SELECT id, name, chat_enabled, active, code, color 
            FROM departments 
            WHERE active = 1 
            ORDER BY name ASC
        """)
        
        departments = cursor.fetchall()  # Already dictionaries thanks to DictCursor
        
        cursor.close()
        db.close()
        
        return jsonify({
            'success': True,
            'departments': departments,
            'total': len(departments)
        })
        
    except Exception as e:
        print(f"Erreur récupération départements: {e}")
        print(f"Type d'erreur: {type(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Erreur lors de la récupération des départements'
        }), 500

@chat_bp.route('/messages/<channel>', methods=['GET'])
def get_channel_messages(channel):
    """Récupérer les messages d'un canal"""
    try:
        db = get_db_connection()
        cursor = db.cursor()  # DictCursor from utils.py
        
        # Limiter à 50 messages récents
        cursor.execute("""
            SELECT 
                m.id, m.user_id, m.channel, m.message, m.message_type, 
                m.timestamp, m.file_id, u.name as username
            FROM chat_messages m
            JOIN users u ON m.user_id = u.id
            WHERE m.channel = %s
            ORDER BY m.timestamp DESC
            LIMIT 50
        """, (channel,))
        
        messages = cursor.fetchall()  # Already dictionaries
        
        # Récupérer les informations des fichiers si nécessaire
        for message in messages:
            if message['file_id'] and message['message_type'] in ['file', 'image', 'voice', 'pdf']:
                cursor.execute("""
                    SELECT filename, filepath, file_type, file_size
                    FROM chat_files
                    WHERE id = %s
                """, (message['file_id'],))
                
                file_info = cursor.fetchone()  # Already a dictionary
                if file_info:
                    message['file_info'] = file_info
                if file_info:
                    message['file_info'] = file_info
                    # Créer l'URL pour récupérer le fichier
                    if message['message_type'] == 'voice':
                        message['file_url'] = url_for('chat.get_voice_file', filename=file_info['filepath'], _external=True)
                    else:
                        message['file_url'] = url_for('chat.get_chat_file', filename=file_info['filepath'], _external=True)
        
        cursor.close()
        db.close()
        
        # Inverser pour avoir l'ordre chronologique
        messages.reverse()
        
        return jsonify({
            'success': True,
            'messages': messages,
            'channel': channel,
            'total': len(messages)
        })
        
    except Exception as e:
        print(f"Erreur récupération messages: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur lors de la récupération des messages'
        }), 500

@chat_bp.route('/online-users', methods=['GET'])
def get_online_users():
    """Récupérer les utilisateurs en ligne"""
    try:
        db = get_db_connection()
        cursor = db.cursor()  # DictCursor from utils.py
        
        cursor.execute("""
            SELECT 
                u.id, u.name, u.status, 
                d.name as department, d.color as department_color
            FROM users u
            LEFT JOIN departments d ON u.department_id = d.id
            WHERE u.status IN ('online', 'busy')
            ORDER BY u.status ASC, u.name ASC
        """)
        
        users = cursor.fetchall()  # Already dictionaries
        cursor.close()
        db.close()
        
        return jsonify({
            'success': True,
            'users': users,
            'total': len(users)
        })
        
    except Exception as e:
        print(f"Erreur récupération utilisateurs en ligne: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur lors de la récupération des utilisateurs'
        }), 500

@chat_bp.route('/upload', methods=['POST'])
def upload_chat_file():
    """Upload de fichier pour le chat"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Aucun fichier fourni'}), 400
        
        file = request.files['file']
        channel = request.form.get('channel', 'global')
        user_id = request.form.get('user_id')
        
        if file.filename == '':
            return jsonify({'error': 'Aucun fichier sélectionné'}), 400
        
        if not user_id:
            return jsonify({'error': 'ID utilisateur requis'}), 400
        
        # Sécuriser le nom de fichier
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        safe_filename = f"{timestamp}_{filename}"
        
        # Créer le dossier d'upload si nécessaire
        upload_dir = os.path.join('uploads', 'chat_files')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Enregistrer le fichier
        filepath = os.path.join(upload_dir, safe_filename)
        file.save(filepath)
        
        # Enregistrer dans la base de données
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute("""
            INSERT INTO chat_files (user_id, channel, filename, filepath, file_type, file_size)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, channel, filename, safe_filename, file.content_type, file.content_length or 0))
        
        file_id = cursor.lastrowid
        db.commit()
        cursor.close()
        db.close()
        
        # URL pour récupérer le fichier
        file_url = url_for('chat.get_chat_file', filename=safe_filename, _external=True)
        
        return jsonify({
            'success': True,
            'url': file_url,
            'file_id': file_id,
            'filename': filename,
            'safe_filename': safe_filename
        })
        
    except Exception as e:
        print(f"Erreur upload fichier: {e}")
        return jsonify({'error': 'Erreur lors de l\'upload du fichier'}), 500

@chat_bp.route('/upload-voice', methods=['POST'])
def upload_voice():
    """Upload de message vocal"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Aucun fichier audio fourni'}), 400
        
        audio_file = request.files['file']
        channel = request.form.get('channel', 'global')
        user_id = request.form.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'ID utilisateur requis'}), 400
        
        # Enregistrer le fichier audio
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"voice_{timestamp}_{user_id}.webm"
        
        # Créer le dossier d'upload si nécessaire
        upload_dir = os.path.join('uploads', 'chat_voice')
        os.makedirs(upload_dir, exist_ok=True)
        
        filepath = os.path.join(upload_dir, filename)
        audio_file.save(filepath)
        
        # Enregistrer dans la base de données
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute("""
            INSERT INTO chat_files (user_id, channel, filename, filepath, file_type, file_size)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, channel, filename, filename, 'audio/webm', audio_file.content_length or 0))
        
        file_id = cursor.lastrowid
        db.commit()
        cursor.close()
        db.close()
        
        # URL pour récupérer l'audio
        voice_url = url_for('chat.get_voice_file', filename=filename, _external=True)
        
        return jsonify({
            'success': True,
            'url': voice_url,
            'file_id': file_id,
            'filename': filename
        })
        
    except Exception as e:
        print(f"Erreur upload vocal: {e}")
        return jsonify({'error': 'Erreur lors de l\'upload du message vocal'}), 500

@chat_bp.route('/files/<path:filename>')
def get_chat_file(filename):
    """Récupérer un fichier du chat"""
    try:
        return send_from_directory(os.path.join('uploads', 'chat_files'), filename)
    except Exception as e:
        print(f"Erreur récupération fichier: {e}")
        return jsonify({'error': 'Fichier non trouvé'}), 404

@chat_bp.route('/voice/<path:filename>')
def get_voice_file(filename):
    """Récupérer un message vocal"""
    try:
        return send_from_directory(os.path.join('uploads', 'chat_voice'), filename)
    except Exception as e:
        print(f"Erreur récupération vocal: {e}")
        return jsonify({'error': 'Fichier vocal non trouvé'}), 404

@chat_bp.route('/save-message', methods=['POST'])
def save_message():
    """Sauvegarder un message dans la base de données"""
    try:
        data = request.get_json()
        
        user_id = data.get('user_id')
        channel = data.get('channel')
        message = data.get('message')
        message_type = data.get('type', 'text')
        file_id = data.get('file_id')
        
        if not all([user_id, channel]):
            return jsonify({'error': 'Données manquantes'}), 400
        
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute("""
            INSERT INTO chat_messages (user_id, channel, message, message_type, file_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, channel, message, message_type, file_id))
        
        message_id = cursor.lastrowid
        db.commit()
        cursor.close()
        db.close()
        
        return jsonify({
            'success': True,
            'message_id': message_id
        })
        
    except Exception as e:
        print(f"Erreur sauvegarde message: {e}")
        return jsonify({'error': 'Erreur lors de la sauvegarde'}), 500
