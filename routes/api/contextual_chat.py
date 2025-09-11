from flask import Blueprint, request, session, jsonify, current_app
from flask_socketio import emit, join_room, leave_room
from datetime import datetime
import os
from core.database import get_db_connection
from utils import token_required

contextual_chat_bp = Blueprint('contextual_chat', __name__)

# Fonctions utilitaires
def update_user_presence(user_id, context_type, context_id, is_active):
    """Mettre à jour la présence d'un utilisateur"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insérer ou mettre à jour la présence
        cursor.execute("""
            INSERT INTO chat_presence (user_id, context_type, context_id, is_active, last_seen)
            VALUES (%s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE 
                is_active = %s, 
                last_seen = NOW()
        """, (user_id, context_type, context_id, is_active, is_active))
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Erreur lors de la mise à jour de la présence: {e}")

# Socket.IO Events
def init_socketio_events(socketio):
    """Initialiser les événements Socket.IO pour le chat"""
    
    @socketio.on('join_chat')
    def on_join_chat(data):
        """Rejoindre une conversation contextuelle"""
        try:
            user_id = session.get('user_id')
            if not user_id:
                return
            
            context_type = data.get('context_type')  # 'work_order', 'intervention', 'customer'
            context_id = data.get('context_id')
            
            if not context_type or not context_id:
                emit('error', {'message': 'Contexte invalide'})
                return
            
            room_name = f"{context_type}_{context_id}"
            join_room(room_name)
            
            # Marquer l'utilisateur comme actif dans ce contexte
            update_user_presence(user_id, context_type, context_id, True)
            
            # Notifier les autres utilisateurs
            emit('user_joined', {
                'user_id': user_id,
                'user_name': get_user_name(user_id)
            }, room=room_name, include_self=False)
            
        except Exception as e:
            print(f"Erreur dans join_chat: {e}")
    
    @socketio.on('leave_chat')
    def on_leave_chat(data):
        """Quitter une conversation"""
        try:
            user_id = session.get('user_id')
            if not user_id:
                return
            
            context_type = data.get('context_type')
            context_id = data.get('context_id')
            
            room_name = f"{context_type}_{context_id}"
            leave_room(room_name)
            
            # Marquer l'utilisateur comme inactif
            update_user_presence(user_id, context_type, context_id, False)
            
            # Notifier les autres utilisateurs
            emit('user_left', {
                'user_id': user_id,
                'user_name': get_user_name(user_id)
            }, room=room_name, include_self=False)
            
        except Exception as e:
            print(f"Erreur dans leave_chat: {e}")
    
    @socketio.on('send_message')
    def on_send_message(data):
        """Envoyer un message dans le chat"""
        try:
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
                
        except Exception as e:
            print(f"Erreur dans send_message: {e}")
    
    @socketio.on('typing_start')
    def on_typing_start(data):
        """Utilisateur commence à taper"""
        try:
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
            
        except Exception as e:
            print(f"Erreur dans typing_start: {e}")
    
    @socketio.on('typing_stop')
    def on_typing_stop(data):
        """Utilisateur arrête de taper"""
        try:
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
            
        except Exception as e:
            print(f"Erreur dans typing_stop: {e}")
    
    @socketio.on('disconnect')
    def on_disconnect():
        """Gérer la déconnexion"""
        try:
            user_id = session.get('user_id')
            if user_id:
                # Marquer l'utilisateur comme hors ligne dans tous les contextes
                mark_user_offline(user_id)
        except Exception as e:
            print(f"Erreur dans disconnect: {e}")

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
        
        return user['name'] if user else f"Utilisateur {user_id}"
        
    except Exception as e:
        print(f"Erreur lors de la récupération du nom utilisateur: {e}")
        return f"Utilisateur {user_id}"

def save_chat_message(user_id, context_type, context_id, message, message_type='text'):
    """Sauvegarder un message de chat"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO chat_messages 
            (user_id, context_type, context_id, message, message_type, created_at)
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

def save_uploaded_file(file, user_id, context_type, context_id):
    """Sauvegarder un fichier uploadé"""
    try:
        # Créer le dossier d'upload s'il n'existe pas
        upload_folder = os.path.join(current_app.root_path, 'uploads', 'chat')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Générer un nom de fichier sécurisé
        filename = file.filename
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
            'messages': messages[::-1],  # Inverser pour avoir l'ordre chronologique
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
            'error': f'Erreur lors de la récupération des messages: {str(e)}'
        }), 500

@contextual_chat_bp.route('/contexts/<context_type>/<int:context_id>/presence', methods=['GET'])
@token_required
def get_chat_presence(context_type, context_id):
    """Récupérer la liste des utilisateurs présents"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                cp.*,
                u.name as user_name,
                u.email as user_email
            FROM chat_presence cp
            LEFT JOIN users u ON cp.user_id = u.id
            WHERE cp.context_type = %s 
                AND cp.context_id = %s 
                AND cp.is_active = 1
                AND cp.last_seen > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
        """, (context_type, context_id))
        
        presence = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'presence': presence
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur lors de la récupération de la présence: {str(e)}'
        }), 500

@contextual_chat_bp.route('/contexts/<context_type>/<int:context_id>/upload', methods=['POST'])
@token_required
def upload_chat_file(context_type, context_id):
    """Upload un fichier dans le chat"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Aucun fichier fourni'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nom de fichier vide'
            }), 400
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Non authentifié'
            }), 401
        
        # Sauvegarder le fichier
        file_info = save_uploaded_file(file, user_id, context_type, context_id)
        
        return jsonify({
            'success': True,
            'file_info': file_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur lors de l\'upload: {str(e)}'
        }), 500
