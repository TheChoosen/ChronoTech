"""
Module de gestion des clients - ChronoTech
Architecture modulaire pour améliorer la maintenabilité
"""

from flask import Blueprint

# Création du blueprint principal
bp = Blueprint('customers', __name__)

# Import et configuration des modules segmentés
from .utils import get_db_connection, get_current_user, require_role, log_customer_activity
from .validation import validate_customer_form_advanced, setup_validation_routes
from .geocoding import geocode_address, calculate_distance
from .consents import setup_consent_routes
from .routes import setup_main_routes
from .api import setup_api_routes
from .finances import setup_finance_routes

# Configuration des routes dans le blueprint
setup_main_routes(bp)
setup_api_routes(bp)
setup_finance_routes(bp)
setup_validation_routes(bp)
setup_consent_routes(bp)

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
