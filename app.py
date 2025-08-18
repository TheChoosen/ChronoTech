"""
ChronoTech - Module Interventions & Travaux (v2.0)
Application Flask principale basée sur le PRD Fusionné
Architecture moderne avec design Claymorphism et intégration IA
"""
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import os
import logging
from datetime import datetime, timedelta
import pymysql
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import json
from functools import wraps

# Import des modules ChronoTech
from core.config import Config
from core.database import db_manager, setup_database, migrate_database, seed_database, log_activity, is_database_ready, quick_db_test
from core.models import User, Customer, WorkOrder, WorkOrderLine, InterventionNote, InterventionMedia, Notification
from core.models import get_dashboard_stats, get_recent_activities
from core.utils import (
    validate_work_order_data, validate_user_data, validate_file_upload,
    generate_claim_number, hash_password, verify_password, init_template_filters,
    setup_upload_folders, ValidationError, FileUploadError, sanitize_html
)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    """Factory pattern pour créer l'application Flask"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialisation des composants
    init_template_filters(app)
    setup_upload_folders(app.root_path)
    
    # Configuration de la base de données
    with app.app_context():
        try:
            logger.info("Vérification de la base de données...")
            
            # Test de connexion ultra-rapide
            quick_test = quick_db_test()
            if quick_test == "ready":
                logger.info("✅ Base de données prête - aucune configuration nécessaire")
            elif quick_test == "accessible":
                logger.info("Base de données accessible - vérification de la structure...")
                setup_database()
                migrate_database()
                logger.info("✅ Base de données configurée avec succès")
            else:
                logger.warning("⚠️ Base de données non accessible - mode autonome activé")
                logger.info("L'application fonctionnera sans fonctionnalités de base de données")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
            logger.warning("⚠️ Démarrage en mode autonome sans base de données")
            logger.info("L'application sera accessible mais limitée")
    
    return app


# Création de l'application
app = create_app()

# Filtre Jinja pour badge type client
def customer_type_badge(value):
    if value == 'entreprise':
        return 'bg-primary'
    elif value == 'particulier':
        return 'bg-success'
    return 'bg-secondary'
app.jinja_env.filters['customer_type_badge'] = customer_type_badge

# Utilitaires
def get_db_connection():
    """Connexion à la base de données MySQL - Wrapper pour compatibilité"""
    try:
        conn = db_manager.get_connection()
        if conn is None:
            raise ConnectionError("Impossible de se connecter à la base de données")
        return conn
    except Exception as e:
        logger.error(f"Erreur lors de l'obtention de la connexion DB: {e}")
        raise ConnectionError("Service de base de données temporairement indisponible")

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
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def allowed_file(filename):
    """Vérifier les extensions de fichiers autorisées - Wrapper pour compatibilité"""
    from core.utils import allowed_file as utils_allowed_file
    return utils_allowed_file(filename)

# Configuration des uploads - Pour compatibilité avec l'ancien code
UPLOAD_FOLDER = app.config.get('UPLOAD_FOLDER', 'static/uploads')
ALLOWED_EXTENSIONS = app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'mp3', 'wav', 'pdf'})

# Routes d'authentification
@app.route('/')
def index():
    """Page d'accueil - redirige vers dashboard si connecté"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def auth_login():
    """Connexion utilisateur"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, email, password, role 
                    FROM users 
                    WHERE email = %s
                """, (email,))
                user = cursor.fetchone()
                
                if user and check_password_hash(user['password'], password):
                    session['user_id'] = user['id']
                    session['user_name'] = user['name']
                    session['user_email'] = user['email']
                    session['user_role'] = user['role']
                    
                    # Enregistrer la connexion - Table user_activity_log non disponible temporairement
                    # cursor.execute("""
                    #     INSERT INTO user_activity_log (user_id, action, details)
                    #     VALUES (%s, 'login', %s)
                    # """, (user['id'], f"Connexion depuis {request.remote_addr}"))
                    # conn.commit()
                    
                    flash(f'Bienvenue {user["name"]} !', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Email ou mot de passe incorrect', 'error')
        finally:
            conn.close()
    
    return render_template('auth/login.html')

@app.route('/logout')
def auth_logout():
    """Déconnexion utilisateur"""
    if 'user_id' in session:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_activity_log (user_id, action, details)
                    VALUES (%s, 'logout', %s)
                """, (session['user_id'], f"Déconnexion depuis {request.remote_addr}"))
                conn.commit()
        finally:
            conn.close()
    
    session.clear()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('auth_login'))

# Routes principales
@app.route('/dashboard')
@login_required
def dashboard():
    """Tableau de bord principal avec vue personnalisée selon le rôle"""
    try:
        conn = get_db_connection()
        if conn is None:
            flash('Service de base de données temporairement indisponible', 'error')
            return render_template('dashboard/main.html', stats={}, recent_orders=[], error_message="Base de données indisponible")
            
        with conn.cursor() as cursor:
            user_role = session.get('user_role')
            user_id = session.get('user_id')
            
            # Statistiques générales
            stats = {}
            
            if user_role == 'technician':
                # Vue technicien : mes tâches du jour
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_assigned,
                        COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN priority = 'urgent' THEN 1 END) as urgent
                    FROM work_orders 
                    WHERE assigned_technician_id = %s 
                    AND status NOT IN ('completed', 'cancelled')
                """, (user_id,))
                stats['my_tasks'] = cursor.fetchone()
                
                # Mes interventions du jour
                cursor.execute("""
                    SELECT wo.*, c.name as customer_name,
                           CASE 
                               WHEN wo.scheduled_date IS NOT NULL THEN wo.scheduled_date
                               ELSE wo.created_at
                           END as task_date
                    FROM work_orders wo
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    WHERE wo.assigned_technician_id = %s
                    AND wo.status NOT IN ('completed', 'cancelled')
                    AND DATE(COALESCE(wo.scheduled_date, wo.created_at)) = CURDATE()
                    ORDER BY wo.priority DESC, task_date ASC
                """, (user_id,))
                my_tasks_today = cursor.fetchall()
                
            else:
                # Vue superviseur/admin : vue d'ensemble
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_orders,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                        COUNT(CASE WHEN priority = 'urgent' THEN 1 END) as urgent,
                        COUNT(CASE WHEN assigned_technician_id IS NULL THEN 1 END) as unassigned
                    FROM work_orders 
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                """)
                stats['overview'] = cursor.fetchone()
                
                # Interventions récentes
                cursor.execute("""
                    SELECT wo.*, u.name as technician_name, c.name as customer_name
                    FROM work_orders wo
                    LEFT JOIN users u ON wo.assigned_technician_id = u.id
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    ORDER BY wo.updated_at DESC
                    LIMIT 10
                """)
                recent_orders = cursor.fetchall()
                my_tasks_today = recent_orders
            
            # Notifications non lues
            cursor.execute("""
                SELECT * FROM notifications 
                WHERE user_id = %s AND is_read = 0
                ORDER BY created_at DESC
                LIMIT 5
            """, (user_id,))
            notifications = cursor.fetchall()
            
            return render_template('dashboard/main.html', 
                                 stats=stats, 
                                 recent_orders=recent_orders,
                                 user_role=user_role)
                                 
    except ConnectionError as e:
        logger.error(f"Erreur de connexion dans dashboard: {e}")
        flash('Service de base de données temporairement indisponible', 'error')
        return render_template('dashboard/main.html', stats={}, recent_orders=[], error_message="Base de données indisponible")
    except Exception as e:
        logger.error(f"Erreur dans dashboard: {e}")
        flash('Une erreur inattendue s\'est produite', 'error')
        return render_template('dashboard/main.html', stats={}, recent_orders=[], error_message="Erreur système")
    finally:
        if conn:
            conn.close()

# Routes pour le profil utilisateur et paramètres
@app.route('/profile')
@login_required
def user_profile():
    """Page de profil utilisateur"""
    try:
        conn = get_db_connection()
        if conn is None:
            flash('Service de base de données temporairement indisponible', 'error')
            return redirect(url_for('dashboard'))
            
        with conn.cursor() as cursor:
            # Récupérer les informations complètes de l'utilisateur
            cursor.execute("""
                SELECT id, name, email, role, is_active
                FROM users 
                WHERE id = %s
            """, (session.get('user_id'),))
            
            user = cursor.fetchone()
            if not user:
                flash('Utilisateur non trouvé', 'error')
                return redirect(url_for('dashboard'))
            
            # Statistiques de l'utilisateur si c'est un technicien
            user_stats = {}
            if user.get('role') in ['technician', 'supervisor']:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_work_orders,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
                        SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as current_orders
                    FROM work_orders 
                    WHERE assigned_to = %s
                """, (user['id'],))
                user_stats = cursor.fetchone() or {}
                
        return render_template('profile/index.html', user=user, stats=user_stats)
        
    except Exception as e:
        logger.error(f"Erreur profil utilisateur: {e}")
        flash('Erreur lors du chargement du profil', 'error')
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Modifier le profil utilisateur"""
    try:
        conn = get_db_connection()
        if conn is None:
            flash('Service de base de données temporairement indisponible', 'error')
            return redirect(url_for('user_profile'))
            
        if request.method == 'POST':
            # Traitement de la modification du profil
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            
            if not full_name or not email:
                flash('Le nom complet et l\'email sont obligatoires', 'error')
                return redirect(url_for('edit_profile'))
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users 
                    SET name = %s, email = %s
                    WHERE id = %s
                """, (full_name, email, session.get('user_id')))
                
                conn.commit()
                
                # Mettre à jour la session
                session['user_name'] = full_name
                session['user_email'] = email
                
            flash('Profil mis à jour avec succès', 'success')
            return redirect(url_for('user_profile'))
        
        # GET request - afficher le formulaire
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, email, role
                FROM users 
                WHERE id = %s
            """, (session.get('user_id'),))
            
            user = cursor.fetchone()
            if not user:
                flash('Utilisateur non trouvé', 'error')
                return redirect(url_for('dashboard'))
                
        return render_template('profile/edit.html', user=user)
        
    except Exception as e:
        logger.error(f"Erreur modification profil: {e}")
        flash('Erreur lors de la modification du profil', 'error')
        return redirect(url_for('user_profile'))
    finally:
        if conn:
            conn.close()

@app.route('/settings')
@login_required
def settings():
    """Page des paramètres utilisateur"""
    try:
        conn = get_db_connection()
        if conn is None:
            flash('Service de base de données temporairement indisponible', 'error')
            return redirect(url_for('dashboard'))
            
        with conn.cursor() as cursor:
            # Récupérer les paramètres utilisateur
            cursor.execute("""
                SELECT id, name, email, role, is_active
                FROM users 
                WHERE id = %s
            """, (session.get('user_id'),))
            
            user = cursor.fetchone()
            if not user:
                flash('Utilisateur non trouvé', 'error')
                return redirect(url_for('dashboard'))
                
        # Paramètres par défaut (on peut les stocker en DB plus tard)
        settings_data = {
            'notifications': {
                'email_notifications': True,
                'sms_notifications': False,
                'desktop_notifications': True
            },
            'display': {
                'theme': 'light',
                'language': 'fr',
                'timezone': 'Europe/Paris'
            },
            'privacy': {
                'show_profile': True,
                'show_activity': False
            }
        }
        
        return render_template('settings/index.html', user=user, settings=settings_data)
        
    except Exception as e:
        logger.error(f"Erreur paramètres: {e}")
        flash('Erreur lors du chargement des paramètres', 'error')
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

@app.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    """Mettre à jour les paramètres utilisateur"""
    try:
        # Pour l'instant, on simule la mise à jour des paramètres
        setting_type = request.form.get('setting_type')
        
        if setting_type == 'notifications':
            flash('Paramètres de notifications mis à jour', 'success')
        elif setting_type == 'display':
            flash('Paramètres d\'affichage mis à jour', 'success')
        elif setting_type == 'privacy':
            flash('Paramètres de confidentialité mis à jour', 'success')
        else:
            flash('Paramètres mis à jour', 'success')
            
        return redirect(url_for('settings'))
        
    except Exception as e:
        logger.error(f"Erreur mise à jour paramètres: {e}")
        flash('Erreur lors de la mise à jour des paramètres', 'error')
        return redirect(url_for('settings'))

# Import des modules de routes
from routes import work_orders, interventions, customers, technicians, analytics, api

# Enregistrement des blueprints
app.register_blueprint(work_orders.bp, url_prefix='/work_orders')
app.register_blueprint(interventions.bp, url_prefix='/interventions')
app.register_blueprint(customers.bp, url_prefix='/customers')
app.register_blueprint(technicians.bp, url_prefix='/technicians')
app.register_blueprint(analytics.bp, url_prefix='/analytics')
app.register_blueprint(api.bp, url_prefix='/api')

# Gestion des erreurs
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

# Filtres Jinja personnalisés
@app.template_filter('datetime_format')
def datetime_format(value, format='%d/%m/%Y %H:%M'):
    """Formater les dates/heures"""
    if value is None:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except:
            return value
    return value.strftime(format)

@app.template_filter('duration_format')
def duration_format(minutes):
    """Formater la durée en minutes vers HH:MM"""
    if not minutes:
        return '00:00'
    hours = minutes // 60
    mins = minutes % 60
    return f'{hours:02d}:{mins:02d}'

@app.template_filter('currency')
def currency_format(amount):
    """Formater les montants en euros"""
    if amount is None:
        return '0,00 €'
    return f'{amount:,.2f} €'.replace(',', ' ').replace('.', ',')

@app.template_filter('priority_badge')
def priority_badge(priority):
    """Classes CSS pour les badges de priorité"""
    badges = {
        'low': 'clay-badge-info',
        'medium': 'clay-badge-warning',
        'high': 'clay-badge-danger',
        'urgent': 'clay-badge-critical'
    }
    return badges.get(priority, 'clay-badge-secondary')

@app.template_filter('status_badge')
def status_badge(status):
    """Classes CSS pour les badges de statut"""
    badges = {
        'draft': 'clay-badge-secondary',
        'pending': 'clay-badge-info',
        'assigned': 'clay-badge-warning',
        'in_progress': 'clay-badge-primary',
        'completed': 'clay-badge-success',
        'cancelled': 'clay-badge-danger'
    }
    return badges.get(status, 'clay-badge-secondary')

@app.template_filter('nl2br')
def nl2br_filter(text):
    """Convertit les retours à la ligne en balises <br>"""
    if not text:
        return ''
    import re
    from markupsafe import Markup
    # Remplace les retours à la ligne par des balises <br>
    return Markup(re.sub(r'\r?\n', '<br>', str(text)))

# Variables globales pour les templates
@app.context_processor
def inject_globals():
    """Injecter des variables globales dans tous les templates, y compris un faux 'moment' pour compatibilité Jinja."""
    from datetime import datetime
    class MomentShim:
        def __init__(self, dt):
            if isinstance(dt, str):
                try:
                    self.dt = datetime.fromisoformat(dt)
                except Exception:
                    self.dt = None
            else:
                self.dt = dt
        def format(self, fmt):
            if not self.dt:
                return ''
            # Map some common moment.js formats to strftime
            fmt_map = {
                'DD/MM/YYYY': '%d/%m/%Y',
                'DD/MM/YYYY HH:mm': '%d/%m/%Y %H:%M',
                'YYYY-MM-DD': '%Y-%m-%d',
                'YYYY-MM-DD HH:mm': '%Y-%m-%d %H:%M',
                'HH:mm': '%H:%M',
            }
            for mfmt, sffmt in fmt_map.items():
                if fmt == mfmt:
                    return self.dt.strftime(sffmt)
            # fallback: try to use fmt as strftime
            try:
                return self.dt.strftime(fmt)
            except Exception:
                return str(self.dt)
    def moment(dt=None):
        from datetime import datetime
        if dt is None:
            dt = datetime.now()
        return MomentShim(dt)
    return {
        'current_user': {
            'id': session.get('user_id'),
            'name': session.get('user_name'),
            'email': session.get('user_email'),
            'role': session.get('user_role')
        },
        'app_name': 'ChronoTech',
        'app_version': '2.0',
        'current_time': datetime.now(),
        'moment': moment
    }

if __name__ == '__main__':
    # Créer les dossiers nécessaires
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs('static/temp', exist_ok=True)
    
    # Lancement de l'application
    app.run(
        debug=os.getenv('FLASK_ENV') == 'development',
        host=app.config.get('HOST', '0.0.0.0'),
        port=app.config.get('PORT', 5010)
    )
