"""
Routes pour la gestion du dashboard et widgets
"""
from flask import Blueprint, render_template, session, redirect, url_for
from .widgets_api import widgets_bp

# Créer le blueprint principal
bp = Blueprint('dashboard', __name__)

# Enregistrer les routes API des widgets
bp.register_blueprint(widgets_bp, url_prefix='/api')

@bp.route('/')
def dashboard():
    """Page principale du dashboard"""
    if 'user_id' not in session:
        return redirect(url_for('auth_login'))
    
    return render_template('dashboard/main.html',
                         user_name=session.get('user_name', 'Utilisateur'),
                         user_role=session.get('user_role', 'technician'))

@bp.route('/customize')
def customize_dashboard():
    """Page de personnalisation du dashboard"""
    if 'user_id' not in session:
        return redirect(url_for('auth_login'))
    
    return render_template('dashboard/customize.html',
                         user_name=session.get('user_name', 'Utilisateur'),
                         user_role=session.get('user_role', 'technician'))
