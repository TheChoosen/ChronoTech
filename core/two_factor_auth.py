"""
Module d'authentification à deux facteurs (2FA)
Sprint 6 - Tâche #41
"""
import pyotp
import qrcode
import io
import base64
from functools import wraps
from flask import session, redirect, url_for, flash, request, render_template
from core.database import db_manager

def generate_2fa_secret():
    """Générer un secret pour l'authentification 2FA"""
    return pyotp.random_base32()

def generate_2fa_qr_code(user_email, secret):
    """Générer un QR code pour configurer l'authentification 2FA"""
    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user_email,
        issuer_name='ChronoTech'
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    
    return base64.b64encode(buf.getvalue()).decode()

def verify_2fa_token(secret, token):
    """Vérifier un token 2FA"""
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)

def two_factor_required(f):
    """
    Décorateur pour exiger l'authentification 2FA
    Tâche #41 - Sprint 6
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Vérifier si l'utilisateur est connecté
        if 'user_id' not in session:
            flash('Veuillez vous connecter', 'warning')
            return redirect(url_for('login'))
        
        # Vérifier si l'utilisateur a un rôle admin
        if session.get('role') != 'admin':
            # 2FA obligatoire uniquement pour les admins
            return f(*args, **kwargs)
        
        # Vérifier si la 2FA est configurée pour cet utilisateur
        conn = db_manager.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT two_factor_enabled, two_factor_verified
            FROM users
            WHERE id = %s
        """, (session['user_id'],))
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            flash('Utilisateur non trouvé', 'error')
            return redirect(url_for('logout'))
        
        # Si 2FA n'est pas activée, rediriger vers la configuration
        if not user.get('two_factor_enabled'):
            flash('Configuration 2FA requise pour les administrateurs', 'warning')
            return redirect(url_for('two_factor.setup_2fa'))
        
        # Si 2FA n'est pas vérifiée pour cette session
        if not session.get('two_factor_verified'):
            session['redirect_after_2fa'] = request.url
            return redirect(url_for('two_factor.verify_2fa'))
        
        return f(*args, **kwargs)
    
    return decorated_function

def setup_user_2fa(user_id):
    """Configurer la 2FA pour un utilisateur"""
    secret = generate_2fa_secret()
    
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE users
        SET two_factor_secret = %s,
            two_factor_enabled = TRUE
        WHERE id = %s
    """, (secret, user_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return secret

def disable_user_2fa(user_id):
    """Désactiver la 2FA pour un utilisateur"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE users
        SET two_factor_secret = NULL,
            two_factor_enabled = FALSE,
            two_factor_verified = FALSE
        WHERE id = %s
    """, (user_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
