import os
from dotenv import load_dotenv
import pymysql.cursors

load_dotenv()

class Config:
    """Configuration de base pour ChronoTech"""
    
    # Configuration Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    FLASK_APP = os.environ.get('FLASK_APP', 'app.py')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Base de données MySQL
    MYSQL_HOST = os.environ.get('MYSQL_HOST', '192.168.50.101')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'gsicloud')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'TCOChoosenOne204$')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'bdm')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    
    # Configuration serveur
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5010))
    
    # Configuration uploads
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = set(os.environ.get('ALLOWED_EXTENSIONS', 'png,jpg,jpeg,gif,mp4,mov,mp3,wav,pdf').split(','))
    
    # Configuration IA et APIs
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    DEEPL_API_KEY = os.environ.get('DEEPL_API_KEY', '')
    WHISPER_API_ENDPOINT = os.environ.get('WHISPER_API_ENDPOINT', 'https://api.openai.com/v1/audio/transcriptions')
    
    # Configuration des langues
    SUPPORTED_LANGUAGES = os.environ.get('SUPPORTED_LANGUAGES', 'fr,en,es').split(',')
    DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE', 'fr')
    
    # Configuration des notifications
    NOTIFICATION_EMAIL_ENABLED = os.environ.get('NOTIFICATION_EMAIL_ENABLED', 'False').lower() == 'true'
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    
    # Configuration Cloudflare (optionnel)
    CLOUDFLARE_TUNNEL_ENABLED = os.environ.get('CLOUDFLARE_TUNNEL_ENABLED', 'False').lower() == 'true'
    CLOUDFLARE_TUNNEL_URL = os.environ.get('CLOUDFLARE_TUNNEL_URL', '')
    
    # Configuration des logs
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/chronotech.log')
    
    # Configuration Redis (optionnel)
    REDIS_ENABLED = os.environ.get('REDIS_ENABLED', 'False').lower() == 'true'
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    
    # Configuration de session
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', 3600))  # 1 heure
    REMEMBER_COOKIE_DURATION = int(os.environ.get('REMEMBER_COOKIE_DURATION', 604800))  # 1 semaine
    
    @staticmethod
    def init_app(app):
        """Initialisation de l'application avec la configuration"""
        # Création des répertoires nécessaires
        import os
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # Configuration des logs
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug:
            file_handler = RotatingFileHandler(
                Config.LOG_FILE, 
                maxBytes=10240000, 
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(getattr(logging, Config.LOG_LEVEL))
            app.logger.addHandler(file_handler)
            app.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
            app.logger.info('ChronoTech startup')

class DevelopmentConfig(Config):
    """Configuration pour l'environnement de développement"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Configuration pour l'environnement de production"""
    DEBUG = False
    TESTING = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log vers syslog en production
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)

class TestingConfig(Config):
    """Configuration pour les tests"""
    TESTING = True
    MYSQL_DB = os.environ.get('TEST_MYSQL_DB', 'chronotech_test')
    WTF_CSRF_ENABLED = False

# Dictionnaire des configurations
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_db_config():
    """Retourne la configuration de la base de données pour PyMySQL"""
    return {
        'host': Config.MYSQL_HOST,
        'user': Config.MYSQL_USER,
        'password': Config.MYSQL_PASSWORD,
        'database': Config.MYSQL_DB,
        'port': Config.MYSQL_PORT,
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': False
    }
