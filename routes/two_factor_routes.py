"""
Routes pour l'authentification à deux facteurs
Sprint 6 - Tâche #41
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from core.security import login_required
from core.two_factor_auth import (
    generate_2fa_qr_code, setup_user_2fa, verify_2fa_token,
    disable_user_2fa
)
from core.database import db_manager
import mysql.connector.cursor

two_factor_bp = Blueprint('two_factor', __name__)

@two_factor_bp.route('/2fa/setup')
@login_required
def setup_2fa():
    """Page de configuration 2FA"""
    user_id = session.get('user_id')
    
    # Récupérer l'email de l'utilisateur
    conn = db_manager.get_connection()
    cursor = conn.cursor(cursor_class=mysql.connector.cursor.MySQLCursorDict)
    
    cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user:
        flash('Utilisateur non trouvé', 'error')
        return redirect(url_for('dashboard'))
    
    # Générer le secret et le QR code
    secret = setup_user_2fa(user_id)
    qr_code = generate_2fa_qr_code(user['email'], secret)
    
    return render_template('auth/setup_2fa.html', 
                         qr_code=qr_code,
                         secret=secret)

@two_factor_bp.route('/2fa/verify', methods=['GET', 'POST'])
@login_required
def verify_2fa():
    """Page de vérification 2FA"""
    if request.method == 'POST':
        token = request.form.get('token')
        user_id = session.get('user_id')
        
        # Récupérer le secret de l'utilisateur
        conn = db_manager.get_connection()
        cursor = conn.cursor(cursor_class=mysql.connector.cursor.MySQLCursorDict)
        
        cursor.execute("""
            SELECT two_factor_secret
            FROM users
            WHERE id = %s AND two_factor_enabled = TRUE
        """, (user_id,))
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user or not user['two_factor_secret']:
            flash('2FA non configurée', 'error')
            return redirect(url_for('two_factor.setup_2fa'))
        
        # Vérifier le token
        if verify_2fa_token(user['two_factor_secret'], token):
            session['two_factor_verified'] = True
            
            # Mettre à jour la base de données
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET two_factor_verified = TRUE
                WHERE id = %s
            """, (user_id,))
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Authentification 2FA réussie', 'success')
            
            # Rediriger vers l'URL demandée ou le dashboard
            redirect_url = session.pop('redirect_after_2fa', url_for('dashboard'))
            return redirect(redirect_url)
        else:
            flash('Code invalide. Veuillez réessayer.', 'error')
    
    return render_template('auth/verify_2fa.html')

@two_factor_bp.route('/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    """Désactiver la 2FA"""
    user_id = session.get('user_id')
    password = request.form.get('password')
    
    # Vérifier le mot de passe avant de désactiver
    # (implémentation simplifiée pour la démo)
    
    disable_user_2fa(user_id)
    session.pop('two_factor_verified', None)
    
    flash('Authentification 2FA désactivée', 'success')
    return redirect(url_for('dashboard'))

# API endpoints pour la 2FA
@two_factor_bp.route('/api/2fa/status')
@login_required
def get_2fa_status():
    """Obtenir le statut 2FA de l'utilisateur"""
    user_id = session.get('user_id')
    
    conn = db_manager.get_connection()
    cursor = conn.cursor(cursor_class=mysql.connector.cursor.MySQLCursorDict)
    
    cursor.execute("""
        SELECT two_factor_enabled, two_factor_verified
        FROM users
        WHERE id = %s
    """, (user_id,))
    
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return jsonify({
        'enabled': bool(user and user['two_factor_enabled']),
        'verified': bool(user and user['two_factor_verified'])
    })
