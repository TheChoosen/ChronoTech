#!/usr/bin/env python3
"""
WebSocket Server pour ChronoChat - Temps réel
Implémentation Flask-SocketIO pour chat en temps réel
"""

from flask import Flask, request, session
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import mysql.connector
from datetime import datetime
import json
import os

# Configuration de l'application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'chronotech_websocket_secret_key_2025'

# Configuration SocketIO avec support CORS
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='eventlet',
                   logger=True,
                   engineio_logger=True)

# Configuration base de données
DB_CONFIG = {
    'host': '192.168.50.101',
    'user': 'gsicloud',
    'password': 'TCOChoosenOne204$',
    'database': 'bdm',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

# Stockage des connexions actives
active_connections = {}
user_rooms = {}

def get_db_connection():
    """Créer une connexion à la base de données"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as e:
        print(f"Erreur de connexion DB: {e}")
        return None

def log_chat_message(user_id, username, message, recipient_type, recipient_id, room_name):
    """Enregistrer le message dans la base de données"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        cursor = conn.cursor()
        
        # Déterminer le type de destinataire
        if recipient_type == 'user':
            recipient_user_id = recipient_id
            department_id = None
        elif recipient_type == 'department':
            recipient_user_id = None
            department_id = recipient_id
        else:  # general
            recipient_user_id = None
            department_id = None
            
        query = """
            INSERT INTO chat_messages 
            (user_id, username, message, recipient_user_id, department_id, room_name, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            user_id, username, message, recipient_user_id, 
            department_id, room_name, datetime.now()
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Erreur sauvegarde message: {e}")
        return False

def get_user_info(user_id):
    """Récupérer les informations d'un utilisateur"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
            
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, name, email, role, department FROM users WHERE id = %s"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return user
        
    except Exception as e:
        print(f"Erreur récupération utilisateur: {e}")
        return None

def get_departments():
    """Récupérer la liste des départements"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
            
        cursor = conn.cursor(dictionary=True)
        query = "SELECT DISTINCT department FROM users WHERE department IS NOT NULL AND department != ''"
        cursor.execute(query)
        departments = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return [dept['department'] for dept in departments]
        
    except Exception as e:
        print(f"Erreur récupération départements: {e}")
        return []

def get_users_by_department(department):
    """Récupérer les utilisateurs d'un département"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
            
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, name, email, role FROM users WHERE department = %s"
        cursor.execute(query, (department,))
        users = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return users
        
    except Exception as e:
        print(f"Erreur récupération utilisateurs département: {e}")
        return []

def update_user_presence(user_id, status='online'):
    """Mettre à jour la présence utilisateur"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        cursor = conn.cursor()
        query = """
            UPDATE user_presence 
            SET status = %s, last_activity = %s, updated_at = %s
            WHERE user_id = %s
        """
        
        cursor.execute(query, (status, datetime.now(), datetime.now(), user_id))
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Erreur mise à jour présence: {e}")
        return False

# Événements WebSocket

@socketio.on('connect')
def on_connect(auth):
    """Gestion de la connexion WebSocket"""
    print(f"Client connecté: {request.sid}")
    
    # Vérifier l'authentification
    user_id = request.args.get('user_id')
    username = request.args.get('username')
    
    if not user_id or not username:
        print("Connexion refusée - pas d'authentification")
        disconnect()
        return False
    
    # Enregistrer la connexion
    active_connections[request.sid] = {
        'user_id': int(user_id),
        'username': username,
        'connected_at': datetime.now()
    }
    
    # Mettre à jour la présence
    update_user_presence(user_id, 'online')
    
    # Rejoindre la room générale
    join_room('general')
    user_rooms[request.sid] = ['general']
    
    # Notifier les autres utilisateurs
    emit('user_connected', {
        'user_id': user_id,
        'username': username,
        'timestamp': datetime.now().isoformat()
    }, room='general', include_self=False)
    
    # Envoyer les informations initiales
    emit('connection_established', {
        'user_id': user_id,
        'username': username,
        'departments': get_departments(),
        'timestamp': datetime.now().isoformat()
    })
    
    print(f"Utilisateur connecté: {username} (ID: {user_id})")

@socketio.on('disconnect')
def on_disconnect():
    """Gestion de la déconnexion WebSocket"""
    print(f"Client déconnecté: {request.sid}")
    
    if request.sid in active_connections:
        user_info = active_connections[request.sid]
        user_id = user_info['user_id']
        username = user_info['username']
        
        # Mettre à jour la présence
        update_user_presence(user_id, 'offline')
        
        # Notifier les autres utilisateurs
        emit('user_disconnected', {
            'user_id': user_id,
            'username': username,
            'timestamp': datetime.now().isoformat()
        }, room='general', include_self=False)
        
        # Nettoyer les connexions
        del active_connections[request.sid]
        if request.sid in user_rooms:
            del user_rooms[request.sid]
        
        print(f"Utilisateur déconnecté: {username} (ID: {user_id})")

@socketio.on('join_room')
def on_join_room(data):
    """Rejoindre une room de chat"""
    room = data.get('room')
    if not room:
        return
    
    join_room(room)
    
    if request.sid in user_rooms:
        if room not in user_rooms[request.sid]:
            user_rooms[request.sid].append(room)
    else:
        user_rooms[request.sid] = [room]
    
    if request.sid in active_connections:
        username = active_connections[request.sid]['username']
        emit('room_joined', {
            'room': room,
            'username': username,
            'timestamp': datetime.now().isoformat()
        }, room=room)

@socketio.on('leave_room')
def on_leave_room(data):
    """Quitter une room de chat"""
    room = data.get('room')
    if not room:
        return
    
    leave_room(room)
    
    if request.sid in user_rooms and room in user_rooms[request.sid]:
        user_rooms[request.sid].remove(room)
    
    if request.sid in active_connections:
        username = active_connections[request.sid]['username']
        emit('room_left', {
            'room': room,
            'username': username,
            'timestamp': datetime.now().isoformat()
        }, room=room)

@socketio.on('send_message')
def on_send_message(data):
    """Envoyer un message de chat"""
    if request.sid not in active_connections:
        emit('error', {'message': 'Non authentifié'})
        return
    
    user_info = active_connections[request.sid]
    user_id = user_info['user_id']
    username = user_info['username']
    
    message = data.get('message', '').strip()
    recipient_type = data.get('recipient_type', 'general')  # general, user, department
    recipient_id = data.get('recipient_id')
    
    if not message:
        emit('error', {'message': 'Message vide'})
        return
    
    # Déterminer la room
    if recipient_type == 'user':
        room_name = f"user_{min(user_id, recipient_id)}_{max(user_id, recipient_id)}"
    elif recipient_type == 'department':
        room_name = f"dept_{recipient_id}"
    else:
        room_name = 'general'
    
    # Sauvegarder en base
    if log_chat_message(user_id, username, message, recipient_type, recipient_id, room_name):
        # Créer le message à diffuser
        message_data = {
            'user_id': user_id,
            'username': username,
            'message': message,
            'recipient_type': recipient_type,
            'recipient_id': recipient_id,
            'room_name': room_name,
            'timestamp': datetime.now().isoformat()
        }
        
        # Diffuser le message
        if recipient_type == 'user':
            # Message privé - seulement aux participants
            emit('new_message', message_data, room=room_name)
        elif recipient_type == 'department':
            # Message de département
            emit('new_message', message_data, room=room_name)
        else:
            # Message général
            emit('new_message', message_data, room='general')
        
        print(f"Message envoyé par {username}: {message[:50]}...")
    else:
        emit('error', {'message': 'Erreur sauvegarde message'})

@socketio.on('get_departments')
def on_get_departments():
    """Récupérer la liste des départements"""
    departments = get_departments()
    emit('departments_list', {'departments': departments})

@socketio.on('get_users_by_department')
def on_get_users_by_department(data):
    """Récupérer les utilisateurs d'un département"""
    department = data.get('department')
    if not department:
        emit('error', {'message': 'Département non spécifié'})
        return
    
    users = get_users_by_department(department)
    emit('department_users', {
        'department': department,
        'users': users
    })

@socketio.on('typing_start')
def on_typing_start(data):
    """Utilisateur commence à taper"""
    if request.sid not in active_connections:
        return
    
    user_info = active_connections[request.sid]
    room = data.get('room', 'general')
    
    emit('user_typing', {
        'user_id': user_info['user_id'],
        'username': user_info['username'],
        'typing': True
    }, room=room, include_self=False)

@socketio.on('typing_stop')
def on_typing_stop(data):
    """Utilisateur arrête de taper"""
    if request.sid not in active_connections:
        return
    
    user_info = active_connections[request.sid]
    room = data.get('room', 'general')
    
    emit('user_typing', {
        'user_id': user_info['user_id'],
        'username': user_info['username'],
        'typing': False
    }, room=room, include_self=False)

@socketio.on('heartbeat')
def on_heartbeat():
    """Battement de cœur pour maintenir la connexion"""
    if request.sid in active_connections:
        user_id = active_connections[request.sid]['user_id']
        update_user_presence(user_id, 'online')
        emit('heartbeat_ack', {'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    print("🚀 Démarrage du serveur WebSocket ChronoChat...")
    print("📡 WebSocket Server - Port 5001")
    print("🔗 Connexion BDD: 192.168.50.101")
    print("🌐 CORS autorisé pour tous les domaines")
    
    # Démarrer le serveur
    socketio.run(app, 
                host='0.0.0.0', 
                port=5001, 
                debug=True,
                allow_unsafe_werkzeug=True)
