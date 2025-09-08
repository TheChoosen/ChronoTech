"""
Module de gestion des clients - ChronoTech
Architecture modulaire pour améliorer la maintenabilité
"""

from flask import Blueprint

# Création du blueprint principal
bp = Blueprint('customers', __name__)

# Import et configuration des modules segmentés
try:
    from .utils import get_db_connection, get_current_user, require_role, log_customer_activity
except Exception as e:
    print(f"Warning: Failed to import utils: {e}")
    get_db_connection = get_current_user = require_role = log_customer_activity = None

try:
    from .validation import validate_customer_form_advanced, setup_validation_routes
except Exception as e:
    print(f"Warning: Failed to import validation: {e}")
    validate_customer_form_advanced = setup_validation_routes = None

try:
    from .geocoding import geocode_address, calculate_distance
except Exception as e:
    print(f"Warning: Failed to import geocoding: {e}")
    geocode_address = calculate_distance = None

try:
    from .consents import setup_consent_routes
except Exception as e:
    print(f"Warning: Failed to import consents: {e}")
    setup_consent_routes = None

try:
    from .main_routes import setup_main_routes
except Exception as e:
    print(f"Warning: Failed to import main_routes: {e}")
    setup_main_routes = None

try:
    from .api import setup_api_routes
except Exception as e:
    print(f"Warning: Failed to import api: {e}")
    setup_api_routes = None

try:
    from .finances import setup_finance_routes
except Exception as e:
    print(f"Warning: Failed to import finances: {e}")
    setup_finance_routes = None

# Configuration des routes dans le blueprint avec gestion d'erreurs
if setup_main_routes:
    try:
        setup_main_routes(bp)
        print("✅ Main routes configured successfully")
    except Exception as e:
        print(f"❌ Error configuring main routes: {e}")

if setup_api_routes:
    try:
        setup_api_routes(bp)
        print("✅ API routes configured successfully")
    except Exception as e:
        print(f"❌ Error configuring API routes: {e}")

if setup_finance_routes:
    try:
        setup_finance_routes(bp)
        print("✅ Finance routes configured successfully")
    except Exception as e:
        print(f"❌ Error configuring finance routes: {e}")

if setup_validation_routes:
    try:
        setup_validation_routes(bp)
        print("✅ Validation routes configured successfully")
    except Exception as e:
        print(f"❌ Error configuring validation routes: {e}")

if setup_consent_routes:
    try:
        setup_consent_routes(bp)
        print("✅ Consent routes configured successfully")
    except Exception as e:
        print(f"❌ Error configuring consent routes: {e}")

__all__ = [
    'bp',
    'get_db_connection',
    'get_current_user', 
    'require_role',
    'log_customer_activity',
    'validate_customer_form_advanced',
    'geocode_address',
    'calculate_distance'
]
