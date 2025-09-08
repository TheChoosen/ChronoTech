"""
ChronoTech - Service de Chat Contextuel
Gestion des conversations en temps réel
"""

from flask import Blueprint, request, jsonify, session
from flask_socketio import emit, join_room, leave_room, disconnect
from core.database import get_db_connection
from core.security import token_required
import json
from datetime import datetime

contextual_chat_bp = Blueprint('contextual_chat', __name__, url_prefix='/api/chat')

# Socket.IO Events
def init_socketio_events(socketio):
    """Initialiser les événements Socket.IO pour le chat"""
    
    @socketio.on('join_chat')
    def on_join_chat(data):
        """Rejoindre une conversation contextuelle"""
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Non authentifié'})
            return
        
        context_type = data.get('context_type')  # work_order, customer, vehicle
        context_id = data.get('context_id')
        room_name = f"{context_type}_{context_id}"
        
        join_room(room_name)
        
        # Marquer la présence de l'utilisateur
        mark_user_presence(user_id, context_type, context_id, True)
        
        # Envoyer les messages récents
        recent_messages = get_recent_messages(context_type, context_id)
        emit('chat_history', {
            'messages': recent_messages,
            'context': {'type': context_type, 'id': context_id}
        })
        
        # Notifier les autres utilisateurs
        emit('user_joined', {
            'user_id': user_id,
            'user_name': get_user_name(user_id)
        }, room=room_name, include_self=False)
    
    @socketio.on('leave_chat')
    def on_leave_chat(data):
        """Quitter une conversation"""
        user_id = session.get('user_id')
        if not user_id:
            return
        
        context_type = data.get('context_type')
        context_id = data.get('context_id')
        room_name = f"{context_type}_{context_id}"
        
        leave_room(room_name)
        mark_user_presence(user_id, context_type, context_id, False)
        
        emit('user_left', {
            'user_id': user_id,
            'user_name': get_user_name(user_id)
        }, room=room_name)
    
    @socketio.on('send_message')
    def on_send_message(data):
        """Envoyer un message dans le chat"""
        user_id = session.get('user_id')
        if not user_id:
            emit('error', {'message': 'Non authentifié'})
            return
        
        context_type = data.get('context_type')
        context_id = data.get('context_id')
        message_content = data.get('message', '').strip()
        message_type = data.get('type', 'text')  # text, file, system
        
        if not message_content:
            emit('error', {'message': 'Message vide'})
            return
        
        # Sauvegarder le message
        message_id = save_chat_message(
            user_id, context_type, context_id, 
            message_content, message_type
        )
        
        if message_id:
            # Préparer le message pour diffusion
            message_data = {
                'id': message_id,
                'user_id': user_id,
                'user_name': get_user_name(user_id),
                'message': message_content,
                'type': message_type,
                'timestamp': datetime.now().isoformat(),
                'context': {'type': context_type, 'id': context_id}
            }
            
            room_name = f"{context_type}_{context_id}"
            emit('new_message', message_data, room=room_name)
            
            # Notifier les utilisateurs hors ligne
            notify_offline_users(context_type, context_id, message_data)
    
    @socketio.on('typing_start')
    def on_typing_start(data):
        """Utilisateur commence à taper"""
        user_id = session.get('user_id')
        if not user_id:
            return
        
        context_type = data.get('context_type')
        context_id = data.get('context_id')
        room_name = f"{context_type}_{context_id}"
        
        emit('user_typing', {
            'user_id': user_id,
            'user_name': get_user_name(user_id),
            'typing': True
        }, room=room_name, include_self=False)
    
    @socketio.on('typing_stop')
    def on_typing_stop(data):
        """Utilisateur arrête de taper"""
        user_id = session.get('user_id')
        if not user_id:
            return
        
        context_type = data.get('context_type')
        context_id = data.get('context_id')
        room_name = f"{context_type}_{context_id}"
        
        emit('user_typing', {
            'user_id': user_id,
            'user_name': get_user_name(user_id),
            'typing': False
        }, room=room_name, include_self=False)
    
    @socketio.on('disconnect')
    def on_disconnect():
        """Gérer la déconnexion"""
        user_id = session.get('user_id')
        if user_id:
            # Marquer l'utilisateur comme hors ligne dans tous les contextes
            mark_user_offline(user_id)

# API REST pour le chat
@contextual_chat_bp.route('/contexts/<context_type>/<int:context_id>/messages', methods=['GET'])
@token_required
def get_chat_messages(context_type, context_id):
    """Récupérer l'historique des messages"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Récupérer les messages avec pagination
        offset = (page - 1) * limit
        cursor.execute("""
            SELECT 
                cm.*,
                u.name as user_name,
                u.email as user_email
            FROM chat_messages cm
            LEFT JOIN users u ON cm.user_id = u.id
            WHERE cm.context_type = %s AND cm.context_id = %s
            ORDER BY cm.created_at DESC
            LIMIT %s OFFSET %s
        """, (context_type, context_id, limit, offset))
        
        messages = cursor.fetchall()
        
        # Compter le total
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM chat_messages
            WHERE context_type = %s AND context_id = %s
        """, (context_type, context_id))
        
        total = cursor.fetchone()['total']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'messages': messages,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@contextual_chat_bp.route('/contexts/<context_type>/<int:context_id>/users', methods=['GET'])
