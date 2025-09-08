"""
Module d'authentification pour ChronoTech
"""
from flask import session, flash, redirect, url_for
from functools import wraps

def login_required(f):
    """Décorateur pour protéger les routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('auth_login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    """Décorateur pour vérifier les rôles utilisateur"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session or session['user_role'] not in allowed_roles:
                flash('Accès non autorisé.', 'danger')
                return redirect(url_for('auth_login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
