"""
ChronoTech - Module Interventions & Travaux (v2.0)
Application Flask principale basée sur le PRD Fusionné
Architecture moderne avec design Claymorphism et intégration IA
"""
import traceback
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
# Import and register optional blueprints
from routes.appointments import bp as appointments_bp
from routes.vehicles import bp as vehicles_bp
from routes.products import bp as products_bp
from routes.invoices import bp as invoices_bp

# Import Sprint 2 API blueprints
try:
    from routes.work_orders.api_tasks import api_tasks_bp
    from routes.interventions.api_interventions import api_interventions_bp
    SPRINT2_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Sprint 2 blueprints non disponibles: {e}")
    SPRINT2_AVAILABLE = False

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Customer 360 API routes après logger
try:
    from routes.customer360_api import customer360_api
    CUSTOMER360_API_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Customer 360 API non disponible: {e}")
    CUSTOMER360_API_AVAILABLE = False


# Suppress noisy scanner/probe requests from werkzeug access logs
class _ProbeFilter(logging.Filter):
    def __init__(self, patterns=None):
        super().__init__()
        # simple substrings matching common probe filenames
        self.patterns = patterns or [
            '/wp-', '/wp-content', 'wp_filemanager', '/php', '/shell.php', '/fm.php',
            '/admin.php', '/log.php', '/upload.php', '/info.php', '/ini.php', '/0x.php'
        ]

    def filter(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            return True
        # if any probe pattern appears in the log message, suppress it
        for p in self.patterns:
            if p in msg:
                return False
        return True

def create_app(config_class=Config):
    """Factory pattern pour créer l'application Flask"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    # Attach probe filter to werkzeug access logger to reduce noise
    try:
        werk_logger = logging.getLogger('werkzeug')
        werk_logger.addFilter(_ProbeFilter())
    except Exception:
        logger.exception('Impossible d’ajouter le filtre de probe au logger werkzeug')
    
    # Initialisation des composants
    init_template_filters(app)
    setup_upload_folders(app.root_path)
    # Register small blueprints
    try:
        app.register_blueprint(appointments_bp, url_prefix='/appointments')
    except Exception as e:
        logger.warning(f"Impossible d'enregistrer appointments blueprint: {e}")
    try:
        app.register_blueprint(vehicles_bp, url_prefix='/vehicles')
    except Exception as e:
        logger.warning(f"Impossible d'enregistrer vehicles blueprint: {e}")
    try:
        app.register_blueprint(products_bp)
    except Exception as e:
        logger.warning(f"Impossible d'enregistrer products blueprint: {e}")
    try:
        app.register_blueprint(invoices_bp)
    except Exception as e:
        logger.warning(f"Impossible d'enregistrer invoices blueprint: {e}")
    
    # Register Sprint 2 API blueprints (sécurisés)
    if SPRINT2_AVAILABLE:
        try:
            app.register_blueprint(api_tasks_bp, url_prefix='/api/v1')
            logger.info("✅ API Tasks blueprint enregistré (Sprint 2) - /api/v1/work_orders/<id>/tasks")
        except Exception as e:
            logger.error(f"❌ Erreur enregistrement API Tasks: {e}")
        
        try:
            app.register_blueprint(api_interventions_bp, url_prefix='/api/v1')
            logger.info("✅ API Interventions blueprint enregistré (Sprint 2) - /api/v1/interventions")
        except Exception as e:
            logger.error(f"❌ Erreur enregistrement API Interventions: {e}")
        
        try:
            from routes.ai_routes import ai_bp
            app.register_blueprint(ai_bp, url_prefix='/api/v1')
            logger.info("✅ AI Routes blueprint enregistré (Sprint 2) - /api/v1/ai")
        except Exception as e:
            logger.error(f"❌ Erreur enregistrement AI Routes: {e}")
    else:
        logger.warning("⚠️ Sprint 2 API blueprints non disponibles - fonctionnalités limitées")
    
    # Register Sprint 3 blueprints (Interface Mobile, Superviseur & PDF)
    try:
        from routes.mobile import mobile_bp
        app.register_blueprint(mobile_bp, url_prefix='/mobile')
        logger.info("✅ Mobile blueprint enregistré (Sprint 3) - /mobile")
    except Exception as e:
        logger.error(f"❌ Erreur enregistrement Mobile blueprint: {e}")
    
    try:
        from routes.supervisor import supervisor_bp
        app.register_blueprint(supervisor_bp, url_prefix='/supervisor')
        logger.info("✅ Supervisor blueprint enregistré (Sprint 3) - /supervisor")
    except Exception as e:
        logger.error(f"❌ Erreur enregistrement Supervisor blueprint: {e}")
    
    try:
        from routes.pdf import pdf_bp
        app.register_blueprint(pdf_bp, url_prefix='/pdf')
        logger.info("✅ PDF blueprint enregistré (Sprint 3) - /pdf")
    except Exception as e:
        logger.error(f"❌ Erreur enregistrement PDF blueprint: {e}")
    
    # Register Customer 360 API si disponible
    if CUSTOMER360_API_AVAILABLE:
        try:
            app.register_blueprint(customer360_api, url_prefix='/api/customer360')
            logger.info("✅ Customer 360 API blueprint enregistré")
        except Exception as e:
            logger.error(f"❌ Erreur enregistrement Customer 360 API: {e}")
    else:
        logger.warning("⚠️ Customer 360 API non disponible")
    
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
    # Expect canonical tokens: 'company', 'individual', 'government'
    if value == 'company' or value == 'entreprise':
        return 'bg-primary'
    elif value == 'individual' or value == 'particulier':
        return 'bg-success'
    elif value == 'government' or value == 'administration':
        return 'bg-info'
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

@app.route('/clay')
def clay():
    """Page d'accueil - redirige vers dashboard si connecté"""
    return render_template('clay.html')

@app.route('/login', methods=['GET', 'POST'])
def auth_login():
    """Connexion utilisateur avec données des deux tables"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Join bdm.users and gsi.clientsweb
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        u.id, u.name, u.email, u.password, u.role,
                        c.Record_id
                    FROM bdm.users u
                    LEFT JOIN gsi.clientsweb c ON u.email = c.Courriel
                    WHERE u.email = %s
                """, (email,))
                user_data = cursor.fetchone()
                
                if user_data and check_password_hash(user_data['password'], password):
                    # Get company code if clientsweb record exists
                    company_code = ""
                    if user_data['Record_id']:
                        company_code = get_user_company_code(user_data['Record_id'])
                    
                    # Store in session
                    session['user_id'] = user_data['id']
                    session['user_name'] = user_data['name']
                    session['user_email'] = user_data['email']
                    session['user_role'] = user_data['role']
                    session['user_company'] = company_code
                    
                    flash(f'Bienvenue {user_data["name"]} !', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Email ou mot de passe incorrect', 'error')
        finally:
            conn.close()
    
    return render_template('auth/login.html')

def get_user_company_code(user_id):
    """
    Get the company code for a user from clientsweb -> compagnieweb tables
    Returns the company code (e.g., 'BDM') or None if not found
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection("gsi")
        cursor = conn.cursor(dictionary=True)
        
        # Get the compagnieweb_Record_id from clientsweb
        cursor.execute("""
            SELECT compagnieweb_Record_id 
            FROM clientsweb 
            WHERE Record_id = %s
        """, [user_id])
        
        client_result = cursor.fetchone()
        
        if not client_result or not client_result.get('compagnieweb_Record_id'):
            return None
        
        compagnieweb_record_id = client_result['compagnieweb_Record_id']
        
        # Get the compagnie_id from compagnieweb table
        cursor.execute("""
            SELECT compagnie_id 
            FROM compagnieweb 
            WHERE Record_id = %s
        """, [compagnieweb_record_id])
        
        company_result = cursor.fetchone()
        
        if not company_result or not company_result.get('compagnie_id'):
            return None
        
        compagnie_id = company_result['compagnie_id']
        
        # Extract company code by removing duplicate (e.g., BDMBDM -> BDM)
        if len(compagnie_id) % 2 == 0:
            mid_point = len(compagnie_id) // 2
            first_half = compagnie_id[:mid_point]
            second_half = compagnie_id[mid_point:]
            
            if first_half == second_half:
                company_code = first_half
                return company_code
        
        # If not a duplicate pattern, return the full compagnie_id
        return compagnie_id
        
    except Exception as e:
        print(f"ERROR: Failed to get user company: {str(e)}")
        traceback.print_exc()
        return None
    finally:
        try:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
        except Exception as cleanup_error:
            print(f"ERROR: Failed to cleanup database connection: {cleanup_error}")


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

# Import des modules de routes avec gestion des conflits
ROUTES_AVAILABLE = False
work_orders_bp = None
interventions_bp = None
customers_bp = None
technicians_bp = None
analytics_bp = None
api_bp = None

# Import work_orders.py spécifiquement pour éviter le conflit avec le package
try:
    import sys
    import importlib.util
    
    work_orders_spec = importlib.util.spec_from_file_location("work_orders_module", 
                                                             "/home/amenard/Chronotech/ChronoTech/routes/work_orders.py")
    work_orders_module = importlib.util.module_from_spec(work_orders_spec)
    work_orders_spec.loader.exec_module(work_orders_module)
    work_orders_bp = work_orders_module.bp
    logger.info("✅ work_orders blueprint importé avec succès")
except Exception as e:
    logger.error(f"❌ Erreur import work_orders: {e}")

# Import des autres modules avec gestion d'erreurs individuelles
try:
    # Import interventions.py spécifiquement comme work_orders
    interventions_spec = importlib.util.spec_from_file_location("interventions_module", 
                                                               "/home/amenard/Chronotech/ChronoTech/routes/interventions.py")
    interventions_module = importlib.util.module_from_spec(interventions_spec)
    interventions_spec.loader.exec_module(interventions_module)
    interventions_bp = interventions_module.bp
    logger.info("✅ interventions blueprint importé avec succès")
except Exception as e:
    logger.error(f"❌ Erreur import interventions: {e}")
    import traceback
    traceback.print_exc()
    
try:  
    import routes.customers as customers_module
    customers_bp = customers_module.bp
    logger.info("✅ customers blueprint importé avec succès")
except Exception as e:
    logger.error(f"❌ Erreur import customers: {e}")

try:
    import routes.technicians as technicians_module
    technicians_bp = technicians_module.bp
    logger.info("✅ technicians blueprint importé avec succès")
except Exception as e:
    logger.error(f"❌ Erreur import technicians: {e}")

try:
    import routes.analytics as analytics_module
    analytics_bp = analytics_module.bp
    logger.info("✅ analytics blueprint importé avec succès")
except Exception as e:
    logger.error(f"❌ Erreur import analytics: {e}")

try:
    import routes.api as api_module
    api_bp = api_module.bp
    logger.info("✅ api blueprint importé avec succès")
except Exception as e:
    logger.error(f"❌ Erreur import api: {e}")

# Vérifier si au moins quelques blueprints sont disponibles
available_blueprints = sum([bp is not None for bp in [work_orders_bp, interventions_bp, customers_bp, technicians_bp, analytics_bp, api_bp]])
if available_blueprints > 0:
    ROUTES_AVAILABLE = True
    logger.info(f"✅ {available_blueprints}/6 blueprints principaux importés")
else:
    logger.error("❌ Aucun blueprint principal n'a pu être importé")

# Enregistrement des blueprints
if ROUTES_AVAILABLE:
    try:
        if work_orders_bp:
            app.register_blueprint(work_orders_bp, url_prefix='/work_orders')
            logger.info("✅ Blueprint work_orders enregistré")
        
        if interventions_bp:
            app.register_blueprint(interventions_bp, url_prefix='/interventions')
            logger.info("✅ Blueprint interventions enregistré")
        
        if customers_bp:
            app.register_blueprint(customers_bp, url_prefix='/customers')
            logger.info("✅ Blueprint customers enregistré")
        
        if technicians_bp:
            app.register_blueprint(technicians_bp, url_prefix='/technicians')
            logger.info("✅ Blueprint technicians enregistré")
        
        if analytics_bp:
            app.register_blueprint(analytics_bp, url_prefix='/analytics')
            logger.info("✅ Blueprint analytics enregistré")
        
        if api_bp:
            app.register_blueprint(api_bp, url_prefix='/api')
            logger.info("✅ Blueprint api enregistré")
        
        # Enregistrer openai si disponible
        try:
            from routes.openai import openai_bp
            app.register_blueprint(openai_bp, url_prefix='/openai')
            logger.info("✅ OpenAI blueprint enregistré")
        except ImportError:
            logger.info("ℹ️ OpenAI blueprint non disponible - continuons sans")
        
        logger.info("✅ Tous les blueprints principaux enregistrés")
    except Exception as e:
        logger.error(f"❌ Erreur enregistrement blueprints: {e}")
else:
    logger.warning("⚠️ Routes principales non disponibles")

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

# Replace your existing MomentShim class in app.py with this enhanced version

@app.context_processor
def inject_globals():
    """Injecter des variables globales dans tous les templates, y compris un faux 'moment' pour compatibilité Jinja."""
    from datetime import datetime, timezone
    import math
    
    class MomentShim:
        def __init__(self, dt):
            if dt is None:
                self.dt = None
            elif isinstance(dt, str):
                try:
                    # Handle various string formats
                    if dt.endswith('Z'):
                        dt = dt[:-1] + '+00:00'
                    self.dt = datetime.fromisoformat(dt)
                    # Ensure timezone awareness
                    if self.dt.tzinfo is None:
                        self.dt = self.dt.replace(tzinfo=timezone.utc)
                except Exception:
                    try:
                        # Try parsing as standard format
                        self.dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
                        self.dt = self.dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        self.dt = None
            elif isinstance(dt, datetime):
                self.dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            else:
                self.dt = dt
        
        def fromNow(self, suffix=True):
            """
            Returns a human-readable relative time string (e.g., "il y a 2 heures", "dans 3 jours")
            Similar to moment.js fromNow() method, but in French for ChronoTech
            """
            if not self.dt:
                return "date invalide"
                
            now = datetime.now(timezone.utc)
            
            # Ensure both datetimes are timezone-aware
            if self.dt.tzinfo is None:
                dt = self.dt.replace(tzinfo=timezone.utc)
            else:
                dt = self.dt
                
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)
            
            diff = now - dt
            total_seconds = diff.total_seconds()
            
            # Determine if it's past or future
            is_past = total_seconds > 0
            abs_seconds = abs(total_seconds)
            
            # Calculate time units
            minute = 60
            hour = minute * 60
            day = hour * 24
            month = day * 30.44  # Average month length
            year = day * 365.25  # Average year length
            
            # French time expressions
            if abs_seconds < 45:
                time_str = "quelques secondes"
            elif abs_seconds < 90:
                time_str = "une minute"
            elif abs_seconds < 45 * minute:
                minutes = math.floor(abs_seconds / minute)
                time_str = f"{minutes} minute{'s' if minutes > 1 else ''}"
            elif abs_seconds < 90 * minute:
                time_str = "une heure"
            elif abs_seconds < 22 * hour:
                hours = math.floor(abs_seconds / hour)
                time_str = f"{hours} heure{'s' if hours > 1 else ''}"
            elif abs_seconds < 36 * hour:
                time_str = "un jour"
            elif abs_seconds < 25 * day:
                days = math.floor(abs_seconds / day)
                time_str = f"{days} jour{'s' if days > 1 else ''}"
            elif abs_seconds < 45 * day:
                time_str = "un mois"
            elif abs_seconds < 320 * day:
                months = math.floor(abs_seconds / month)
                time_str = f"{months} mois"
            elif abs_seconds < 548 * day:
                time_str = "un an"
            else:
                years = math.floor(abs_seconds / year)
                time_str = f"{years} an{'s' if years > 1 else ''}"
            
            if not suffix:
                return time_str
            
            if is_past:
                return f"il y a {time_str}"
            else:
                return f"dans {time_str}"
        
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
                'DD/MM': '%d/%m',
                'MMM YYYY': '%b %Y',
                'MMMM YYYY': '%B %Y',
                'DD MMM': '%d %b',
                'DD MMMM': '%d %B',
            }
            
            # Check if it's a direct mapping
            if fmt in fmt_map:
                return self.dt.strftime(fmt_map[fmt])
            
            # Try to convert moment.js format to strftime
            converted_fmt = fmt
            moment_to_strftime = {
                'YYYY': '%Y',
                'YY': '%y',
                'MM': '%m',
                'MMM': '%b',
                'MMMM': '%B',
                'DD': '%d',
                'HH': '%H',
                'hh': '%I',
                'mm': '%M',
                'ss': '%S',
                'A': '%p',
                'a': '%p'
            }
            
            for moment_token, strftime_token in moment_to_strftime.items():
                converted_fmt = converted_fmt.replace(moment_token, strftime_token)
            
            # fallback: try to use converted format as strftime
            try:
                return self.dt.strftime(converted_fmt)
            except Exception:
                # If all else fails, return ISO format
                return self.dt.strftime('%Y-%m-%d %H:%M:%S')
        
        def calendar(self):
            """Return a calendar-style representation"""
            if not self.dt:
                return "date invalide"
                
            now = datetime.now(timezone.utc)
            diff = (self.dt.date() - now.date()).days
            
            if diff == 0:
                return f"Aujourd'hui à {self.dt.strftime('%H:%M')}"
            elif diff == 1:
                return f"Demain à {self.dt.strftime('%H:%M')}"
            elif diff == -1:
                return f"Hier à {self.dt.strftime('%H:%M')}"
            elif -7 <= diff < 0:
                days = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
                return f"{days[self.dt.weekday()]} dernier à {self.dt.strftime('%H:%M')}"
            elif 0 < diff <= 7:
                days = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
                return f"{days[self.dt.weekday()]} à {self.dt.strftime('%H:%M')}"
            else:
                return self.dt.strftime('%d/%m/%Y à %H:%M')
        
        def __str__(self):
            return str(self.dt) if self.dt else "None"
    
        def fromNow(self):
            """Retourne une chaîne relative en français depuis maintenant (ex: 'il y a 2 heures')."""
            if not self.dt:
                return ''
            from datetime import datetime
            now = datetime.now()
            try:
                diff = now - self.dt
            except Exception:
                return ''
            seconds = int(diff.total_seconds())
            past = seconds >= 0
            sec = abs(seconds)
            if sec < 45:
                return "à l'instant" if past else 'dans un instant'
            if sec < 90:
                return 'il y a une minute' if past else 'dans une minute'
            minutes = sec // 60
            if minutes < 45:
                return f"il y a {minutes} minutes" if past else f"dans {minutes} minutes"
            if minutes < 90:
                return 'il y a une heure' if past else 'dans une heure'
            hours = minutes // 60
            if hours < 24:
                return f"il y a {hours} heures" if past else f"dans {hours} heures"
            days = hours // 24
            if days == 1:
                return 'il y a un jour' if past else 'dans un jour'
            if days < 30:
                return f"il y a {days} jours" if past else f"dans {days} jours"
            # Fallback to a readable date for older items
            try:
                return self.dt.strftime('%d/%m/%Y')
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
        'datetime': datetime,
        'timedelta': timedelta,
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
        port=int(os.getenv('FLASK_PORT', 5013))
    )
