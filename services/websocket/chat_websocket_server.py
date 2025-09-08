"""
Serveur WebSocket pour le chat en temps réel ChronoTech
"""
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from datetime import datetime
import json
import os
import sys

# Ajouter le répertoire parent au path pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db_connection

# Configuration Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'chronotech_websocket_secret_key_2025'

# Configuration SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Variables globales pour suivre les utilisateurs connectés
connected_users = {}  # {session_id: {user_id, username, channel}}
user_sessions = {}    # {user_id: [session_ids]}

def save_message_to_db(user_id, channel, message, message_type='text', file_id=None):
    """Sauvegarder un message dans la base de données"""
    try:
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
        
        return message_id
        
    except Exception as e:
        print(f"Erreur sauvegarde message: {e}")
        return None

def update_user_status(user_id, status='online'):
    """Mettre à jour le statut d'un utilisateur"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute("""
            UPDATE users SET status = %s WHERE id = %s
        """, (status, user_id))
        
        db.commit()
        cursor.close()
        db.close()
        
    except Exception as e:
        print(f"Erreur mise à jour statut: {e}")

@socketio.on('connect')
def handle_connect():
    """Gestion de la connexion d'un client"""
    print(f'Client connecté: {request.sid}')
    emit('connect_response', {
        'status': 'connected',
        'session_id': request.sid,
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Gestion de la déconnexion d'un client"""
    session_id = request.sid
    print(f'Client déconnecté: {session_id}')
    
    # Nettoyer les données de session
    if session_id in connected_users:
        user_data = connected_users[session_id]
        user_id = user_data.get('user_id')
        username = user_data.get('username')
        channel = user_data.get('channel')
        
        # Supprimer de la liste des connectés
        del connected_users[session_id]
        
        # Mettre à jour la liste des sessions utilisateur
        if user_id in user_sessions:
            if session_id in user_sessions[user_id]:
                user_sessions[user_id].remove(session_id)
            
            # Si plus de sessions actives, marquer comme offline
            if not user_sessions[user_id]:
                update_user_status(user_id, 'offline')
                del user_sessions[user_id]
        
        # Notifier les autres utilisateurs du canal
        if channel:
            emit('user_left', {
                'user_id': user_id,
                'username': username,
                'timestamp': datetime.now().isoformat()
            }, room=channel)

@socketio.on('join')
def handle_join(data):
    """Gestion de l'entrée dans un canal"""
    try:
        user_id = data.get('user_id')
        username = data.get('username')
        channel = data.get('channel')
        
        if not all([user_id, username, channel]):
            emit('error', {'message': 'Données manquantes pour rejoindre le canal'})
            return
        
        session_id = request.sid
        
        # Quitter l'ancien canal si nécessaire
        if session_id in connected_users:
            old_channel = connected_users[session_id].get('channel')
            if old_channel and old_channel != channel:
                leave_room(old_channel)
                emit('user_left', {
                    'user_id': user_id,
                    'username': username,
                    'timestamp': datetime.now().isoformat()
                }, room=old_channel)
        
        # Rejoindre le nouveau canal
        join_room(channel)
        
        # Mettre à jour les données de session
        connected_users[session_id] = {
            'user_id': user_id,
            'username': username,
            'channel': channel
        }
        
        # Ajouter à la liste des sessions utilisateur
        if user_id not in user_sessions:
            user_sessions[user_id] = []
        if session_id not in user_sessions[user_id]:
            user_sessions[user_id].append(session_id)
        
        # Mettre à jour le statut utilisateur
        update_user_status(user_id, 'online')
        
        print(f'Utilisateur {username} (ID: {user_id}) a rejoint le canal {channel}')
        
        # Notifier les autres utilisateurs
        emit('user_joined', {
            'user_id': user_id,
            'username': username,
            'channel': channel,
            'timestamp': datetime.now().isoformat()
        }, room=channel, include_self=False)
        
        # Confirmer la jointure
        emit('join_success', {
            'channel': channel,
            'message': f'Vous avez rejoint le canal #{channel}'
        })
        
    except Exception as e:
        print(f"Erreur lors de la jointure: {e}")
        emit('error', {'message': 'Erreur lors de la jointure du canal'})

@socketio.on('leave')
def handle_leave(data):
    """Gestion de la sortie d'un canal"""
    try:
        user_id = data.get('user_id')
        username = data.get('username')
        channel = data.get('channel')
        
        session_id = request.sid
        
        if channel:
            leave_room(channel)
            
            # Notifier les autres utilisateurs
            emit('user_left', {
                'user_id': user_id,
                'username': username,
                'timestamp': datetime.now().isoformat()
            }, room=channel)
            
            print(f'Utilisateur {username} a quitté le canal {channel}')
        
    except Exception as e:
        print(f"Erreur lors de la sortie: {e}")

@socketio.on('message')
def handle_message(data):
    """Gestion d'un nouveau message"""
    try:
        user_id = data.get('user_id')
        username = data.get('username')
        channel = data.get('channel')
        message = data.get('message')
        message_type = data.get('type', 'text')
        file_id = data.get('file_id')
        
        if not all([user_id, username, channel]):
            emit('error', {'message': 'Données manquantes pour le message'})
            return
        
        # Sauvegarder dans la base de données
        message_id = save_message_to_db(user_id, channel, message, message_type, file_id)
        
        if message_id:
            # Préparer les données du message
            message_data = {
                'id': message_id,
                'user_id': user_id,
                'username': username,
                'channel': channel,
                'message': message,
                'type': message_type,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'file_id': file_id
            }
            
            # Diffuser aux autres utilisateurs du canal
            emit('new_message', message_data, room=channel)
            
            print(f'Message envoyé par {username} dans #{channel}: {message_type}')
        else:
            emit('error', {'message': 'Erreur lors de la sauvegarde du message'})
            
    except Exception as e:
        print(f"Erreur lors de l'envoi du message: {e}")
        emit('error', {'message': 'Erreur lors de l\'envoi du message'})

@socketio.on('typing')
def handle_typing(data):
    """Gestion de l'indicateur de frappe"""
    try:
        user_id = data.get('user_id')
        username = data.get('username')
        channel = data.get('channel')
        
        if channel:
            # Diffuser l'indicateur de frappe aux autres utilisateurs
            emit('user_typing', {
                'user_id': user_id,
                'username': username,
                'timestamp': datetime.now().isoformat()
            }, room=channel, include_self=False)
            
    except Exception as e:
        print(f"Erreur indicateur frappe: {e}")

@socketio.on('get_online_users')
def handle_get_online_users(data):
    """Récupérer la liste des utilisateurs en ligne dans un canal"""
    try:
        channel = data.get('channel')
        
        # Récupérer les utilisateurs connectés pour ce canal
        channel_users = []
        for session_id, user_data in connected_users.items():
            if user_data.get('channel') == channel:
                channel_users.append({
                    'user_id': user_data.get('user_id'),
                    'username': user_data.get('username')
                })
        
        emit('online_users_list', {
            'channel': channel,
            'users': channel_users,
            'count': len(channel_users)
        })
        
    except Exception as e:
        print(f"Erreur récupération utilisateurs en ligne: {e}")

@app.route('/health')
def health_check():
    """Point de contrôle de santé du serveur WebSocket"""
    return {
        'status': 'healthy',
        'service': 'ChronoTech WebSocket Chat Server',
        'connected_users': len(connected_users),
        'active_users': len(user_sessions),
        'timestamp': datetime.now().isoformat()
    }

if __name__ == '__main__':
    print("🚀 Démarrage du serveur WebSocket ChronoTech Chat")
    print("📡 Port: 5001")
    print("🔗 URL: http://localhost:5001")
    
    # Créer les dossiers d'upload si nécessaire
    os.makedirs('uploads/chat_files', exist_ok=True)
    os.makedirs('uploads/chat_voice', exist_ok=True)
    
    try:
        socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"❌ Erreur démarrage serveur: {e}")
