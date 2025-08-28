"""
Module customers - Architecture modulaire
Fichier de transition vers la nouvelle structure

MIGRATION TERMINÉE ✅
Le fichier customers.py monolithique (6400+ lignes) a été segmenté en modules logiques.
"""

# Import du blueprint principal depuis la nouvelle architecture
from routes.customers import bp

# Imports de compatibilité pour maintenir l'ancien code
from routes.customers.utils import (
    get_db_connection, 
    get_current_user, 
    require_role,
    log_customer_activity,
    MiniPagination,
    _debug
)

from routes.customers.validation import (
    validate_customer_form_advanced,
    validate_siret,
    validate_phone_international,
    validate_email_advanced,
    validate_postal_code_format,
    FORM_VALIDATION_CONFIG
)

from routes.customers.geocoding import (
    geocode_address,
    calculate_distance,
    find_addresses_in_radius,
    GEOCODING_CONFIG
)

from routes.customers.consents import (
    fetch_customer_consents,
    update_customer_consent,
    check_consent_compliance,
    can_send_communication,
    CONSENT_CONFIG
)

# Tous les endpoints sont maintenant configurés automatiquement
# via les modules dans routes/customers/__init__.py

# Exports pour compatibilité
__all__ = [
    'bp',
    'get_db_connection',
    'get_current_user',
    'require_role',
    'log_customer_activity',
    'MiniPagination',
    'validate_customer_form_advanced',
    'geocode_address',
    'calculate_distance',
    'fetch_customer_consents',
    'GEOCODING_CONFIG',
    'FORM_VALIDATION_CONFIG',
    'CONSENT_CONFIG'
]

"""
ARCHITECTURE MODULAIRE:

routes/customers/
├── __init__.py       # Point d'entrée principal
├── utils.py         # Utilitaires et helpers
├── validation.py    # Validations et formulaires  
├── geocoding.py     # Services géolocalisation
├── consents.py      # Gestion RGPD/consentements
├── routes.py        # Routes principales CRUD
├── api.py          # Endpoints API REST
└── finances.py     # Gestion financière

AVANTAGES:
✅ Maintenabilité améliorée
✅ Code organisé par domaines métier
✅ Tests unitaires plus faciles
✅ Import sélectif des modules
✅ Équipes peuvent travailler en parallèle
✅ Toutes les routes existantes préservées

MIGRATION: 
- L'ancien fichier customers.py (6407 lignes) est sauvegardé
- Toutes les fonctionnalités sont préservées
- Les routes restent identiques pour les templates
- Import du blueprint: from routes.customers import bp
"""