@token_required
def get_active_users(context_type, context_id):
    """Récupérer les utilisateurs actifs dans le chat"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                cp.user_id,
                u.name as user_name,
                u.email as user_email,
                cp.joined_at,
                cp.last_seen
            FROM chat_presence cp
            LEFT JOIN users u ON cp.user_id = u.id
            WHERE cp.context_type = %s 
            AND cp.context_id = %s 
            AND cp.is_active = 1
            ORDER BY cp.joined_at DESC
        """, (context_type, context_id))
        
        active_users = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'active_users': active_users
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@contextual_chat_bp.route('/upload', methods=['POST'])
@token_required
def upload_chat_file():
    """Upload d'un fichier dans le chat"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Aucun fichier'}), 400
        
        file = request.files['file']
        context_type = request.form.get('context_type')
        context_id = request.form.get('context_id')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Nom de fichier vide'}), 400
        
        # Sauvegarder le fichier et créer un message
        file_info = save_chat_file(file, session['user_id'], context_type, context_id)
        
        return jsonify({
            'success': True,
            'file_info': file_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Fonctions utilitaires
def get_recent_messages(context_type, context_id, limit=50):
    """Récupérer les messages récents"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                cm.*,
                u.name as user_name,
                u.email as user_email
            FROM chat_messages cm
            LEFT JOIN users u ON cm.user_id = u.id
            WHERE cm.context_type = %s AND cm.context_id = %s
            ORDER BY cm.created_at ASC
            LIMIT %s
        """, (context_type, context_id, limit))
        
        messages = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return messages
        
    except Exception as e:
        print(f"Erreur lors de la récupération des messages: {e}")
        return []

def save_chat_message(user_id, context_type, context_id, message, message_type='text'):
    """Sauvegarder un message de chat"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO chat_messages 
            (user_id, context_type, context_id, content, message_type, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (user_id, context_type, context_id, message, message_type))
        
        message_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        return message_id
        
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du message: {e}")
        return None

def mark_user_presence(user_id, context_type, context_id, is_active):
    """Marquer la présence d'un utilisateur"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if is_active:
            cursor.execute("""
                INSERT INTO chat_presence 
                (user_id, context_type, context_id, is_active, joined_at, last_seen)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                is_active = %s, last_seen = NOW()
            """, (user_id, context_type, context_id, is_active, is_active))
        else:
            cursor.execute("""
                UPDATE chat_presence 
                SET is_active = %s, last_seen = NOW()
                WHERE user_id = %s AND context_type = %s AND context_id = %s
            """, (is_active, user_id, context_type, context_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Erreur lors de la mise à jour de la présence: {e}")

def mark_user_offline(user_id):
    """Marquer un utilisateur comme hors ligne partout"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE chat_presence 
            SET is_active = 0, last_seen = NOW()
            WHERE user_id = %s
        """, (user_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Erreur lors de la mise hors ligne: {e}")

def get_user_name(user_id):
    """Récupérer le nom d'un utilisateur"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT name FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return user['name'] if user else 'Utilisateur inconnu'
        
    except Exception as e:
        print(f"Erreur lors de la récupération du nom: {e}")
        return 'Utilisateur inconnu'

def notify_offline_users(context_type, context_id, message_data):
    """Notifier les utilisateurs hors ligne (notifications push, email, etc.)"""
    # À implémenter selon les besoins de notification
    pass

def save_chat_file(file, user_id, context_type, context_id):
    """Sauvegarder un fichier uploadé dans le chat"""
    import os
    from werkzeug.utils import secure_filename
    
    try:
        # Créer le dossier s'il n'existe pas
        upload_folder = f"uploads/chat/{context_type}/{context_id}"
        os.makedirs(upload_folder, exist_ok=True)
        
        # Sécuriser le nom de fichier
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{filename}"
        
        file_path = os.path.join(upload_folder, safe_filename)
        file.save(file_path)
        
        # Sauvegarder l'info en base
        file_message = f"📎 Fichier partagé: {filename}"
        message_id = save_chat_message(user_id, context_type, context_id, file_message, 'file')
        
        # Retourner les infos du fichier
        return {
            'message_id': message_id,
            'filename': filename,
            'file_path': file_path,
            'file_size': os.path.getsize(file_path)
        }
        
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du fichier: {e}")
        raise e
