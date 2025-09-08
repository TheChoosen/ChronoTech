"""
Configuration de sécurité centralisée pour ChronoTech
Sprint 1 - Security Hardening
Sprint 3 - Client Portal Security
"""
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import secrets

# Import Sprint 3 client security functions
try:
    from core.client_security import generate_client_token, verify_client_token, generate_secure_link
except ImportError:
    # Fallback si pas encore créé
    def generate_client_token(work_order_id):
        return None
    def verify_client_token(work_order_id, token):
        return False
    def generate_secure_link(work_order_id):
        return None

class SecurityConfig:
    """Configuration centralisée des mesures de sécurité"""
    
    # CSRF Protection
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(32))
    WTF_CSRF_TIME_LIMIT = 3600  # 1 heure
    WTF_CSRF_SSL_STRICT = False  # Mettre True en production HTTPS
    
    # Session Security
    SESSION_COOKIE_SECURE = False  # Mettre True en production HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 7200  # 2 heures
    
    # Rate Limiting Configuration
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Content Security Policy - Version corrigée pour FontAwesome et Socket.io
    CSP_HEADER = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://kit.fontawesome.com https://*.fontawesome.com https://cdn.socket.io",
        'style-src': "'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://*.fontawesome.com",
        'font-src': "'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com https://*.fontawesome.com data:",
        'img-src': "'self' data: https:",
        'connect-src': "'self' https://*.fontawesome.com wss: ws:",
        'frame-src': "'none'",
        'object-src': "'none'",
        'base-uri': "'self'",
        'form-action': "'self'"
    }
    
    # File Upload Security
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {
        'images': {'png', 'jpg', 'jpeg', 'gif'},
        'videos': {'mp4', 'mov'},
        'audio': {'mp3', 'wav'},
        'documents': {'pdf', 'txt', 'doc', 'docx'}
    }

def init_security(app):
    """Initialiser toutes les mesures de sécurité"""
    
    # Configuration Flask
    app.config.update(
        SECRET_KEY=SecurityConfig.SECRET_KEY,
        WTF_CSRF_TIME_LIMIT=SecurityConfig.WTF_CSRF_TIME_LIMIT,
        WTF_CSRF_SSL_STRICT=SecurityConfig.WTF_CSRF_SSL_STRICT,
        SESSION_COOKIE_SECURE=SecurityConfig.SESSION_COOKIE_SECURE,
        SESSION_COOKIE_HTTPONLY=SecurityConfig.SESSION_COOKIE_HTTPONLY,
        SESSION_COOKIE_SAMESITE=SecurityConfig.SESSION_COOKIE_SAMESITE,
        PERMANENT_SESSION_LIFETIME=SecurityConfig.PERMANENT_SESSION_LIFETIME,
        MAX_CONTENT_LENGTH=SecurityConfig.MAX_CONTENT_LENGTH
    )
    
    # CSRF Protection
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Rate Limiting
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[SecurityConfig.RATELIMIT_DEFAULT],
        storage_uri=SecurityConfig.RATELIMIT_STORAGE_URL
    )
    limiter.init_app(app)
    
    # Content Security Policy
    @app.after_request
    def set_security_headers(response):
        # CSP Header - Réactivé avec support FontAwesome
        csp_value = '; '.join([f"{key} {value}" for key, value in SecurityConfig.CSP_HEADER.items()])
        response.headers['Content-Security-Policy'] = csp_value
        
        # Security Headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        
        return response
    
    # CSRF Error Handler
    @app.errorhandler(400)
    def csrf_error(e):
        from flask import jsonify, request
        import logging
        
        if 'csrf' in str(e).lower():
            logging.getLogger('security').warning(f"CSRF Error: {str(e)} - IP: {get_remote_address()}")
            
            if request.is_json:
                return jsonify({'error': 'Token CSRF invalide ou manquant'}), 400
            else:
                from flask import flash, redirect, url_for
                flash('Session expirée, veuillez réessayer', 'error')
                return redirect(url_for('index'))
        return e
    
    return csrf, limiter

def get_csrf_token():
    """Générer un token CSRF pour les templates"""
    from flask_wtf.csrf import generate_csrf
    return generate_csrf()

# Décorateurs de sécurité réutilisables
def security_headers(f):
    """Décorateur pour ajouter des headers de sécurité spécifiques"""
    from functools import wraps
    from flask import make_response
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return decorated_function

def audit_log(action):
    """Décorateur pour logger les actions sensibles"""
    from functools import wraps
    from flask import session, request
    import logging
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id', 'anonymous')
            ip = get_remote_address()
            
            logging.getLogger('security').info(
                f"AUDIT: User {user_id} from {ip} performed {action} on {request.endpoint}"
            )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
