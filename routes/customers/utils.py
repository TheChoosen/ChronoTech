"""
Utilitaires et fonctions helper pour le module customers
"""

import pymysql
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import session, jsonify, request
from core.config import get_db_config
from core.utils import log_info, log_error, log_warning
from core.models import User
from core.database import log_activity


def get_db_connection():
    """Établit une connexion à la base de données MySQL"""
    try:
        config = get_db_config()
        return pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4',
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        log_error(f"Erreur connexion BDD: {e}")
        return None


def get_current_user():
    """Récupère l'utilisateur courant à partir de la session"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.find_by_id(user_id)


def require_role(*roles):
    """Décorateur pour contrôler l'accès basé sur les rôles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Authentification requise'}), 401
            if roles and user.role not in roles:
                return jsonify({'error': 'Accès refusé'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def log_customer_activity(customer_id, activity_type, title, description=None, 
                         reference_id=None, reference_table=None, actor_id=None):
    """Log une activité client dans la timeline"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        cursor = conn.cursor()
        
        # Utilisateur courant si non spécifié
        if not actor_id:
            user = get_current_user()
            actor_id = user.id if user else None
        
        # Métadonnées contextuelles
        metadata = {
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
            'timestamp': datetime.now().isoformat()
        }
        
        cursor.execute("""
            INSERT INTO customer_activity 
            (customer_id, activity_type, title, description, reference_id, reference_table, actor_id, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, [
            customer_id, activity_type, title, description, 
            reference_id, reference_table, actor_id, json.dumps(metadata)
        ])
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        log_error(f"Erreur log activité client: {e}")
        return False


def format_time_ago(timestamp):
    """Formate un timestamp en format 'il y a X temps'"""
    if not timestamp:
        return "Date inconnue"
    
    now = datetime.now()
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    diff = now - timestamp
    
    if diff.days > 0:
        return f"il y a {diff.days} jour{'s' if diff.days > 1 else ''}"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"il y a {hours} heure{'s' if hours > 1 else ''}"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"il y a {minutes} minute{'s' if minutes > 1 else ''}"
    else:
        return "à l'instant"


class MiniPagination:
    """Classe simple pour la pagination"""
    def __init__(self, page=1, per_page=20, total=0):
        self.page = page
        self.per_page = per_page
        self.total = total
        
    @property
    def has_prev(self):
        return self.page > 1
        
    @property
    def prev_num(self):
        return self.page - 1 if self.has_prev else None
        
    @property
    def has_next(self):
        return self.page < self.pages
        
    @property
    def next_num(self):
        return self.page + 1 if self.has_next else None
        
    @property
    def pages(self):
        return -(-self.total // self.per_page)  # Division ceiling
        
    @property
    def offset(self):
        return (self.page - 1) * self.per_page


def _debug(msg):
    """Fonction debug helper"""
    if __debug__:
        log_info(f"DEBUG: {msg}")
