
"""Module de gestion des clients - ChronoTech"""

import pymysql
import json
import traceback
import hashlib
import requests
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, make_response, current_app
from werkzeug.utils import secure_filename
from core.forms import CustomerForm
from core.config import get_db_config
from core.utils import log_info, log_error, log_warning
from core.models import User
from core.database import log_activity

# Configuration géospatiale
GEOCODING_CONFIG = {
    'provider': 'nominatim',  # nominatim, google, mapbox
    'api_key': None,  # Pour Google Maps ou Mapbox
    'rate_limit': 1,  # Requests per second
    'timeout': 5,     # Timeout en secondes
}

def geocode_address(address_string):
    """Géocode une adresse en coordonnées lat/lng"""
    try:
        if GEOCODING_CONFIG['provider'] == 'nominatim':
            # Service gratuit OpenStreetMap
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': address_string,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'ChronoTech/1.0 (contact@chronotech.fr)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=GEOCODING_CONFIG['timeout'])
            if response.status_code == 200:
                data = response.json()
                if data:
                    return float(data[0]['lat']), float(data[0]['lon'])
        
        elif GEOCODING_CONFIG['provider'] == 'google' and GEOCODING_CONFIG['api_key']:
            # Google Maps Geocoding API (nécessite clé API)
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': address_string,
                'key': GEOCODING_CONFIG['api_key']
            }
            
            response = requests.get(url, params=params, timeout=GEOCODING_CONFIG['timeout'])
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'OK' and data['results']:
                    location = data['results'][0]['geometry']['location']
                    return location['lat'], location['lng']
        
        return None
    except Exception as e:
        log_error(f"Erreur géocodage pour '{address_string}': {e}")
        return None

def calculate_distance(lat1, lng1, lat2, lng2):
    """Calcule la distance entre deux points en kilomètres (formule de Haversine)"""
    import math
    
    # Conversion en radians
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    # Formule de Haversine
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Rayon de la Terre en kilomètres
    r = 6371
    
    return c * r

def find_addresses_in_radius(center_lat, center_lng, radius_km, customer_id=None):
    """Trouve les adresses dans un rayon donné"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        where_clause = "latitude IS NOT NULL AND longitude IS NOT NULL"
        params = []
        
        if customer_id:
            where_clause += " AND customer_id = %s"
            params.append(customer_id)
        
        cursor.execute(f"""
            SELECT *, 
                   (6371 * acos(cos(radians(%s)) * cos(radians(latitude)) * 
                   cos(radians(longitude) - radians(%s)) + sin(radians(%s)) * 
                   sin(radians(latitude)))) AS distance_km
            FROM customer_addresses
            WHERE {where_clause}
            HAVING distance_km <= %s
            ORDER BY distance_km
        """, [center_lat, center_lng, center_lat] + params + [radius_km])
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return results
    except Exception as e:
        log_error(f"Erreur recherche adresses dans rayon: {e}")
        return []

def get_customer_consents(customer_id):
    """Récupère les consentements d'un client"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute("""
            SELECT * FROM customer_consents 
            WHERE customer_id = %s AND is_active = 1
            ORDER BY consent_type, created_at DESC
        """, [customer_id])
        
        consents = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Organiser par type de consentement
        consent_map = {}
        for consent in consents:
            consent_type = consent['consent_type']
            if consent_type not in consent_map:
                consent_map[consent_type] = consent
        
        return consent_map
    except Exception as e:
        log_error(f"Erreur récupération consentements client {customer_id}: {e}")
        return {}

def update_customer_consent(customer_id, consent_type, granted, user_id, source='manual'):
    """Met à jour un consentement client"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Désactiver les anciens consentements
        cursor.execute("""
            UPDATE customer_consents 
            SET is_active = 0, updated_at = NOW()
            WHERE customer_id = %s AND consent_type = %s
        """, [customer_id, consent_type])
        
        # Ajouter le nouveau consentement
        cursor.execute("""
            INSERT INTO customer_consents 
            (customer_id, consent_type, granted, granted_at, source, created_by, created_at, is_active)
            VALUES (%s, %s, %s, NOW(), %s, %s, NOW(), 1)
        """, [customer_id, consent_type, granted, source, user_id])
        
        consent_id = cursor.lastrowid
        
        # Log de l'activité
        activity_data = {
            'consent_type': consent_type,
            'granted': granted,
            'source': source,
            'consent_id': consent_id
        }
        
        log_activity(
            user_id, 
            'consent_update', 
            f"{'Accord' if granted else 'Refus'} consentement {consent_type}",
            customer_id=customer_id,
            details=json.dumps(activity_data)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        log_error(f"Erreur mise à jour consentement: {e}")
        return False

def check_consent_compliance(customer_id):
    """Vérifie la conformité des consentements d'un client"""
    try:
        consents = get_customer_consents(customer_id)
        compliance_status = {
            'compliant': True,
            'missing_mandatory': [],
            'expired_consents': [],
            'renewal_required': []
        }
        
        # Vérifier les consentements obligatoires
        for consent_type, config in CONSENT_CONFIG['required_consents'].items():
            if config['mandatory']:
                if consent_type not in consents or not consents[consent_type]['granted']:
                    compliance_status['compliant'] = False
                    compliance_status['missing_mandatory'].append({
                        'type': consent_type,
                        'name': config['name'],
                        'description': config['description']
                    })
        
        # Vérifier les consentements expirés
        renewal_period = CONSENT_CONFIG['audit_requirements']['consent_renewal_period']
        cutoff_date = datetime.now().timestamp() - (renewal_period * 24 * 3600)
        
        for consent_type, consent in consents.items():
            consent_date = consent['granted_at'].timestamp() if consent['granted_at'] else 0
            if consent_date < cutoff_date:
                compliance_status['renewal_required'].append({
                    'type': consent_type,
                    'granted_at': consent['granted_at'],
                    'days_old': (datetime.now() - consent['granted_at']).days
                })
        
        return compliance_status
    except Exception as e:
        log_error(f"Erreur vérification conformité consentements: {e}")
        return {'compliant': False, 'error': str(e)}

def can_send_communication(customer_id, communication_type='marketing'):
    """Vérifie si on peut envoyer une communication à un client"""
    try:
        consents = get_customer_consents(customer_id)
        
        # Vérifications de base
        if 'data_processing' not in consents or not consents['data_processing']['granted']:
            return False, "Consentement traitement données manquant"
        
        if communication_type == 'marketing':
            if 'marketing' not in consents or not consents['marketing']['granted']:
                return False, "Consentement marketing manquant"
        
        # Vérifier si le client n'est pas en opposition
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute("""
            SELECT * FROM customer_communication_blocks 
            WHERE customer_id = %s AND is_active = 1 
            AND (communication_type = %s OR communication_type = 'all')
            AND (expires_at IS NULL OR expires_at > NOW())
        """, [customer_id, communication_type])
        
        blocks = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if blocks:
            return False, f"Communication bloquée: {blocks[0]['reason']}"
        
        return True, "Autorisé"
    except Exception as e:
        log_error(f"Erreur vérification autorisation communication: {e}")
        return False, f"Erreur technique: {e}"

# Utilitaire pour récupérer l'utilisateur courant
def get_current_user():
    """Récupère l'utilisateur courant à partir de la session"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.find_by_id(user_id)

# Décorateur RBAC pour restreindre l'accès selon le rôle utilisateur
def require_role(*roles):
    """Décorateur pour contrôler l'accès basé sur les rôles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Authentification requise'}), 401
            if roles and user.role not in roles:
                return jsonify({'error': 'Accès refusé'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Création du blueprint
bp = Blueprint('customers', __name__)

# Routes de gestion des consentements
@bp.route('/api/customer/<int:customer_id>/consents', methods=['GET'])
@require_role(['admin', 'manager', 'technician'])
def get_customer_consents_api(customer_id):
    """API pour récupérer les consentements d'un client"""
    try:
        consents = get_customer_consents(customer_id)
        compliance = check_consent_compliance(customer_id)
        
        # Enrichir avec les configurations
        enriched_consents = {}
        for consent_type, config in CONSENT_CONFIG['required_consents'].items():
            enriched_consents[consent_type] = {
                'config': config,
                'current': consents.get(consent_type),
                'granted': consents.get(consent_type, {}).get('granted', False) if consents.get(consent_type) else False
            }
        
        return jsonify({
            'success': True,
            'consents': enriched_consents,
            'compliance': compliance
        })
    except Exception as e:
        log_error(f"Erreur API consentements client {customer_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/customer/<int:customer_id>/consent', methods=['POST'])
@require_role(['admin', 'manager'])
def update_customer_consent_api(customer_id):
    """API pour mettre à jour un consentement client"""
    try:
        data = request.get_json()
        consent_type = data.get('consent_type')
        granted = data.get('granted', False)
        source = data.get('source', 'manual')
        
        if not consent_type:
            return jsonify({'success': False, 'message': 'Type de consentement requis'}), 400
        
        if consent_type not in CONSENT_CONFIG['required_consents']:
            return jsonify({'success': False, 'message': 'Type de consentement invalide'}), 400
        
        user_id = get_current_user().id
        success = update_customer_consent(customer_id, consent_type, granted, user_id, source)
        
        if success:
            return jsonify({'success': True, 'message': 'Consentement mis à jour'})
        else:
            return jsonify({'success': False, 'message': 'Erreur lors de la mise à jour'}), 500
            
    except Exception as e:
        log_error(f"Erreur mise à jour consentement API: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/api/customer/<int:customer_id>/communication-check', methods=['POST'])
@require_role(['admin', 'manager', 'technician'])
def check_communication_permission(customer_id):
    """API pour vérifier l'autorisation d'envoi de communication"""
    try:
        data = request.get_json()
        communication_type = data.get('type', 'marketing')
        
        allowed, reason = can_send_communication(customer_id, communication_type)
        
        return jsonify({
            'success': True,
            'allowed': allowed,
            'reason': reason,
            'communication_type': communication_type
        })
    except Exception as e:
        log_error(f"Erreur vérification communication: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Configuration de validation avancée des formulaires
FORM_VALIDATION_CONFIG = {
    'business_rules': {
        'siret': {
            'required_for_business': True,
            'format': r'^[0-9]{14}$',
            'api_validation': False  # Validation via API SIRENE (désactivée par défaut)
        },
        'phone': {
            'international_format': True,
            'multiple_allowed': True,
            'validation_api': 'libphonenumber'
        },
        'email': {
            'domain_validation': True,
            'mx_record_check': False,  # Désactivé pour éviter la lenteur
            'disposable_email_check': True
        },
        'address': {
            'geocoding_validation': True,
            'international_support': True,
            'postal_code_format_check': True
        }
    },
    'field_dependencies': {
        'customer_type': {
            'business': ['company_name', 'siret'],
            'individual': ['first_name', 'last_name']
        },
        'billing_address_same_as_service': {
            True: [],  # Pas de champs supplémentaires requis
            False: ['billing_address', 'billing_city', 'billing_postal_code']
        }
    },
    'conditional_validations': {
        'warranty_end_date': {
            'condition': 'warranty_start_date_filled',
            'rule': 'must_be_after_start_date'
        },
        'emergency_contact': {
            'condition': 'customer_type_individual_and_elderly',
            'rule': 'required'
        }
    }
}

def validate_siret(siret):
    """Valide un numéro SIRET"""
    try:
        import re
        
        # Format de base
        if not re.match(r'^[0-9]{14}$', siret):
            return False, "Format SIRET invalide (14 chiffres requis)"
        
        # Algorithme de validation SIRET
        def validate_siret_checksum(siret_str):
            total = 0
            for i, digit in enumerate(siret_str[:-1]):
                multiplier = 2 if i % 2 == 1 else 1
                result = int(digit) * multiplier
                if result > 9:
                    result = (result // 10) + (result % 10)
                total += result
            
            checksum = (10 - (total % 10)) % 10
            return checksum == int(siret_str[-1])
        
        if not validate_siret_checksum(siret):
            return False, "Numéro SIRET invalide (échec validation)"
        
        return True, "SIRET valide"
    except Exception as e:
        return False, f"Erreur validation SIRET: {e}"

def validate_phone_international(phone):
    """Valide un numéro de téléphone international"""
    try:
        import re
        
        # Nettoyage de base
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Validation de base
        if len(cleaned) < 10:
            return False, "Numéro trop court"
        
        if len(cleaned) > 15:
            return False, "Numéro trop long"
        
        # Formats français courants
        french_patterns = [
            r'^\+33[1-9][0-9]{8}$',  # +33 suivi de 9 chiffres
            r'^0[1-9][0-9]{8}$',     # 0 suivi de 9 chiffres
        ]
        
        for pattern in french_patterns:
            if re.match(pattern, cleaned):
                return True, "Numéro valide"
        
        # Format international générique
        if cleaned.startswith('+') and len(cleaned) >= 11:
            return True, "Numéro international valide"
        
        return False, "Format de numéro invalide"
    except Exception as e:
        return False, f"Erreur validation téléphone: {e}"

def validate_email_advanced(email):
    """Validation avancée d'email"""
    try:
        import re
        
        # Format de base
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "Format email invalide"
        
        domain = email.split('@')[1].lower()
        
        # Liste des domaines jetables courants
        disposable_domains = {
            '10minutemail.com', 'guerrillamail.com', 'mailinator.com',
            'yopmail.com', 'tempmail.org', 'temp-mail.org'
        }
        
        if FORM_VALIDATION_CONFIG['business_rules']['email']['disposable_email_check']:
            if domain in disposable_domains:
                return False, "Adresses email temporaires non autorisées"
        
        return True, "Email valide"
    except Exception as e:
        return False, f"Erreur validation email: {e}"

def validate_postal_code_format(postal_code, country='FR'):
    """Valide le format du code postal selon le pays"""
    try:
        import re
        
        postal_patterns = {
            'FR': r'^[0-9]{5}$',
            'BE': r'^[0-9]{4}$',
            'CH': r'^[0-9]{4}$',
            'DE': r'^[0-9]{5}$',
            'ES': r'^[0-9]{5}$',
            'IT': r'^[0-9]{5}$',
            'GB': r'^[A-Z]{1,2}[0-9R][0-9A-Z]? [0-9][A-Z]{2}$',
            'US': r'^[0-9]{5}(-[0-9]{4})?$'
        }
        
        pattern = postal_patterns.get(country.upper(), r'^.+$')  # Pattern générique par défaut
        
        if re.match(pattern, postal_code.upper()):
            return True, f"Code postal valide pour {country}"
        else:
            return False, f"Format de code postal invalide pour {country}"
    except Exception as e:
        return False, f"Erreur validation code postal: {e}"

def validate_customer_form_advanced(form_data):
    """Validation avancée d'un formulaire client"""
    try:
        errors = {}
        warnings = []
        
        # Validation du type de client et champs dépendants
        customer_type = form_data.get('customer_type', 'individual')
        dependencies = FORM_VALIDATION_CONFIG['field_dependencies']['customer_type'][customer_type]
        
        for field in dependencies:
            if not form_data.get(field):
                errors[field] = f"Champ requis pour le type de client '{customer_type}'"
        
        # Validation SIRET pour les entreprises
        if customer_type == 'business' and form_data.get('siret'):
            valid, message = validate_siret(form_data['siret'])
            if not valid:
                errors['siret'] = message
        
        # Validation téléphone
        if form_data.get('phone'):
            valid, message = validate_phone_international(form_data['phone'])
            if not valid:
                errors['phone'] = message
        
        # Validation email
        if form_data.get('email'):
            valid, message = validate_email_advanced(form_data['email'])
            if not valid:
                errors['email'] = message
        
        # Validation code postal
        if form_data.get('postal_code'):
            country = form_data.get('country', 'FR')
            valid, message = validate_postal_code_format(form_data['postal_code'], country)
            if not valid:
                errors['postal_code'] = message
        
        # Validation de l'adresse avec géocodage
        if (form_data.get('address') and form_data.get('city') and 
            FORM_VALIDATION_CONFIG['business_rules']['address']['geocoding_validation']):
            
            full_address = f"{form_data['address']}, {form_data['city']}"
            if form_data.get('postal_code'):
                full_address += f" {form_data['postal_code']}"
            
            coordinates = geocode_address(full_address)
            if not coordinates:
                warnings.append("Impossible de géolocaliser l'adresse - vérifiez la saisie")
        
        # Validations conditionnelles
        for field, condition_config in FORM_VALIDATION_CONFIG['conditional_validations'].items():
            # Exemple: warranty_end_date doit être après warranty_start_date
            if field == 'warranty_end_date' and form_data.get('warranty_start_date'):
                start_date = form_data.get('warranty_start_date')
                end_date = form_data.get('warranty_end_date')
                if end_date and start_date and end_date <= start_date:
                    errors[field] = "La date de fin de garantie doit être postérieure à la date de début"
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    except Exception as e:
        log_error(f"Erreur validation formulaire avancée: {e}")
        return {
            'valid': False,
            'errors': {'general': f"Erreur de validation: {e}"},
            'warnings': []
        }

# Route API pour validation en temps réel
@bp.route('/api/validate-form', methods=['POST'])
@require_role(['admin', 'manager', 'technician'])
def validate_form_api():
    """API pour validation de formulaire en temps réel"""
    try:
        form_data = request.get_json()
        validation_result = validate_customer_form_advanced(form_data)
        
        return jsonify({
            'success': True,
            'validation': validation_result
        })
    except Exception as e:
        log_error(f"Erreur API validation formulaire: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


class MiniPagination:
    """Lightweight pagination object to mimic Flask-SQLAlchemy / Werkzeug pagination used in templates."""
    def __init__(self, total=0, page=1, per_page=20):
        try:
            self.total = int(total or 0)
        except Exception:
            self.total = 0
        self.page = int(page or 1)
        self.per_page = int(per_page or 20)
        self.pages = max(1, (self.total + self.per_page - 1) // self.per_page)

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def prev_num(self):
        return self.page - 1 if self.has_prev else None

    @property
    def next_num(self):
        return self.page + 1 if self.has_next else None

    def iter_pages(self, left_edge=2, left_current=2, right_current=2, right_edge=2):
        # Simplified iterator that yields all pages; templates handle ellipses if needed
        for p in range(1, self.pages + 1):
            yield p



def _debug(msg):
    try:
        print(f"[DEBUG customers] {msg}")
    except Exception:
        pass


def get_db_connection():
    """Obtient une connexion à la base de données"""
    try:
        return pymysql.connect(**get_db_config())
    except Exception as e:
        log_error(f"Erreur de connexion à la base de données: {e}")
        return None


@bp.route('/')
def index():
    """Page principale des clients"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            stats = {
                'total_customers': 0,
                'active_customers': 0,
                'total_work_orders': 0,
                'total_revenue': 0
            }
            pagination = MiniPagination(total=0, page=1, per_page=20)
            return render_template('customers/index.html', customers=[], stats=stats, pagination=pagination)

        # Build dynamic filters from query params
        args = request.args or {}
        search = (args.get('search') or '').strip()
        customer_type = args.get('customer_type') or ''
        zone = args.get('zone') or ''
        status = args.get('status') or ''
        sort = args.get('sort') or 'name'

        # Detect existing columns to avoid referencing missing schema fields
        try:
            col_cur = conn.cursor()
            col_cur.execute("SHOW COLUMNS FROM customers")
            existing_cols = {r[0] for r in col_cur.fetchall()}
            col_cur.close()
        except Exception:
            existing_cols = set()

        where_clauses = []
        params = []

        if search:
            like = f"%{search}%"
            where_clauses.append("(name LIKE %s OR company LIKE %s OR email LIKE %s OR phone LIKE %s)")
            params.extend([like, like, like, like])

        if customer_type and 'customer_type' in existing_cols:
            where_clauses.append('customer_type = %s')
            params.append(customer_type)

        if zone and 'zone' in existing_cols:
            where_clauses.append('zone = %s')
            params.append(zone)

        if status and 'status' in existing_cols:
            where_clauses.append('status = %s')
            params.append(status)

        # If there's an is_active column and the caller did not filter by status,
        # default to only showing active customers for backward-compatibility.
        if 'is_active' in existing_cols and not status:
            where_clauses.insert(0, 'is_active = TRUE')

        # Map allowed sorts to SQL order clauses
        sort_map = {
            'name': 'name ASC',
            'name_desc': 'name DESC',
            'created_date': 'created_at DESC',
            'last_order': 'created_at DESC'
        }
        order_by = sort_map.get(sort, 'name ASC')

        # Build select list, include optional columns only if present
        select_cols = ['id', 'name', 'company', 'email', 'phone', 'address', 'created_at', 'is_active']
        for opt in ('status', 'customer_type', 'zone'):
            if opt in existing_cols:
                select_cols.append(opt)

        where_sql = ' AND '.join(where_clauses)

        # Log the built query and params for debugging
        try:
            log_info(f"Customers SQL WHERE: {where_sql} params={params}")
        except Exception:
            pass

        # First get total count matching filters (accurate stats & pagination)
        # If no WHERE clauses, don't include the WHERE keyword (avoid SQL syntax error)
        if where_sql:
            count_sql = f"SELECT COUNT(*) AS cnt FROM customers WHERE {where_sql}"
            count_params = params
        else:
            count_sql = "SELECT COUNT(*) AS cnt FROM customers"
            count_params = []
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute(count_sql, count_params)
            row = cursor.fetchone()
            total_matching = int(row['cnt']) if row and 'cnt' in row else 0
        except Exception as e:
            log_error(f"Erreur count customers: {e}")
            total_matching = 0

        # Now fetch the actual rows (could add LIMIT/OFFSET for pagination later)
        base_sql = f"SELECT {', '.join(select_cols)} FROM customers"
        if where_sql:
            base_sql += f" WHERE {where_sql}"
        base_sql += f" ORDER BY {order_by}"
        try:
            cursor.execute(base_sql, params)
            customers = cursor.fetchall()
        except Exception as e:
            log_error(f"Erreur select customers: {e}")
            customers = []
        finally:
            cursor.close()
        # Normalize optional fields so templates can safely access them even when columns are missing
        try:
            for c in customers:
                # ensure keys exist
                for k in ('customer_type', 'status', 'is_active', 'avatar', 'company', 'city', 'email', 'phone', 'vehicles_count', 'work_orders_count', 'total_spent', 'last_order_date'):
                    if k not in c:
                        c[k] = None
        except Exception:
            pass

        # Compute vehicles count for listed customers
        try:
            if customers:
                cust_ids = [c['id'] for c in customers]
                # build placeholders for IN clause
                placeholders = ','.join(['%s'] * len(cust_ids))
                cur2 = conn.cursor(pymysql.cursors.DictCursor)
                cur2.execute(f"SELECT customer_id, COUNT(*) AS cnt FROM vehicles WHERE customer_id IN ({placeholders}) GROUP BY customer_id", cust_ids)
                rows = cur2.fetchall()
                counts = {r['customer_id']: r['cnt'] for r in rows}
                for c in customers:
                    c['vehicles_count'] = counts.get(c['id'], 0)
                cur2.close()
            else:
                # no customers -> nothing to do
                pass
        except Exception as e:
            log_error(f"Erreur comptage véhicules: {e}")
        finally:
            conn.close()

        log_info(f"Récupération de {len(customers)} clients")
        # Statistiques basiques (à adapter selon tes besoins)
        stats = {
            'total_customers': total_matching,
            'active_customers': len([c for c in customers if c.get('is_active', True)]),
            'total_work_orders': 0,  # À calculer si besoin
            'total_revenue': 0      # À calculer si besoin
        }
        pagination = MiniPagination(total=total_matching, page=1, per_page=20)
        # If AJAX request, return only the rendered list fragment as JSON for client-side replacement
        try:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        except Exception:
            is_ajax = False

        if is_ajax:
            try:
                fragment = render_template('customers/_list.html', customers=customers, stats=stats, pagination=pagination)
                stats_fragment = render_template('customers/_stats.html', stats=stats)
                return jsonify({'success': True, 'html': fragment, 'stats_html': stats_fragment, 'total': pagination.total})
            except Exception as e:
                log_error(f"Erreur rendu fragment clients pour AJAX: {e}")
                return jsonify({'success': False, 'error': 'render_error'}), 500

        return render_template('customers/index.html', customers=customers, stats=stats, pagination=pagination)

    except Exception as e:
        log_error(f"Erreur lors de la récupération des clients: {e}")
        flash('Erreur lors du chargement des clients', 'error')
        stats = {
            'total_customers': 0,
            'active_customers': 0,
            'total_work_orders': 0,
            'total_revenue': 0
        }
        pagination = MiniPagination(total=0, page=1, per_page=20)
        return render_template('customers/index.html', customers=[], stats=stats, pagination=pagination)


@bp.route('/add', methods=['GET', 'POST'])
def add_customer():
    """Ajouter un nouveau client"""
    form = CustomerForm()
    if form.validate_on_submit():
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erreur de connexion à la base de données', 'error')
                return render_template('customers/add.html', form=form)

            cursor = conn.cursor()
            # Normalize customer_type values to canonical tokens used in templates
            ct_raw = getattr(form, 'customer_type', None) and form.customer_type.data or None
            ct_map = {
                'particulier': 'individual',
                'entreprise': 'company',
                'government': 'government',
                'individual': 'individual',
                'company': 'company'
            }
            customer_type_value = ct_map.get(ct_raw, ct_raw)

            cursor.execute("""
                INSERT INTO customers (name, company, email, phone, address, siret, status, customer_type, postal_code, city, country, billing_address, payment_terms, notes, tax_number, preferred_contact_method, zone, created_at, updated_at, is_active)
                VALUES (%(name)s, %(company)s, %(email)s, %(phone)s, %(address)s, %(siret)s, %(status)s, %(customer_type)s, %(postal_code)s, %(city)s, %(country)s, %(billing_address)s, %(payment_terms)s, %(notes)s, %(tax_number)s, %(preferred_contact_method)s, %(zone)s, NOW(), NOW(), TRUE)
            """, {
                'name': form.name.data,
                'company': form.company.data,
                'email': form.email.data,
                'phone': form.phone.data,
                'address': form.address.data,
                'siret': getattr(form, 'siret', None) and form.siret.data or None,
                'status': getattr(form, 'status', None) and form.status.data or None,
                'customer_type': customer_type_value,
                'postal_code': getattr(form, 'postal_code', None) and form.postal_code.data or None,
                'city': getattr(form, 'city', None) and form.city.data or None,
                'country': getattr(form, 'country', None) and form.country.data or None,
                'billing_address': getattr(form, 'billing_address', None) and form.billing_address.data or None,
                'payment_terms': getattr(form, 'payment_terms', None) and form.payment_terms.data or None,
                'notes': getattr(form, 'notes', None) and form.notes.data or None,
                'tax_number': getattr(form, 'tax_number', None) and form.tax_number.data or None,
                'preferred_contact_method': getattr(form, 'preferred_contact_method', None) and form.preferred_contact_method.data or None,
                'zone': getattr(form, 'zone', None) and form.zone.data or None
            })

            customer_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()

            log_info(f"Nouveau client créé: {form.name.data} (ID: {customer_id})")
            flash('Client ajouté avec succès', 'success')
            return redirect(url_for('customers.index'))
        except pymysql.IntegrityError as e:
            log_error(f"Erreur d'intégrité lors de l'ajout du client: {e}")
            flash('Un client avec cet email existe déjà', 'error')
        except Exception as e:
            log_error(f"Erreur lors de l'ajout du client: {e}")
            flash('Erreur lors de l\'ajout du client', 'error')
    return render_template('customers/add.html', form=form)


@bp.route('/<int:customer_id>')
def view_customer(customer_id):
    """Voir les détails d'un client"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            return redirect(url_for('customers.index'))

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Récupérer les informations du client
        cursor.execute("""
            SELECT * FROM customers WHERE id = %s
        """, (customer_id,))

        customer = cursor.fetchone()
        # Ensure optional keys exist to avoid template runtime errors when the column is absent
        try:
            if customer is not None:
                if 'customer_type' not in customer:
                    customer['customer_type'] = None
        except Exception:
            pass
        if not customer:
            cursor.close()
            conn.close()
            flash('Client non trouvé', 'error')
            return redirect(url_for('customers.index'))

        # Récupérer les bons de travail associés
        cursor.execute("""
            SELECT id, claim_number, description, status, priority, created_at, scheduled_date
            FROM work_orders 
            WHERE customer_id = %s 
            ORDER BY created_at DESC
        """, (customer_id,))

        work_orders = cursor.fetchall()

        cursor.close()
        conn.close()

        # Minimal stats and auxiliary data expected by the template
        stats = {
            'total_work_orders': len(work_orders),
            'completed_work_orders': len([w for w in work_orders if w.get('status') == 'completed']),
            'total_spent': 0,
            # Avoid calling custom filters in contexts where they may not be registered
            'last_order_date': None
        }

        # Provide commonly-used lists/objects to avoid template errors when data is missing
        recent_work_orders = work_orders[:5]
        recent_activities = []
        customer_contacts = []
        monthly_orders_data = []
        priority_distribution = []

        # Load vehicles for this customer
        vehicles = []
        try:
            conn2 = get_db_connection()
            if conn2:
                cur2 = conn2.cursor(pymysql.cursors.DictCursor)
                cur2.execute("SELECT id, make, model, year, vin, license_plate, notes FROM vehicles WHERE customer_id = %s ORDER BY created_at DESC", (customer_id,))
                vehicles = cur2.fetchall()
                cur2.close()
                conn2.close()
        except Exception:
            vehicles = []

        return render_template('customers/view.html', customer=customer, work_orders=work_orders,
                               stats=stats, recent_work_orders=recent_work_orders,
                               recent_activities=recent_activities, customer_contacts=customer_contacts,
                               monthly_orders_data=monthly_orders_data, priority_distribution=priority_distribution,
                               vehicles=vehicles)

    except Exception as e:
        log_error(f"Erreur lors de la récupération du client {customer_id}: {e}")
        flash('Erreur lors du chargement du client', 'error')
        return redirect(url_for('customers.index'))


@bp.route('/<int:customer_id>/contacts/create', methods=['POST'])
def create_contact(customer_id):
    """Create a contact for a customer. AJAX-aware (returns JSON) or fallback to redirect."""
    name = request.form.get('name')
    role = request.form.get('role')
    email = request.form.get('email')
    phone = request.form.get('phone')
    try:
        conn = get_db_connection()
        if not conn:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'DB connection error'}), 500
            flash('Erreur de connexion DB', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id))

        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO contacts (customer_id, name, role, email, phone, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (customer_id, name, role, email, phone))
            conn.commit()
            cid = cursor.lastrowid
            # fetch created
            try:
                cursor.execute("SELECT id, name, role, email, phone FROM contacts WHERE id = %s", (cid,))
                created = cursor.fetchone()
            except Exception:
                created = None
        conn.close()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'id': cid, 'contact': created})
        flash('Contact ajouté', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))
    except Exception as e:
        log_error(f"Erreur création contact: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur création contact'}), 500
        flash('Erreur création contact', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))


@bp.route('/contacts/<int:contact_id>/update', methods=['POST'])
def update_contact(contact_id):
    """Update a contact. Expects form data and customer_id in form for redirect fallback."""
    name = request.form.get('name')
    role = request.form.get('role')
    email = request.form.get('email')
    phone = request.form.get('phone')
    customer_id = request.form.get('customer_id')
    try:
        conn = get_db_connection()
        if not conn:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'DB connection error'}), 500
            flash('Erreur de connexion DB', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))

        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE contacts SET name=%s, role=%s, email=%s, phone=%s, updated_at=NOW()
                WHERE id = %s
            """, (name, role, email, phone, contact_id))
            conn.commit()
            try:
                cursor.execute("SELECT id, name, role, email, phone FROM contacts WHERE id = %s", (contact_id,))
                updated = cursor.fetchone()
            except Exception:
                updated = None
        conn.close()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'contact': updated})
        flash('Contact modifié', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))
    except Exception as e:
        log_error(f"Erreur update contact: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur mise à jour'}), 500
        flash('Erreur mise à jour contact', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))


@bp.route('/contacts/<int:contact_id>/delete', methods=['POST'])
def delete_contact(contact_id):
    """Delete a contact. Expects customer_id in form for redirect fallback."""
    customer_id = request.form.get('customer_id') or request.args.get('customer_id')
    try:
        conn = get_db_connection()
        if not conn:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'DB connection error'}), 500
            flash('Erreur de connexion DB', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM contacts WHERE id = %s", (contact_id,))
            conn.commit()
        conn.close()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True})
        flash('Contact supprimé', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))
    except Exception as e:
        log_error(f"Erreur suppression contact: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur suppression'}), 500
        flash('Erreur suppression contact', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))


@bp.route('/<int:customer_id>/addresses/create', methods=['POST'])
def create_address(customer_id):
    """Create a delivery address for a customer with geolocation support. AJAX-aware."""
    label = request.form.get('label')
    street = request.form.get('street')
    postal_code = request.form.get('postal_code')
    city = request.form.get('city')
    country = request.form.get('country')
    phone = request.form.get('phone')
    
    # Nouvelles données géospatiales
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    delivery_window_start = request.form.get('delivery_window_start')
    delivery_window_end = request.form.get('delivery_window_end')
    access_instructions = request.form.get('access_instructions')
    delivery_zone = request.form.get('delivery_zone')
    
    try:
        conn = get_db_connection()
        if not conn:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'DB connection error'}), 500
            flash('Erreur de connexion DB', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id))
        
        with conn.cursor() as cursor:
            # Géocoder l'adresse si les coordonnées ne sont pas fournies
            if not latitude or not longitude:
                try:
                    coords = geocode_address(f"{street}, {postal_code} {city}, {country}")
                    if coords:
                        latitude, longitude = coords
                except Exception as e:
                    log_warning(f"Géocodage échoué pour adresse {customer_id}: {e}")
            
            cursor.execute("""
                INSERT INTO customer_addresses (
                    customer_id, label, street, postal_code, city, country, phone,
                    latitude, longitude, delivery_window_start, delivery_window_end,
                    access_instructions, delivery_zone, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                customer_id, label, street, postal_code, city, country, phone,
                latitude, longitude, delivery_window_start, delivery_window_end,
                access_instructions, delivery_zone
            ))
            conn.commit()
            aid = cursor.lastrowid
            try:
                cursor.execute("SELECT id, label, street, postal_code, city, country, phone FROM addresses WHERE id = %s", (aid,))
                created = cursor.fetchone()
            except Exception:
                created = None
        conn.close()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'id': aid, 'address': created})
        flash('Adresse ajoutée', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))
    except Exception as e:
        log_error(f"Erreur création adresse: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur création adresse'}), 500
        flash('Erreur création adresse', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))


@bp.route('/addresses/<int:address_id>/update', methods=['POST'])
def update_address(address_id):
    label = request.form.get('label')
    street = request.form.get('street')
    postal_code = request.form.get('postal_code')
    city = request.form.get('city')
    country = request.form.get('country')
    phone = request.form.get('phone')
    customer_id = request.form.get('customer_id')
    try:
        conn = get_db_connection()
        if not conn:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'DB connection error'}), 500
            flash('Erreur de connexion DB', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE addresses SET label=%s, street=%s, postal_code=%s, city=%s, country=%s, phone=%s, updated_at=NOW()
                WHERE id = %s
            """, (label, street, postal_code, city, country, phone, address_id))
            conn.commit()
            try:
                cursor.execute("SELECT id, label, street, postal_code, city, country, phone FROM addresses WHERE id = %s", (address_id,))
                updated = cursor.fetchone()
            except Exception:
                updated = None
        conn.close()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'address': updated})
        flash('Adresse modifiée', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))
    except Exception as e:
        log_error(f"Erreur update adresse: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur mise à jour'}), 500
        flash('Erreur mise à jour adresse', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))


@bp.route('/addresses/<int:address_id>/delete', methods=['POST'])
def delete_address(address_id):
    customer_id = request.form.get('customer_id') or request.args.get('customer_id')
    try:
        conn = get_db_connection()
        if not conn:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'DB connection error'}), 500
            flash('Erreur de connexion DB', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM addresses WHERE id = %s", (address_id,))
            conn.commit()
        conn.close()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True})
        flash('Adresse supprimée', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))
    except Exception as e:
        log_error(f"Erreur suppression adresse: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur suppression'}), 500
        flash('Erreur suppression adresse', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))


# Backwards-compatible alias: some templates call `customers.view` with param `id`
@bp.route('/<int:id>/view')
def view(id):
    return redirect(url_for('customers.view_customer', customer_id=id))


@bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
def edit_customer(customer_id):
    """Modifier un client"""
    if request.method == 'POST':
        try:
            # Accept JSON or form-encoded data
            data = request.get_json() if request.is_json else request.form

            conn = get_db_connection()
            if not conn:
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Erreur de connexion à la base de données'})
                else:
                    flash('Erreur de connexion à la base de données', 'error')
                    return redirect(url_for('customers.view_customer', customer_id=customer_id))

            # Detect existing columns to avoid updating non-existent fields
            try:
                col_cur = conn.cursor()
                col_cur.execute("SHOW COLUMNS FROM customers")
                existing_cols = {r[0] for r in col_cur.fetchall()}
                col_cur.close()
            except Exception:
                existing_cols = set()

            # Build a dynamic list of fields to set depending on existing columns
            field_values = {
                'name': data.get('name'),
                'company': data.get('company') or None,
                'siret': data.get('siret') or None,
                'email': data.get('email') or None,
                'phone': data.get('phone') or None,
                'address': data.get('address') or None,
                'postal_code': data.get('postal_code') or None,
                'city': data.get('city') or None,
                'country': data.get('country') or None,
                'billing_address': data.get('billing_address') or None,
                'payment_terms': data.get('payment_terms') or None,
                'notes': data.get('notes') or None,
                'tax_number': data.get('tax_number') or None,
                'preferred_contact_method': data.get('preferred_contact_method') or None,
                'zone': data.get('zone') or None,
                'status': data.get('status') or None,
            }

            # Optionally include customer_type only if column exists
            include_customer_type = 'customer_type' in existing_cols
            if include_customer_type:
                # Normalize French tokens to canonical tokens if present
                ct_raw = data.get('customer_type')
                ct_map = {'particulier': 'individual', 'entreprise': 'company', 'government': 'government', 'individual': 'individual', 'company': 'company'}
                field_values['customer_type'] = ct_map.get(ct_raw, ct_raw)

            # Build SET clause and params dynamically
            set_clauses = []
            params = {}
            for key, val in field_values.items():
                # Skip customer_type if column not present
                if key == 'customer_type' and not include_customer_type:
                    continue
                set_clauses.append(f"{key} = %({key})s")
                params[key] = val

            params['id'] = customer_id

            set_sql = ',\n                    '.join(set_clauses) if set_clauses else ''
            if set_sql:
                sql = f"UPDATE customers\n                SET {set_sql},\n                    updated_at = NOW()\n                WHERE id = %(id)s"
            else:
                # Nothing to update except updated_at
                sql = "UPDATE customers SET updated_at = NOW() WHERE id = %(id)s"

            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            cursor.close()
            conn.close()

            log_info(f"Client modifié: {data.get('name')} (ID: {customer_id})")

            # Decide next action: normal view or create work order
            create_order_flag = False
            try:
                create_order_flag = str(data.get('save_and_add_order', '')).strip() in ['1', 'true', 'True']
            except Exception:
                create_order_flag = False

            next_url = url_for('customers.view_customer', customer_id=customer_id)
            if create_order_flag:
                next_url = url_for('work_orders.create_work_order', customer_id=customer_id)

            if request.is_json:
                return jsonify({'success': True, 'message': 'Client modifié avec succès', 'next': next_url})
            else:
                flash('Client modifié avec succès', 'success')
                return redirect(next_url)

        except Exception as e:
            log_error(f"Erreur lors de la modification du client {customer_id}: {e}")
            if request.is_json:
                return jsonify({'success': False, 'message': 'Erreur lors de la modification du client'})
            else:
                flash('Erreur lors de la modification du client', 'error')
                return redirect(url_for('customers.view_customer', customer_id=customer_id))

    # GET request - afficher le formulaire de modification
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            return redirect(url_for('customers.index'))

        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM customers WHERE id = %s", (customer_id,))
        customer = cursor.fetchone()
        _debug(f"Fetched customer for edit GET: {customer}")
        cursor.close()
        conn.close()

        if not customer:
            flash('Client non trouvé', 'error')
            return redirect(url_for('customers.index'))

        # Instantiate a form prefilled with customer data for the template
        try:
            form = CustomerForm(data=customer)
        except Exception:
            form = CustomerForm()

        return render_template('customers/edit.html', customer=customer, form=form)

    except Exception as e:
        log_error(f"Erreur lors du chargement du formulaire d'édition pour le client {customer_id}: {e}")
        flash('Erreur lors du chargement du formulaire', 'error')
        return redirect(url_for('customers.index'))


@bp.route('/<int:customer_id>/delete', methods=['POST'])
def delete_customer(customer_id):
    """Supprimer un client (soft delete)"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Erreur de connexion à la base de données'})

        cursor = conn.cursor()
        cursor.execute("""
            UPDATE customers 
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = %s
        """, (customer_id,))

        conn.commit()
        cursor.close()
        conn.close()

        log_info(f"Client supprimé (soft delete): ID {customer_id}")

        # Determine if this was an AJAX request (X-Requested-With) or JSON
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({'success': True, 'message': 'Client supprimé avec succès', 'id': customer_id})
        else:
            flash('Client supprimé avec succès', 'success')
            return redirect(url_for('customers.index'))

    except Exception as e:
        log_error(f"Erreur lors de la suppression du client {customer_id}: {e}")
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({'success': False, 'message': 'Erreur lors de la suppression du client'}), 500
        else:
            flash('Erreur lors de la suppression du client', 'error')
            return redirect(url_for('customers.index'))


# Backwards-compatible aliases used by templates
@bp.route('/<int:id>/actions/delete', methods=['POST'], endpoint='delete')
def delete_alias(id):
    return delete_customer(id)


@bp.route('/<int:id>/export', methods=['GET'], endpoint='export_data')
def export_alias(id):
    # Minimal stub: redirect to view for now
    return redirect(url_for('customers.view_customer', customer_id=id))


def _register_dummy_endpoints(state):
    """When the blueprint is registered on the app, create minimal dummy endpoints
    used by templates to avoid url_for errors in environments where other blueprints
    (like 'quotes') may not be registered during tests or limited contexts."""
    app = state.app
    try:
        # Provide a minimal quotes.add endpoint
        if 'quotes.add' not in app.view_functions:
            app.add_url_rule('/quotes/add', endpoint='quotes.add', view_func=lambda: redirect(url_for('customers.index')))
        # Provide minimal appointment and parts endpoints used by templates
        if 'appointments.create' not in app.view_functions:
            app.add_url_rule('/appointments/create', endpoint='appointments.create', view_func=lambda customer_id=None: redirect(url_for('work_orders.create_work_order', customer_id=customer_id or '')))
        if 'parts.create_order' not in app.view_functions:
            app.add_url_rule('/parts/create', endpoint='parts.create_order', view_func=lambda customer_id=None: redirect(url_for('work_orders.create_work_order', customer_id=customer_id or '')))
    except Exception:
        pass


bp.record(_register_dummy_endpoints)


@bp.route('/alt')
def index_alt():
    """Alternative UI for customers list (compact table + quick actions)."""
    try:
        # params
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        q = request.args.get('search', '').strip()

        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            stats = {'total_customers': 0, 'active_customers': 0, 'total_work_orders': 0, 'total_revenue': 0}
            class DummyPagination:
                total = 0
                prev_num = None
                next_num = None
                pages = 1
            pagination = DummyPagination()
            return render_template('customers/index_alt.html', customers=[], stats=stats, pagination=pagination)

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        where_clauses = ["is_active = TRUE"]
        params = []
        if q:
            where_clauses.append("(name LIKE %s OR company LIKE %s OR email LIKE %s OR phone LIKE %s)")
            like_q = f"%{q}%"
            params.extend([like_q, like_q, like_q, like_q])

        where_sql = " AND ".join(where_clauses)

        # total count for pagination
        cursor.execute(f"SELECT COUNT(*) as total FROM customers WHERE {where_sql}", params)
        total = cursor.fetchone().get('total', 0)

        # paging
        offset = (page - 1) * per_page
        params_page = params[:]  # copy
        params_page.extend([per_page, offset])

        cursor.execute(f"SELECT id, name, company, email, phone, city, created_at, is_active FROM customers WHERE {where_sql} ORDER BY name ASC LIMIT %s OFFSET %s", params_page)
        customers = cursor.fetchall()

        # vehicles counts for the page
        try:
            if customers:
                cust_ids = [c['id'] for c in customers]
                placeholders = ','.join(['%s'] * len(cust_ids))
                cur2 = conn.cursor(pymysql.cursors.DictCursor)
                cur2.execute(f"SELECT customer_id, COUNT(*) AS cnt FROM vehicles WHERE customer_id IN ({placeholders}) GROUP BY customer_id", cust_ids)
                rows = cur2.fetchall()
                counts = {r['customer_id']: r['cnt'] for r in rows}
                for c in customers:
                    c['vehicles_count'] = counts.get(c['id'], 0)
                cur2.close()
        except Exception:
            for c in customers:
                c['vehicles_count'] = 0

        # basic stats
        stats = {
            'total_customers': total,
            'active_customers': total,
            'total_work_orders': 0,
            'total_revenue': 0
        }

        # simple Pagination object
        class Pagination:
            def __init__(self, page, per_page, total):
                self.page = page
                self.per_page = per_page
                self.total = total

            @property
            def pages(self):
                return max(1, (self.total + self.per_page - 1) // self.per_page)

            @property
            def has_prev(self):
                return self.page > 1

            @property
            def has_next(self):
                return self.page < self.pages

            @property
            def prev_num(self):
                return self.page - 1 if self.has_prev else None

            @property
            def next_num(self):
                return self.page + 1 if self.has_next else None

            def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
                last = 0
                for num in range(1, self.pages + 1):
                    if num <= left_edge or (num >= self.page - left_current and num <= self.page + right_current) or num > self.pages - right_edge:
                        if last + 1 != num:
                            yield None
                        yield num
                        last = num

        pagination = Pagination(page, per_page, total)

        cursor.close()
        conn.close()

        return render_template('customers/index_alt.html', customers=customers, stats=stats, pagination=pagination)

    except Exception as e:
        log_error(f"Erreur index_alt: {e}")
        flash('Erreur lors du chargement de la page', 'error')
        return redirect(url_for('customers.index'))


@bp.route('/api/search')
def api_search():
    """API de recherche de clients"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'customers': []})

        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Erreur de connexion à la base de données'}), 500

        cursor = conn.cursor(pymysql.cursors.DictCursor)
        search_query = f"%{query}%"
        cursor.execute("""
            SELECT id, name, company, email, phone
            FROM customers 
            WHERE is_active = TRUE 
            AND (name LIKE %s OR company LIKE %s OR email LIKE %s OR phone LIKE %s)
            ORDER BY name ASC
            LIMIT 20
        """, (search_query, search_query, search_query, search_query))

        customers = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({'customers': customers})

    except Exception as e:
        log_error(f"Erreur lors de la recherche de clients: {e}")
        return jsonify({'error': 'Erreur lors de la recherche'}), 500


# ===== NOUVELLES FONCTIONNALITÉS SPRINT 1-2 =====

@bp.route('/<int:customer_id>/timeline')
def customer_timeline(customer_id):
    """Récupère la timeline unifiée d'un client avec filtres avancés"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        activity_type = request.args.get('type')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        actor_type = request.args.get('actor_type')
        export_format = request.args.get('export')  # csv, json, pdf
        
        conn = get_db_connection()
        if not conn:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'Erreur de connexion DB'}), 500
            flash('Erreur de connexion à la base de données', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id))
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Configuration des tables autorisées (sécurisée et extensible)
        ALLOWED_TABLES_CONFIG = {
            'work_orders': {
                'display_field': 'title',
                'secondary_fields': ['status', 'priority'],
                'icon': 'fas fa-wrench',
                'color': 'primary'
            },
            'invoices': {
                'display_field': 'invoice_number',
                'secondary_fields': ['amount', 'status'],
                'icon': 'fas fa-file-invoice',
                'color': 'success'
            },
            'quotes': {
                'display_field': 'quote_number',
                'secondary_fields': ['amount', 'status'],
                'icon': 'fas fa-file-signature',
                'color': 'info'
            },
            'appointments': {
                'display_field': 'title',
                'secondary_fields': ['scheduled_at', 'status'],
                'icon': 'fas fa-calendar',
                'color': 'warning'
            },
            'customer_documents': {
                'display_field': 'title',
                'secondary_fields': ['document_type', 'is_signed'],
                'icon': 'fas fa-file',
                'color': 'secondary'
            },
            'customer_payment_methods': {
                'display_field': 'label',
                'secondary_fields': ['method_type', 'provider'],
                'icon': 'fas fa-credit-card',
                'color': 'primary'
            }
        }
        
        # Construction de la requête avec filtres combinés
        query = """
            SELECT ca.*, u.name as actor_name 
            FROM customer_activity ca
            LEFT JOIN users u ON ca.actor_id = u.id AND ca.actor_type = 'user'
            WHERE ca.customer_id = %s
        """
        params = [customer_id]
        
        # Filtres avancés
        if activity_type:
            query += " AND ca.activity_type = %s"
            params.append(activity_type)
        
        if date_from:
            query += " AND ca.created_at >= %s"
            params.append(date_from)
        
        if date_to:
            query += " AND ca.created_at <= %s"
            params.append(date_to + ' 23:59:59')
        
        if actor_type:
            query += " AND ca.actor_type = %s"
            params.append(actor_type)
        
        # Count total for pagination
        count_query = query.replace("SELECT ca.*, u.name as actor_name", "SELECT COUNT(*) as count")
        cursor.execute(count_query, params)
        total = cursor.fetchone()['count']
        
        # Get results (all for export, paginated for display)
        order_query = query + " ORDER BY ca.created_at DESC"
        if not export_format:
            order_query += " LIMIT %s OFFSET %s"
            offset = (page - 1) * per_page
            params.extend([per_page, offset])
        
        cursor.execute(order_query, params)
        activities = cursor.fetchall()
        
        # Enrichissement contextuel avancé des activités
        for activity in activities:
            if activity['reference_id'] and activity['reference_table']:
                table_name = activity['reference_table']
                if table_name in ALLOWED_TABLES_CONFIG:
                    try:
                        # Configuration pour cette table
                        table_config = ALLOWED_TABLES_CONFIG[table_name]
                        
                        # Construire les champs à récupérer
                        fields = [table_config['display_field']] + table_config['secondary_fields']
                        field_list = ', '.join([f'`{field}`' for field in fields if field])
                        
                        cursor.execute(f"SELECT id, {field_list} FROM `{table_name}` WHERE id = %s", 
                                     [activity['reference_id']])
                        reference_data = cursor.fetchone()
                        
                        if reference_data:
                            # Enrichissement avec formatage contextuel
                            activity['reference_data'] = reference_data
                            activity['reference_config'] = table_config
                            
                            # Formatage spécifique par type
                            if table_name == 'invoices' and 'amount' in reference_data:
                                activity['formatted_amount'] = f"{float(reference_data['amount']):.2f}€"
                            elif table_name == 'appointments' and 'scheduled_at' in reference_data:
                                from datetime import datetime
                                if reference_data['scheduled_at']:
                                    dt = reference_data['scheduled_at']
                                    if isinstance(dt, str):
                                        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                                    activity['formatted_date'] = dt.strftime('%d/%m/%Y %H:%M')
                            
                    except Exception as e:
                        log_error(f"Erreur enrichissement référence {table_name}: {e}")
                        activity['reference_error'] = True
        
        cursor.close()
        conn.close()
        
        # Gestion de l'export
        if export_format:
            return export_timeline(activities, customer_id, export_format)
        
        pagination = MiniPagination(total=total, page=page, per_page=per_page)
        
        # Return JSON if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({
                'success': True,
                'activities': activities,
                'total': total,
                'pagination': {
                    'total': pagination.total,
                    'page': pagination.page,
                    'per_page': pagination.per_page,
                    'pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            })
        
        return render_template(
            'customers/timeline.html',
            customer_id=customer_id,
            activities=activities,
            pagination=pagination,
            allowed_tables=ALLOWED_TABLES_CONFIG
        )
        
    except Exception as e:
        log_error(f"Erreur timeline: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur timeline'}), 500
        flash('Erreur chargement timeline', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))


def export_timeline(activities, customer_id, format_type):
    """Exporte la timeline en différents formats"""
    try:
        if format_type == 'csv':
            import csv
            import io
            from flask import make_response
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # En-têtes CSV
            writer.writerow([
                'Date', 'Type', 'Description', 'Acteur', 'Type Acteur', 
                'Référence Table', 'Référence ID', 'Détails'
            ])
            
            # Données
            for activity in activities:
                writer.writerow([
                    activity.get('created_at', ''),
                    activity.get('activity_type', ''),
                    activity.get('description', ''),
                    activity.get('actor_name', ''),
                    activity.get('actor_type', ''),
                    activity.get('reference_table', ''),
                    activity.get('reference_id', ''),
                    activity.get('details', '')
                ])
            
            output.seek(0)
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=timeline_client_{customer_id}.csv'
            return response
            
        elif format_type == 'json':
            from flask import make_response
            import json
            
            # Préparer les données (convertir les objets datetime)
            export_data = []
            for activity in activities:
                activity_dict = dict(activity)
                # Convertir les datetime en string
                for key, value in activity_dict.items():
                    if hasattr(value, 'isoformat'):
                        activity_dict[key] = value.isoformat()
                export_data.append(activity_dict)
            
            response = make_response(json.dumps(export_data, indent=2, ensure_ascii=False))
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Disposition'] = f'attachment; filename=timeline_client_{customer_id}.json'
            return response
            
        else:
            return jsonify({'success': False, 'message': 'Format d\'export non supporté'}), 400
            
    except Exception as e:
        log_error(f"Erreur export timeline: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de l\'export'}), 500

@bp.route('/<int:customer_id>/profile', methods=['GET', 'PATCH'])
def customer_profile(customer_id):
    """Gère le profil enrichi d'un client (language_code, timezone, segments)"""
    if request.method == 'GET':
        try:
            conn = get_db_connection()
            if not conn:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                    return jsonify({'success': False, 'message': 'Erreur de connexion DB'}), 500
                flash('Erreur de connexion à la base de données', 'error')
                return redirect(url_for('customers.view_customer', customer_id=customer_id))
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("""
                SELECT language_code, timezone, segments, privacy_level, preferred_contact_channel, tax_exempt
                FROM customers WHERE id = %s
            """, [customer_id])
            profile = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not profile:
                return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
            
            # Parse segments JSON
            if profile['segments']:
                try:
                    profile['segments'] = json.loads(profile['segments'])
                except:
                    profile['segments'] = []
            else:
                profile['segments'] = []
            
            return jsonify({'success': True, 'profile': profile})
        except Exception as e:
            log_error(f"Erreur récupération profil: {e}")
            return jsonify({'success': False, 'message': 'Erreur récupération profil'}), 500
    
    else:  # PATCH
        try:
            data = request.get_json() if request.is_json else request.form
            
            language_code = data.get('language_code')
            timezone = data.get('timezone')
            segments = data.get('segments')
            privacy_level = data.get('privacy_level')
            preferred_contact_channel = data.get('preferred_contact_channel')
            tax_exempt = data.get('tax_exempt') == 'true'
            
            # Validate segments format
            if segments and isinstance(segments, str):
                try:
                    segments = json.loads(segments)
                except:
                    return jsonify({'success': False, 'message': 'Format segments invalide'}), 400
            
            if segments and isinstance(segments, list):
                segments_json = json.dumps(segments)
            else:
                segments_json = None
            
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion DB'}), 500
            
            cursor = conn.cursor()
            
            # Update customer profile
            cursor.execute("""
                UPDATE customers SET
                language_code = %s,
                timezone = %s,
                segments = %s,
                privacy_level = %s,
                preferred_contact_channel = %s,
                tax_exempt = %s,
                updated_at = NOW()
                WHERE id = %s
            """, [
                language_code, timezone, segments_json, privacy_level,
                preferred_contact_channel, tax_exempt, customer_id
            ])
            
            # Record activity
            cursor.execute("""
                INSERT INTO customer_activity
                (customer_id, activity_type, title, description, actor_type, created_at)
                VALUES (%s, 'system', %s, %s, 'user', NOW())
            """, [
                customer_id, "Profil mis à jour", 
                f"Langue: {language_code}, Fuseau: {timezone}, Segments: {segments}"
            ])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Profil mis à jour avec succès'
            })
        except Exception as e:
            log_error(f"Erreur mise à jour profil: {e}")
            return jsonify({'success': False, 'message': 'Erreur mise à jour profil'}), 500

@bp.route('/<int:customer_id>/consents', methods=['GET'])
def get_customer_consents(customer_id):
    """Récupère les consentements d'un client"""
    try:
        conn = get_db_connection()
        if not conn:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'Erreur de connexion DB'}), 500
            flash('Erreur de connexion à la base de données', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id))
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT cc.*, u.name as collector_name
            FROM customer_consents cc
            LEFT JOIN users u ON cc.collected_by = u.id
            WHERE cc.customer_id = %s
            ORDER BY cc.consent_type, cc.created_at DESC
        """, [customer_id])
        consents = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'consents': consents})
        
        return render_template('customers/consents.html', customer_id=customer_id, consents=consents)
    except Exception as e:
        log_error(f"Erreur récupération consentements: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur récupération consentements'}), 500
        flash('Erreur chargement consentements', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))

@bp.route('/<int:customer_id>/consents', methods=['POST'])
def update_customer_consent(customer_id):
    """Ajoute ou met à jour un consentement client"""
    try:
        data = request.get_json() if request.is_json else request.form
        consent_type = data.get('consent_type')
        is_granted = bool(data.get('is_granted'))
        source = data.get('source', 'web_form')
        
        if not consent_type:
            return jsonify({'success': False, 'message': 'Type de consentement requis'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Erreur de connexion DB'}), 500
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Check if consent exists
        cursor.execute("""
            SELECT id, version, is_granted FROM customer_consents
            WHERE customer_id = %s AND consent_type = %s
            ORDER BY version DESC LIMIT 1
        """, [customer_id, consent_type])
        existing = cursor.fetchone()
        
        # Capture current user if available
        user_id = 1  # Default user for now, TODO: implement proper user session
        
        # Capture IP address
        ip_address = request.remote_addr
        
        if existing:
            new_version = existing['version'] + 1
            # Skip if no change
            if existing['is_granted'] == is_granted:
                return jsonify({'success': True, 'message': 'Aucun changement', 'consent': existing})
            
            # Update existing consent
            cursor.execute("""
                UPDATE customer_consents SET
                is_granted = %s,
                source = %s,
                ip_address = %s,
                collected_by = %s,
                version = %s,
                granted_at = IF(%s, NOW(), granted_at),
                revoked_at = IF(%s, NOW(), revoked_at),
                updated_at = NOW()
                WHERE id = %s
            """, [is_granted, source, ip_address, user_id, new_version, 
                  is_granted, not is_granted, existing['id']])
            consent_id = existing['id']
        else:
            # Create new consent
            cursor.execute("""
                INSERT INTO customer_consents
                (customer_id, consent_type, is_granted, source, ip_address, 
                 collected_by, version, granted_at)
                VALUES (%s, %s, %s, %s, %s, %s, 1, IF(%s, NOW(), NULL))
            """, [customer_id, consent_type, is_granted, source, 
                  ip_address, user_id, is_granted])
            consent_id = cursor.lastrowid
            new_version = 1
        
        # Record history
        cursor.execute("""
            INSERT INTO customer_consent_history
            (consent_id, customer_id, consent_type, is_granted, source, 
             ip_address, collected_by, version, action, action_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, [consent_id, customer_id, consent_type, is_granted, source, 
              ip_address, user_id, new_version, 'grant' if is_granted else 'revoke'])
        
        # Create activity entry
        action = "Consentement accordé" if is_granted else "Consentement révoqué"
        cursor.execute("""
            INSERT INTO customer_activity
            (customer_id, activity_type, reference_id, reference_table, 
             title, description, actor_id, actor_type, created_at)
            VALUES (%s, 'consent', %s, 'customer_consents', %s, %s, %s, 'user', NOW())
        """, [customer_id, consent_id, f"{action}: {consent_type}", 
              f"Source: {source}", user_id])
        
        conn.commit()
        
        # Fetch updated consent
        cursor.execute("""
            SELECT cc.*, u.name as collector_name
            FROM customer_consents cc
            LEFT JOIN users u ON cc.collected_by = u.id
            WHERE cc.id = %s
        """, [consent_id])
        updated_consent = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': action,
            'consent': updated_consent
        })
    except Exception as e:
        log_error(f"Erreur mise à jour consentement: {e}")
        return jsonify({'success': False, 'message': 'Erreur mise à jour consentement'}), 500

def has_valid_consent(customer_id, consent_type):
    """Vérifie si un client a donné son consentement pour un type spécifique"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT is_granted FROM customer_consents
            WHERE customer_id = %s AND consent_type = %s
            AND is_granted = TRUE
            AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY version DESC LIMIT 1
        """, [customer_id, consent_type])
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result is not None
    except Exception as e:
        log_error(f"Erreur vérification consentement: {e}")
        return False

def log_customer_activity(customer_id, activity_type, title, description=None, 
                         reference_id=None, reference_table=None, actor_id=None):
    """Helper function pour enregistrer une activité client"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customer_activity
            (customer_id, activity_type, reference_id, reference_table, 
             title, description, actor_id, actor_type, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, [customer_id, activity_type, reference_id, reference_table,
              title, description, actor_id, 'user' if actor_id else 'system'])
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        log_error(f"Erreur enregistrement activité: {e}")
        return False

@bp.route('/<int:customer_id>/360')
def customer_360(customer_id):
    """Vue Client 360 complète et enrichie avec données financières et documents"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            return redirect(url_for('customers.index'))
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get customer info with new fields
        cursor.execute("""
            SELECT *, 
                   CASE WHEN segments IS NOT NULL THEN segments ELSE '[]' END as segments_json
            FROM customers WHERE id = %s
        """, [customer_id])
        customer = cursor.fetchone()
        
        if not customer:
            flash('Client non trouvé', 'error')
            return redirect(url_for('customers.index'))
        
        # Parse segments
        try:
            customer['segments'] = json.loads(customer['segments_json'])
        except:
            customer['segments'] = []
        
        # ===== DONNÉES FINANCIÈRES INTÉGRÉES =====
        # Profil financier
        cursor.execute("""
            SELECT * FROM customer_finances WHERE customer_id = %s
        """, [customer_id])
        financial_profile = cursor.fetchone()
        
        # Résumé des méthodes de paiement
        cursor.execute("""
            SELECT COUNT(*) as total_methods,
                   SUM(CASE WHEN is_default = 1 THEN 1 ELSE 0 END) as default_methods,
                   GROUP_CONCAT(DISTINCT method_type) as method_types
            FROM customer_payment_methods 
            WHERE customer_id = %s AND is_active = 1
        """, [customer_id])
        payment_summary = cursor.fetchone()
        
        # Solde et tendance récente
        cursor.execute("""
            SELECT current_balance, credit_limit,
                   (SELECT balance FROM customer_balance_history 
                    WHERE customer_id = %s 
                    ORDER BY created_at DESC LIMIT 1 OFFSET 7) as balance_week_ago
            FROM customer_finances 
            WHERE customer_id = %s
        """, [customer_id, customer_id])
        balance_info = cursor.fetchone()
        
        # ===== DOCUMENTS INTÉGRÉS =====
        # Résumé des documents
        cursor.execute("""
            SELECT 
                COUNT(*) as total_documents,
                SUM(CASE WHEN is_signed = 1 THEN 1 ELSE 0 END) as signed_documents,
                SUM(CASE WHEN is_confidential = 1 THEN 1 ELSE 0 END) as confidential_documents,
                COUNT(DISTINCT document_type) as document_types,
                MAX(created_at) as last_document_date
            FROM customer_documents 
            WHERE customer_id = %s
        """, [customer_id])
        documents_summary = cursor.fetchone()
        
        # Documents récents
        cursor.execute("""
            SELECT id, title, document_type, created_at, is_signed, file_size
            FROM customer_documents 
            WHERE customer_id = %s
            ORDER BY created_at DESC
            LIMIT 5
        """, [customer_id])
        recent_documents = cursor.fetchall()
        
        # ===== KPIs PERSONNALISABLES =====
        # Calcul automatique des KPIs
        kpis = {}
        
        # KPI Financier
        if balance_info:
            current_balance = float(balance_info.get('current_balance', 0))
            credit_limit = float(balance_info.get('credit_limit', 0))
            balance_week_ago = float(balance_info.get('balance_week_ago', 0))
            
            kpis['financial'] = {
                'current_balance': current_balance,
                'credit_utilization': (abs(current_balance) / credit_limit * 100) if credit_limit > 0 else 0,
                'balance_trend': 'improving' if current_balance > balance_week_ago else 'declining' if current_balance < balance_week_ago else 'stable',
                'credit_available': max(0, credit_limit - abs(current_balance)) if credit_limit > 0 else 0
            }
        
        # KPI Engagement
        cursor.execute("""
            SELECT 
                COUNT(*) as total_interactions,
                COUNT(DISTINCT DATE(created_at)) as active_days,
                MAX(created_at) as last_interaction
            FROM customer_activity 
            WHERE customer_id = %s 
            AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """, [customer_id])
        engagement_data = cursor.fetchone()
        
        kpis['engagement'] = {
            'monthly_interactions': engagement_data.get('total_interactions', 0),
            'active_days': engagement_data.get('active_days', 0),
            'last_interaction': engagement_data.get('last_interaction'),
            'engagement_score': min(100, (engagement_data.get('active_days', 0) * 3.33))  # 30 jours max = 100%
        }
        
        # KPI Documents/Compliance
        if documents_summary:
            total_docs = documents_summary.get('total_documents', 0)
            signed_docs = documents_summary.get('signed_documents', 0)
            
            kpis['compliance'] = {
                'total_documents': total_docs,
                'signature_rate': (signed_docs / total_docs * 100) if total_docs > 0 else 0,
                'document_types': documents_summary.get('document_types', 0),
                'last_document_days_ago': None
            }
            
            if documents_summary.get('last_document_date'):
                from datetime import datetime
                last_doc = documents_summary['last_document_date']
                if isinstance(last_doc, str):
                    last_doc = datetime.fromisoformat(last_doc.replace('Z', '+00:00'))
                days_ago = (datetime.now() - last_doc).days
                kpis['compliance']['last_document_days_ago'] = days_ago
        
        # ===== DONNÉES EXISTANTES =====
        # Get enhanced contacts
        cursor.execute("""
            SELECT * FROM customer_contacts
            WHERE customer_id = %s
            ORDER BY is_primary DESC, role, name
        """, [customer_id])
        contacts = cursor.fetchall()
        
        # Get enhanced addresses
        cursor.execute("""
            SELECT * FROM customer_addresses
            WHERE customer_id = %s
            ORDER BY is_primary DESC, type, label
        """, [customer_id])
        addresses = cursor.fetchall()
        
        # Get recent timeline (optimisé avec lazy loading)
        cursor.execute("""
            SELECT ca.*, u.name as actor_name
            FROM customer_activity ca
            LEFT JOIN users u ON ca.actor_id = u.id
            WHERE ca.customer_id = %s
            ORDER BY ca.created_at DESC
            LIMIT 10
        """, [customer_id])
        recent_activities = cursor.fetchall()
        
        # Get vehicles
        cursor.execute("""
            SELECT * FROM vehicles
            WHERE customer_id = %s
            ORDER BY created_at DESC
            LIMIT 5
        """, [customer_id])
        vehicles = cursor.fetchall()
        
        # ===== OPTIMISATION LAZY LOADING =====
        # Préparer les URLs pour le chargement AJAX des sections lourdes
        ajax_endpoints = {
            'full_timeline': url_for('customers.customer_timeline', customer_id=customer_id),
            'all_documents': url_for('customers.get_customer_documents', customer_id=customer_id),
            'financial_details': url_for('customers.get_customer_finances', customer_id=customer_id),
            'payment_methods': url_for('customers.get_payment_methods', customer_id=customer_id),
            'balance_history': url_for('customers.get_customer_balance_summary', customer_id=customer_id),
            'risk_score': url_for('customers.calculate_customer_risk_score', customer_id=customer_id)
        }
        
        cursor.close()
        conn.close()
        
        return render_template(
            'customers/view_360.html',
            customer=customer,
            contacts=contacts,
            addresses=addresses,
            vehicles=vehicles,
            recent_activities=recent_activities,
            # Nouvelles données financières
            financial_profile=financial_profile,
            payment_summary=payment_summary,
            balance_info=balance_info,
            # Nouvelles données documents
            documents_summary=documents_summary,
            recent_documents=recent_documents,
            # KPIs calculés
            kpis=kpis,
            # URLs pour lazy loading
            ajax_endpoints=ajax_endpoints
        )
        
    except Exception as e:
        log_error(f"Erreur Client 360: {e}")
        flash('Erreur lors du chargement du Client 360', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))


# =====================================================
# FINANCES - ENDPOINTS API
# =====================================================

@bp.route('/<int:customer_id>/finances', methods=['GET'])
@require_role('admin', 'manager', 'staff')
def get_customer_finances(customer_id):
    """Récupère les informations financières d'un client"""
    user = get_current_user()
    log_activity(user.id, 'view_finances', entity_type='customer', entity_id=customer_id, ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent'))
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get customer info first
        cursor.execute("SELECT id, name, type FROM customers WHERE id = %s", [customer_id])
        customer = cursor.fetchone()
        if not customer:
            flash('Client non trouvé', 'error')
            return redirect(url_for('customers.index'))
        
        # Get or create finance profile
        cursor.execute("SELECT * FROM customer_finances WHERE customer_id = %s", [customer_id])
        finance_profile = cursor.fetchone()
        
        if not finance_profile:
            # Create default profile
            default_credit = 2500.00 if customer['type'] == 'individual' else (10000.00 if customer['type'] == 'enterprise' else 25000.00)
            default_terms = 'net15' if customer['type'] == 'individual' else ('net30' if customer['type'] == 'enterprise' else 'net45')
            default_tier = 'standard' if customer['type'] == 'individual' else ('wholesale' if customer['type'] == 'enterprise' else 'government')
            
            cursor.execute("""
                INSERT INTO customer_finances 
                (customer_id, credit_limit, available_credit, payment_terms, price_tier, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, [customer_id, default_credit, default_credit, default_terms, default_tier])
            conn.commit()
            
            cursor.execute("SELECT * FROM customer_finances WHERE customer_id = %s", [customer_id])
            finance_profile = cursor.fetchone()
        
        # Get payment methods
        cursor.execute("""
            SELECT id, provider, method_type, masked_number, expiry_date, 
                   holder_name, brand, last_four, is_default, is_active, created_at
            FROM customer_payment_methods
            WHERE customer_id = %s AND is_active = TRUE
            ORDER BY is_default DESC, created_at DESC
        """, [customer_id])
        payment_methods = cursor.fetchall()
        
        # Get recent balance history
        cursor.execute("""
            SELECT * FROM customer_balance_history
            WHERE customer_id = %s
            ORDER BY created_at DESC
            LIMIT 20
        """, [customer_id])
        balance_history = cursor.fetchall()
        
        # Get AR summary from invoices table if it exists
        ar_summary = {'invoice_count': 0, 'total_outstanding': 0, 'past_due_amount': 0, 'earliest_due_date': None}
        try:
            cursor.execute("""
                SELECT
                    COUNT(*) as invoice_count,
                    IFNULL(SUM(total_amount), 0) as total_outstanding,
                    MIN(due_date) as earliest_due_date,
                    IFNULL(SUM(CASE WHEN due_date < NOW() THEN total_amount ELSE 0 END), 0) as past_due_amount
                FROM invoices
                WHERE customer_id = %s AND status IN ('open', 'sent')
            """, [customer_id])
            ar_result = cursor.fetchone()
            if ar_result:
                ar_summary.update(ar_result)
        except Exception as e:
            log_warning(f"Table invoices non trouvée ou erreur AR: {e}")
        
        # Get payment summary
        cursor.execute("""
            SELECT * FROM customer_payment_summary WHERE customer_id = %s
        """, [customer_id])
        payment_summary = cursor.fetchone()
        
        if not payment_summary:
            # Create default payment summary
            cursor.execute("""
                INSERT INTO customer_payment_summary (customer_id, payment_score)
                VALUES (%s, 100)
            """, [customer_id])
            conn.commit()
            
            cursor.execute("SELECT * FROM customer_payment_summary WHERE customer_id = %s", [customer_id])
            payment_summary = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        # Return JSON if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({
                'success': True,
                'customer': customer,
                'finance_profile': finance_profile,
                'payment_methods': payment_methods,
                'balance_history': balance_history,
                'ar_summary': ar_summary,
                'payment_summary': payment_summary
            })
        
        return render_template(
            'customers/finances.html',
            customer=customer,
            finance_profile=finance_profile,
            payment_methods=payment_methods,
            balance_history=balance_history,
            ar_summary=ar_summary,
            payment_summary=payment_summary
        )
    except Exception as e:
        log_error(f"Erreur récupération finances client {customer_id}: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur récupération finances'}), 500
        flash('Erreur chargement informations financières', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))


@bp.route('/<int:customer_id>/finances', methods=['POST'])
@require_role('admin', 'manager', 'staff')
def update_customer_finances(customer_id):
    """Met à jour les informations financières d'un client"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        credit_limit = float(data.get('credit_limit', 0))
        payment_terms = data.get('payment_terms', 'net30')
        price_tier = data.get('price_tier', 'standard')
        discount_percent = float(data.get('discount_percent', 0))
        tax_exempt = data.get('tax_exempt') in ['true', 'True', '1', 1, True]
        tax_exempt_reason = data.get('tax_exempt_reason', '')
        tax_exempt_number = data.get('tax_exempt_number', '')
        hold_status = data.get('hold_status', 'none')
        hold_reason = data.get('hold_reason', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate available credit (credit_limit - outstanding invoices)
        try:
            cursor.execute("""
                SELECT IFNULL(SUM(total_amount), 0) as outstanding
                FROM invoices
                WHERE customer_id = %s AND status IN ('open', 'sent')
            """, [customer_id])
            outstanding_result = cursor.fetchone()
            outstanding = outstanding_result[0] if outstanding_result else 0
        except:
            outstanding = 0
        
        available_credit = max(0, credit_limit - outstanding)
        
        # Update or insert finance profile
        cursor.execute("""
            INSERT INTO customer_finances
            (customer_id, credit_limit, available_credit, payment_terms, price_tier, 
             discount_percent, tax_exempt, tax_exempt_reason, tax_exempt_number, 
             hold_status, hold_reason, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
            credit_limit = VALUES(credit_limit),
            available_credit = VALUES(available_credit),
            payment_terms = VALUES(payment_terms),
            price_tier = VALUES(price_tier),
            discount_percent = VALUES(discount_percent),
            tax_exempt = VALUES(tax_exempt),
            tax_exempt_reason = VALUES(tax_exempt_reason),
            tax_exempt_number = VALUES(tax_exempt_number),
            hold_status = VALUES(hold_status),
            hold_reason = VALUES(hold_reason),
            updated_at = NOW()
        """, [
            customer_id, credit_limit, available_credit, payment_terms, price_tier,
            discount_percent, tax_exempt, tax_exempt_reason, tax_exempt_number,
            hold_status, hold_reason
        ])
        
        # Log activity
        log_customer_activity(
            customer_id, 'system', None, 'customer_finances',
            'Profil financier mis à jour',
            f'Limite: {credit_limit}, Termes: {payment_terms}, Tier: {price_tier}',
            None
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Informations financières mises à jour',
            'available_credit': available_credit
        })
    except Exception as e:
        log_error(f"Erreur mise à jour finances client {customer_id}: {e}")
        return jsonify({'success': False, 'message': 'Erreur mise à jour finances'}), 500


@bp.route('/<int:customer_id>/payment-methods', methods=['GET'])
@require_role('admin', 'manager', 'staff')
def get_payment_methods(customer_id):
    """Récupère les méthodes de paiement d'un client"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute("""
            SELECT id, provider, method_type, masked_number, expiry_date,
                   holder_name, brand, last_four, is_default, is_active, created_at
            FROM customer_payment_methods
            WHERE customer_id = %s
            ORDER BY is_default DESC, created_at DESC
        """, [customer_id])
        payment_methods = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'payment_methods': payment_methods
        })
    except Exception as e:
        log_error(f"Erreur récupération méthodes paiement: {e}")
        return jsonify({'success': False, 'message': 'Erreur récupération méthodes paiement'}), 500


@bp.route('/<int:customer_id>/payment-methods', methods=['POST'])
@require_role('admin', 'manager', 'staff')
def add_payment_method(customer_id):
    """Ajoute une méthode de paiement pour un client"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        provider = data.get('provider', 'other')
        token = data.get('token', '')
        method_type = data.get('method_type', 'credit_card')
        masked_number = data.get('masked_number', '')
        expiry_date = data.get('expiry_date', '')
        holder_name = data.get('holder_name', '')
        brand = data.get('brand', '')
        last_four = data.get('last_four', '')
        is_default = data.get('is_default') in ['true', 'True', '1', 1, True]
        
        if not token:
            return jsonify({'success': False, 'message': 'Token requis'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # If setting as default, clear other defaults
        if is_default:
            cursor.execute("""
                UPDATE customer_payment_methods
                SET is_default = FALSE
                WHERE customer_id = %s
            """, [customer_id])
        
        # Add new payment method
        cursor.execute("""
            INSERT INTO customer_payment_methods
            (customer_id, provider, token, method_type, masked_number,
             expiry_date, holder_name, brand, last_four, is_default, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, [
            customer_id, provider, token, method_type, masked_number,
            expiry_date, holder_name, brand, last_four, is_default
        ])
        
        method_id = cursor.lastrowid
        
        # Log activity
        log_customer_activity(
            customer_id, 'system', method_id, 'customer_payment_methods',
            'Méthode de paiement ajoutée',
            f'Type: {method_type}, Fournisseur: {provider}',
            None
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Méthode de paiement ajoutée',
            'method_id': method_id
        })
    except Exception as e:
        log_error(f"Erreur ajout méthode paiement: {e}")
        return jsonify({'success': False, 'message': 'Erreur ajout méthode paiement'}), 500


# --- Mise à jour d'une méthode de paiement ---
@bp.route('/payment-methods/<int:method_id>', methods=['PATCH'])
@require_role('admin', 'manager', 'staff', 'client')
def update_payment_method(method_id):
    """Met à jour une méthode de paiement"""
    try:
        user = get_current_user()
        data = request.get_json() or {}
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Vérification que la méthode existe
        cursor.execute("""
            SELECT customer_id, method_type, provider
            FROM customer_payment_methods
            WHERE id = %s AND is_active = TRUE
        """, [method_id])
        method = cursor.fetchone()
        
        if not method:
            return jsonify({'success': False, 'message': 'Méthode de paiement non trouvée'}), 404
        
        # Champs modifiables
        fields = []
        params = []
        
        if 'label' in data:
            fields.append('label = %s')
            params.append(data['label'])
        
        if 'expiry_date' in data:
            fields.append('expiry_date = %s')
            params.append(data['expiry_date'])
        
        if 'is_default' in data:
            fields.append('is_default = %s')
            params.append(bool(data['is_default']))
            
            # Si on définit cette méthode comme par défaut, retirer le flag des autres
            if data['is_default']:
                cursor.execute("""
                    UPDATE customer_payment_methods
                    SET is_default = FALSE
                    WHERE customer_id = %s AND id != %s
                """, [method['customer_id'], method_id])
        
        if 'billing_address' in data:
            fields.append('billing_address = %s')
            params.append(json.dumps(data['billing_address']) if data['billing_address'] else None)
        
        if not fields:
            return jsonify({'success': False, 'message': 'Aucune donnée à mettre à jour'}), 400
        
        # Exécution de la mise à jour
        params.extend([method_id])
        query = f"""
            UPDATE customer_payment_methods
            SET {', '.join(fields)}, updated_at = NOW()
            WHERE id = %s
        """
        cursor.execute(query, params)
        
        # Log de l'activité
        log_activity(
            user.id, 'update_payment_method',
            entity_type='payment_method', entity_id=method_id,
            details=str(data),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Méthode de paiement mise à jour'})
        
    except Exception as e:
        log_error(f"Erreur update_payment_method: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de la mise à jour'}), 500

@bp.route('/payment-methods/<int:method_id>', methods=['DELETE'])
@require_role('admin', 'manager', 'staff')
def delete_payment_method(method_id):
    """Supprime une méthode de paiement"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get method info before deletion
        cursor.execute("""
            SELECT customer_id, method_type, provider
            FROM customer_payment_methods
            WHERE id = %s
        """, [method_id])
        method = cursor.fetchone()
        
        if not method:
            return jsonify({'success': False, 'message': 'Méthode de paiement non trouvée'}), 404
        
        # Soft delete - set is_active to FALSE
        cursor.execute("""
            UPDATE customer_payment_methods
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = %s
        """, [method_id])
        
        
        # Log activity
        log_activity(
            user.id if (user := get_current_user()) else 1, 'delete_payment_method',
            entity_type='payment_method', entity_id=method_id,
            details=f'Type: {method["method_type"]}, Fournisseur: {method["provider"]}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Méthode de paiement supprimée'
        })
    except Exception as e:
        log_error(f"Erreur suppression méthode paiement: {e}")
        return jsonify({'success': False, 'message': 'Erreur suppression méthode paiement'}), 500


# --- Gestion du renouvellement automatique des moyens de paiement expirés ---
@bp.route('/payment-methods/check-expired', methods=['POST'])
@require_role('admin', 'manager', 'staff')
def check_expired_payment_methods():
    """Vérifie et signale les moyens de paiement expirés"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Chercher les moyens de paiement qui expirent dans les 30 prochains jours
        cursor.execute("""
            SELECT pm.*, c.name as customer_name, c.email as customer_email
            FROM customer_payment_methods pm
            JOIN customers c ON pm.customer_id = c.id
            WHERE pm.is_active = TRUE 
            AND pm.expiry_date IS NOT NULL
            AND pm.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
            AND pm.expiry_date >= CURDATE()
            ORDER BY pm.expiry_date ASC
        """)
        expiring_methods = cursor.fetchall()
        
        # Chercher les moyens de paiement déjà expirés
        cursor.execute("""
            SELECT pm.*, c.name as customer_name, c.email as customer_email
            FROM customer_payment_methods pm
            JOIN customers c ON pm.customer_id = c.id
            WHERE pm.is_active = TRUE 
            AND pm.expiry_date IS NOT NULL
            AND pm.expiry_date < CURDATE()
            ORDER BY pm.expiry_date DESC
        """)
        expired_methods = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'expiring_soon': expiring_methods,
            'expired': expired_methods,
            'total_expiring': len(expiring_methods),
            'total_expired': len(expired_methods)
        })
        
    except Exception as e:
        log_error(f"Erreur vérification moyens paiement expirés: {e}")
        return jsonify({'success': False, 'message': 'Erreur vérification expiration'}), 500


# --- Historique des soldes intégré au dashboard ---
@bp.route('/<int:customer_id>/balance-summary', methods=['GET'])
@require_role('admin', 'manager', 'staff')
def get_customer_balance_summary(customer_id):
    """Résumé du solde client pour le dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Solde actuel et tendance
        cursor.execute("""
            SELECT 
                current_balance,
                (SELECT balance FROM customer_balance_history 
                 WHERE customer_id = %s 
                 ORDER BY created_at DESC LIMIT 1 OFFSET 1) as previous_balance
            FROM customer_finances 
            WHERE customer_id = %s
        """, [customer_id, customer_id])
        balance_info = cursor.fetchone() or {}
        
        # Historique récent (30 derniers jours)
        cursor.execute("""
            SELECT DATE(created_at) as date, 
                   AVG(balance) as avg_balance,
                   COUNT(*) as transactions
            FROM customer_balance_history
            WHERE customer_id = %s 
            AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
        """, [customer_id])
        balance_history = cursor.fetchall()
        
        # Calcul de la tendance
        current = float(balance_info.get('current_balance', 0))
        previous = float(balance_info.get('previous_balance', 0))
        trend = 'stable'
        if current > previous:
            trend = 'improving'
        elif current < previous:
            trend = 'declining'
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'current_balance': current,
            'trend': trend,
            'history': balance_history,
            'trend_percentage': round(((current - previous) / max(abs(previous), 1)) * 100, 2) if previous != 0 else 0
        })
        
    except Exception as e:
        log_error(f"Erreur résumé solde client: {e}")
        return jsonify({'error': 'Erreur récupération solde'}), 500


# --- Calcul du score de risque client ---
@bp.route('/<int:customer_id>/risk-score', methods=['GET'])
@require_role('admin', 'manager', 'staff')
def calculate_customer_risk_score(customer_id):
    """Calcule le score de risque du client basé sur l'historique"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Récupérer les données financières
        cursor.execute("""
            SELECT credit_limit, current_balance, payment_terms
            FROM customer_finances
            WHERE customer_id = %s
        """, [customer_id])
        finances = cursor.fetchone() or {}
        
        # Historique des paiements (90 derniers jours)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                AVG(CASE WHEN transaction_type = 'payment' THEN amount ELSE 0 END) as avg_payment,
                COUNT(CASE WHEN transaction_type = 'payment' AND amount > 0 THEN 1 END) as payment_count,
                COUNT(CASE WHEN transaction_type = 'adjustment' AND amount < 0 THEN 1 END) as penalty_count
            FROM customer_balance_history
            WHERE customer_id = %s 
            AND created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
        """, [customer_id])
        payment_stats = cursor.fetchone() or {}
        
        # Calcul du score (0-100, 100 = excellent)
        score = 100
        
        # Facteur 1: Utilisation du crédit
        credit_limit = float(finances.get('credit_limit', 0))
        current_balance = float(finances.get('current_balance', 0))
        if credit_limit > 0:
            credit_usage = abs(current_balance) / credit_limit
            if credit_usage > 0.8:
                score -= 20
            elif credit_usage > 0.6:
                score -= 10
            elif credit_usage > 0.4:
                score -= 5
        
        # Facteur 2: Régularité des paiements
        payment_count = payment_stats.get('payment_count', 0)
        total_transactions = payment_stats.get('total_transactions', 0)
        if total_transactions > 0:
            payment_ratio = payment_count / total_transactions
            if payment_ratio < 0.5:
                score -= 15
            elif payment_ratio < 0.7:
                score -= 8
        
        # Facteur 3: Pénalités
        penalty_count = payment_stats.get('penalty_count', 0)
        if penalty_count > 5:
            score -= 20
        elif penalty_count > 2:
            score -= 10
        
        # Déterminer la catégorie de risque
        if score >= 80:
            risk_category = 'low'
            risk_label = 'Risque faible'
        elif score >= 60:
            risk_category = 'medium'
            risk_label = 'Risque modéré'
        elif score >= 40:
            risk_category = 'high'
            risk_label = 'Risque élevé'
        else:
            risk_category = 'critical'
            risk_label = 'Risque critique'
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'score': max(0, min(100, score)),
            'category': risk_category,
            'label': risk_label,
            'factors': {
                'credit_usage': credit_usage if credit_limit > 0 else 0,
                'payment_ratio': payment_ratio if total_transactions > 0 else 1,
                'penalty_count': penalty_count
            }
        })
        
    except Exception as e:
        log_error(f"Erreur calcul score risque: {e}")
        return jsonify({'error': 'Erreur calcul score'}), 500


# --- Workflows automatisés (rappels, dunning) - Structure ---
@bp.route('/<int:customer_id>/payment-workflows', methods=['GET'])
@require_role('admin', 'manager', 'staff')
def get_payment_workflows(customer_id):
    """Récupère les workflows de paiement actifs pour un client"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Vérifier s'il y a des factures en retard
        cursor.execute("""
            SELECT 
                COUNT(*) as overdue_count,
                SUM(CASE WHEN DATEDIFF(NOW(), due_date) > 30 THEN amount ELSE 0 END) as overdue_30_amount,
                SUM(CASE WHEN DATEDIFF(NOW(), due_date) > 60 THEN amount ELSE 0 END) as overdue_60_amount,
                SUM(CASE WHEN DATEDIFF(NOW(), due_date) > 90 THEN amount ELSE 0 END) as overdue_90_amount
            FROM customer_balance_history
            WHERE customer_id = %s 
            AND transaction_type = 'invoice'
            AND due_date < NOW()
            AND amount > 0
        """, [customer_id])
        overdue_info = cursor.fetchone() or {}
        
        # Recommandations de workflow
        workflows = []
        overdue_count = overdue_info.get('overdue_count', 0)
        overdue_30 = float(overdue_info.get('overdue_30_amount', 0))
        overdue_60 = float(overdue_info.get('overdue_60_amount', 0))
        overdue_90 = float(overdue_info.get('overdue_90_amount', 0))
        
        if overdue_count > 0:
            if overdue_90 > 0:
                workflows.append({
                    'type': 'legal_notice',
                    'priority': 'high',
                    'message': f'Mise en demeure recommandée (facturation en retard +90j: {overdue_90:.2f}€)'
                })
            elif overdue_60 > 0:
                workflows.append({
                    'type': 'final_notice',
                    'priority': 'medium',
                    'message': f'Dernier rappel recommandé (facturation en retard +60j: {overdue_60:.2f}€)'
                })
            elif overdue_30 > 0:
                workflows.append({
                    'type': 'reminder',
                    'priority': 'low',
                    'message': f'Rappel de paiement recommandé (facturation en retard +30j: {overdue_30:.2f}€)'
                })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'workflows': workflows,
            'overdue_summary': overdue_info
        })
        
    except Exception as e:
        log_error(f"Erreur workflows paiement: {e}")
        return jsonify({'error': 'Erreur récupération workflows'}), 500


# =====================================================
# DOCUMENTS & SIGNATURE
# =====================================================

# Configuration centralisée pour la gestion des documents
import os
from PIL import Image
import hashlib

# Configuration des documents
DOCUMENT_CONFIG = {
    'upload_path': os.environ.get('UPLOAD_FOLDER', '/home/amenard/Chronotech/ChronoTech/uploads/customers'),
    'max_file_size': int(os.environ.get('MAX_UPLOAD_SIZE', 52428800)),  # 50MB par défaut
    'allowed_extensions': {'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'bmp'},
    'image_max_size': (1920, 1080),  # Redimensionnement max pour images
    'thumbnail_size': (300, 200),   # Taille des vignettes
    'compression_quality': 85,      # Qualité JPEG compression
}

# Configuration des consentements et compliance
CONSENT_CONFIG = {
    'required_consents': {
        'data_processing': {
            'name': 'Traitement des données personnelles',
            'description': 'Consentement au traitement des données personnelles selon RGPD',
            'mandatory': True,
            'category': 'legal'
        },
        'marketing': {
            'name': 'Communications marketing',
            'description': 'Acceptation de recevoir des communications commerciales',
            'mandatory': False,
            'category': 'marketing'
        },
        'technical_data': {
            'name': 'Données techniques',
            'description': 'Collecte des données techniques des équipements',
            'mandatory': False,
            'category': 'technical'
        },
        'geolocation': {
            'name': 'Géolocalisation',
            'description': 'Utilisation des données de géolocalisation',
            'mandatory': False,
            'category': 'location'
        }
    },
    'retention_periods': {
        'active_customer': 365 * 7,      # 7 ans
        'inactive_customer': 365 * 3,    # 3 ans
        'technical_data': 365 * 5,       # 5 ans
        'communication': 365 * 2         # 2 ans
    },
    'audit_requirements': {
        'log_consent_changes': True,
        'log_data_access': True,
        'anonymize_after_retention': True,
        'consent_renewal_period': 365 * 2  # Renouvellement tous les 2 ans
    }
}

def get_document_path(customer_id, filename):
    """Génère le chemin de stockage d'un document"""
    customer_dir = os.path.join(DOCUMENT_CONFIG['upload_path'], str(customer_id))
    os.makedirs(customer_dir, exist_ok=True)
    return os.path.join(customer_dir, filename)

def generate_thumbnail(image_path, customer_id, filename):
    """Génère une vignette pour les images"""
    try:
        with Image.open(image_path) as img:
            # Conversion en RGB si nécessaire
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Création de la vignette
            img.thumbnail(DOCUMENT_CONFIG['thumbnail_size'], Image.Resampling.LANCZOS)
            
            # Sauvegarde de la vignette
            thumbnail_filename = f"thumb_{filename}"
            thumbnail_path = get_document_path(customer_id, thumbnail_filename)
            img.save(thumbnail_path, 'JPEG', quality=80)
            
            return thumbnail_filename
    except Exception as e:
        log_error(f"Erreur génération vignette: {e}")
        return None

def compress_image(image_path, customer_id, filename):
    """Compresse et redimensionne les images"""
    try:
        with Image.open(image_path) as img:
            # Conversion en RGB si nécessaire
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Redimensionnement si nécessaire
            if img.size[0] > DOCUMENT_CONFIG['image_max_size'][0] or img.size[1] > DOCUMENT_CONFIG['image_max_size'][1]:
                img.thumbnail(DOCUMENT_CONFIG['image_max_size'], Image.Resampling.LANCZOS)
            
            # Sauvegarde compressée
            compressed_filename = f"compressed_{filename}"
            compressed_path = get_document_path(customer_id, compressed_filename)
            img.save(compressed_path, 'JPEG', quality=DOCUMENT_CONFIG['compression_quality'], optimize=True)
            
            return compressed_filename
    except Exception as e:
        log_error(f"Erreur compression image: {e}")
        return None

def calculate_file_hash(file_path):
    """Calcule le hash SHA-256 d'un fichier pour vérification d'intégrité"""
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        log_error(f"Erreur calcul hash fichier: {e}")
        return None


# =====================================================
# DOCUMENTS & SIGNATURE AMÉLIORÉS
# =====================================================

@bp.route('/<int:customer_id>/documents', methods=['GET'])
@require_role('admin', 'manager', 'staff', 'client')
def get_customer_documents(customer_id):
    user = get_current_user()
    log_activity(user.id, 'view_documents', entity_type='customer', entity_id=customer_id, ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent'))
    # ...existing code...
@require_role('admin', 'manager', 'staff', 'client')
def get_customer_documents(customer_id):
    """Récupère les documents d'un client"""
    try:
        document_type = request.args.get('type')
        category = request.args.get('category')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get customer info
        cursor.execute("SELECT id, name FROM customers WHERE id = %s", [customer_id])
        customer = cursor.fetchone()
        if not customer:
            return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
        
        # Build query
        where_conditions = ["cd.customer_id = %s"]
        params = [customer_id]
        
        if document_type:
            where_conditions.append("cd.document_type = %s")
            params.append(document_type)
            
        if category:
            where_conditions.append("cd.category = %s")
            params.append(category)
        
        where_clause = " AND ".join(where_conditions)
        
        # Count total for pagination
        count_query = f"""
            SELECT COUNT(*) as count
            FROM customer_documents cd
            WHERE {where_clause}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()['count']
        
        # Get documents with pagination
        query = f"""
            SELECT cd.*, u.name as created_by_name
            FROM customer_documents cd
            LEFT JOIN users u ON cd.created_by = u.id
            WHERE {where_clause}
            ORDER BY cd.created_at DESC
            LIMIT %s OFFSET %s
        """
        offset = (page - 1) * per_page
        params.extend([per_page, offset])
        
        cursor.execute(query, params)
        documents = cursor.fetchall()
        
        # Get document type counts
        cursor.execute("""
            SELECT document_type, COUNT(*) as count
            FROM customer_documents
            WHERE customer_id = %s
            GROUP BY document_type
            ORDER BY count DESC
        """, [customer_id])
        type_counts = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        pagination = MiniPagination(total=total, page=page, per_page=per_page)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({
                'success': True,
                'customer': customer,
                'documents': documents,
                'type_counts': type_counts,
                'pagination': {
                    'total': pagination.total,
                    'page': pagination.page,
                    'per_page': pagination.per_page,
                    'pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            })
        
        return render_template(
            'customers/documents.html',
            customer=customer,
            documents=documents,
            type_counts=type_counts,
            pagination=pagination,
            selected_type=document_type,
            selected_category=category
        )
    except Exception as e:
        log_error(f"Erreur récupération documents client {customer_id}: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur récupération documents'}), 500
        flash('Erreur chargement documents', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))


@bp.route('/<int:customer_id>/documents', methods=['POST'])
@require_role('admin', 'manager', 'staff', 'client')
def upload_document(customer_id):
    """Téléverse un nouveau document pour un client avec compression et vignettes"""
    from werkzeug.utils import secure_filename
    
    try:
        user = get_current_user()
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Aucun fichier fourni'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Aucun fichier sélectionné'}), 400
            
        # Validation de l'extension
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        if file_ext not in DOCUMENT_CONFIG['allowed_extensions']:
            return jsonify({
                'success': False, 
                'message': f'Type de fichier non autorisé. Extensions autorisées: {", ".join(DOCUMENT_CONFIG["allowed_extensions"])}'
            }), 400
        
        # Validation de la taille
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > DOCUMENT_CONFIG['max_file_size']:
            max_mb = DOCUMENT_CONFIG['max_file_size'] / (1024 * 1024)
            return jsonify({'success': False, 'message': f'Fichier trop volumineux (max {max_mb:.0f}MB)'}), 400
        
        # Métadonnées du document
        document_type = request.form.get('document_type', 'other')
        category = request.form.get('category', '')
        title = request.form.get('title') or f'Document {filename}'
        is_confidential = request.form.get('is_confidential') in ['true', 'True', '1', 1, True]
        access_level = request.form.get('access_level', 'staff')
        
        # Génération du nom de fichier unique
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{filename}"
        file_path = get_document_path(customer_id, safe_filename)
        
        # Sauvegarde du fichier original
        file.save(file_path)
        
        # Calcul du hash pour vérification d'intégrité
        file_hash = calculate_file_hash(file_path)
        
        # Traitement des images (compression et vignettes)
        thumbnail_filename = None
        compressed_filename = None
        is_image = file_ext in {'jpg', 'jpeg', 'png', 'gif', 'bmp'}
        
        if is_image:
            # Génération de la vignette
            thumbnail_filename = generate_thumbnail(file_path, customer_id, safe_filename)
            
            # Compression si nécessaire
            if file_ext in {'jpg', 'jpeg', 'png'} and file_size > 1024 * 1024:  # > 1MB
                compressed_filename = compress_image(file_path, customer_id, safe_filename)
        
        # Sauvegarde en base de données
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute("""
            INSERT INTO customer_documents (
                customer_id, title, document_type, category, 
                filename, file_path, file_size, file_hash,
                thumbnail_filename, compressed_filename,
                is_confidential, access_level, created_by,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
            )
        """, [
            customer_id, title, document_type, category,
            safe_filename, file_path, file_size, file_hash,
            thumbnail_filename, compressed_filename,
            is_confidential, access_level, user.id
        ])
        
        document_id = cursor.lastrowid
        
        # Log de l'activité
        log_activity(
            user.id, 'upload_document',
            entity_type='document', entity_id=document_id,
            details=f'Document: {title}, Type: {document_type}, Taille: {file_size}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Document téléversé avec succès',
            'document': {
                'id': document_id,
                'title': title,
                'filename': safe_filename,
                'file_size': file_size,
                'has_thumbnail': thumbnail_filename is not None,
                'is_compressed': compressed_filename is not None
            }
        })
        
    except Exception as e:
        log_error(f"Erreur upload document: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors du téléversement'}), 500
        sha256_hash = hashlib.sha256()
        md5_hash = hashlib.md5()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
                md5_hash.update(byte_block)
        
        file_hash_sha256 = sha256_hash.hexdigest()
        file_hash_md5 = md5_hash.hexdigest()
        
        # Get current user if available
        user_id = None
        try:
            # Try to get from session or other method since flask_login might not be installed
            user_id = session.get('user_id')
        except:
            pass
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Store document metadata
        cursor.execute("""
            INSERT INTO customer_documents
            (customer_id, document_type, category, title, filename, file_path, file_size,
             mime_type, hash_sha256, hash_md5, is_confidential, access_level, created_by, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, [
            customer_id, document_type, category, title, filename, 
            os.path.relpath(file_path, upload_base), file_size, file.content_type, 
            file_hash_sha256, file_hash_md5, is_confidential, access_level, user_id
        ])
        
        document_id = cursor.lastrowid
        
        # Log activity (will be triggered by database trigger as well)
        log_customer_activity(
            customer_id, 'document', document_id, 'customer_documents',
            f'Document téléversé: {title}',
            f'Type: {document_type}, Taille: {file_size} octets',
            user_id
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Document téléversé avec succès',
            'document': {
                'id': document_id,
                'title': title,
                'filename': filename,
                'size': file_size,
                'type': document_type,
                'category': category,
                'hash': file_hash_sha256[:8]  # Show first 8 chars for verification
            }
        })
    except Exception as e:
        log_error(f"Erreur upload document client {customer_id}: {e}")
        return jsonify({'success': False, 'message': f'Erreur upload: {str(e)}'}), 500


@bp.route('/documents/<int:document_id>')
@require_role('admin', 'manager', 'staff', 'client')
def view_document(document_id):
    """Affiche ou télécharge un document avec prévisualisation améliorée"""
    try:
        user = get_current_user()
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Récupérer le document avec toutes les informations nécessaires
        cursor.execute("""
            SELECT cd.*, c.name as customer_name
            FROM customer_documents cd
            JOIN customers c ON cd.customer_id = c.id
            WHERE cd.id = %s
        """, [document_id])
        document = cursor.fetchone()
        
        if not document:
            return jsonify({'success': False, 'message': 'Document non trouvé'}), 404
        
        # Vérification des permissions d'accès
        access_level = document.get('access_level', 'staff')
        user_role = user.role if user else 'guest'
        
        # Logique de contrôle d'accès
        can_access = False
        if user_role in ['admin', 'manager']:
            can_access = True
        elif user_role == 'staff' and access_level in ['public', 'client', 'staff']:
            can_access = True
        elif user_role == 'client' and access_level in ['public', 'client']:
            can_access = True
        elif access_level == 'public':
            can_access = True
        
        if not can_access:
            return jsonify({'success': False, 'message': 'Accès refusé à ce document'}), 403
        
        # Log de l'accès
        access_type = 'preview' if request.args.get('preview') == '1' else 'download'
        cursor.execute("""
            INSERT INTO customer_document_access_log
            (document_id, customer_id, accessed_by, access_type, ip_address, user_agent, accessed_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, [
            document_id, document['customer_id'], user.id,
            access_type, request.remote_addr, request.headers.get('User-Agent')
        ])
        
        # Log activité utilisateur
        log_activity(
            user.id, f'{access_type}_document',
            entity_type='document', entity_id=document_id,
            details=f'Document: {document["title"]}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        conn.commit()
        
        # Prévisualisation demandée
        if request.args.get('preview') == '1':
            # Déterminer le type de prévisualisation
            filename = document.get('filename', '')
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            
            preview_data = {
                'document': document,
                'preview_type': 'unknown',
                'can_preview': False,
                'thumbnail_available': bool(document.get('thumbnail_filename')),
                'compressed_available': bool(document.get('compressed_filename'))
            }
            
            # Types supportés pour prévisualisation
            if file_ext in {'jpg', 'jpeg', 'png', 'gif', 'bmp'}:
                preview_data['preview_type'] = 'image'
                preview_data['can_preview'] = True
            elif file_ext in {'pdf'}:
                preview_data['preview_type'] = 'pdf'
                preview_data['can_preview'] = True
            elif file_ext in {'txt', 'csv', 'log'}:
                preview_data['preview_type'] = 'text'
                preview_data['can_preview'] = True
                # Lire le contenu pour les petits fichiers texte
                if document.get('file_size', 0) < 1024 * 1024:  # < 1MB
                    try:
                        with open(document['file_path'], 'r', encoding='utf-8') as f:
                            preview_data['text_content'] = f.read(10000)  # Premières 10k caractères
                    except Exception:
                        try:
                            with open(document['file_path'], 'r', encoding='latin-1') as f:
                                preview_data['text_content'] = f.read(10000)
                        except Exception:
                            preview_data['text_content'] = "Impossible de lire le contenu du fichier"
            elif file_ext in {'doc', 'docx'}:
                preview_data['preview_type'] = 'document'
                preview_data['can_preview'] = False  # Nécessiterait une conversion
                preview_data['preview_note'] = "Prévisualisation non disponible pour ce type de document"
            elif file_ext in {'mp4', 'avi', 'mov', 'webm'}:
                preview_data['preview_type'] = 'video'
                preview_data['can_preview'] = True
            elif file_ext in {'mp3', 'wav', 'ogg'}:
                preview_data['preview_type'] = 'audio'
                preview_data['can_preview'] = True
            
            cursor.close()
            conn.close()
            
            return render_template('customers/document_preview.html', **preview_data)
        
        # Téléchargement du fichier
        cursor.close()
        conn.close()
        
        try:
            file_path = document['file_path']
            filename = document.get('filename', '')
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            
            # Utiliser la version compressée pour les images si disponible et demandée
            if (request.args.get('compressed') == '1' and 
                document.get('compressed_filename') and 
                file_ext in {'jpg', 'jpeg', 'png'}):
                file_path = get_document_path(document['customer_id'], document['compressed_filename'])
            
            # Utiliser la vignette si demandée
            if (request.args.get('thumbnail') == '1' and 
                document.get('thumbnail_filename')):
                file_path = get_document_path(document['customer_id'], document['thumbnail_filename'])
            
            from flask import send_file
            return send_file(
                file_path,
                as_attachment=request.args.get('download') == '1',
                download_name=document['filename']
            )
            
        except Exception as e:
            log_error(f"Erreur envoi fichier: {e}")
            return jsonify({'success': False, 'message': 'Erreur lors du téléchargement'}), 500
            
    except Exception as e:
        log_error(f"Erreur affichage document {document_id}: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de l\'accès au document'}), 500


# --- Signature électronique améliorée ---


@bp.route('/documents/<int:document_id>/signature', methods=['POST'])
@require_role('admin', 'manager', 'staff', 'client')
def sign_document(document_id):
    """Enregistre la signature d'un document avec validation juridique améliorée"""
    try:
        user = get_current_user()
        data = request.get_json() if request.is_json else request.form
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Vérifier que le document existe
        cursor.execute("""
            SELECT cd.*, c.name as customer_name, c.email as customer_email
            FROM customer_documents cd
            JOIN customers c ON cd.customer_id = c.id
            WHERE cd.id = %s
        """, [document_id])
        document = cursor.fetchone()
        
        if not document:
            return jsonify({'success': False, 'message': 'Document non trouvé'}), 404
        
        # Types de signature supportés
        signature_type = data.get('signature_type', 'manual')  # manual, docusign, adobe_sign, internal
        signature_data = data.get('signature_data', {})
        
        # Validation des données de signature selon le type
        signature_metadata = {
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'timestamp': datetime.now().isoformat(),
            'user_id': user.id,
            'user_name': user.name,
            'user_email': user.email
        }
        
        if signature_type == 'manual':
            # Signature manuelle avec coordonnées
            if not signature_data.get('signature_image'):
                return jsonify({'success': False, 'message': 'Image de signature requise'}), 400
            
            signature_metadata.update({
                'signature_method': 'manual_drawing',
                'canvas_data': signature_data.get('signature_image'),
                'validation_method': 'image_hash'
            })
            
        elif signature_type == 'docusign':
            # Intégration DocuSign (placeholder pour intégration future)
            envelope_id = signature_data.get('envelope_id')
            if not envelope_id:
                return jsonify({'success': False, 'message': 'Envelope ID DocuSign requis'}), 400
            
            signature_metadata.update({
                'signature_method': 'docusign',
                'envelope_id': envelope_id,
                'validation_method': 'docusign_api',
                'provider_status': 'completed'
            })
            
        elif signature_type == 'adobe_sign':
            # Intégration Adobe Sign (placeholder pour intégration future)
            agreement_id = signature_data.get('agreement_id')
            if not agreement_id:
                return jsonify({'success': False, 'message': 'Agreement ID Adobe Sign requis'}), 400
            
            signature_metadata.update({
                'signature_method': 'adobe_sign',
                'agreement_id': agreement_id,
                'validation_method': 'adobe_api',
                'provider_status': 'completed'
            })
            
        elif signature_type == 'internal':
            # Signature électronique interne avec confirmation PIN
            pin_code = signature_data.get('pin_code')
            if not pin_code or len(pin_code) < 4:
                return jsonify({'success': False, 'message': 'Code PIN de signature requis (min 4 caractères)'}), 400
            
            # TODO: Vérifier le PIN contre une base de données ou générer un nouveau PIN
            signature_metadata.update({
                'signature_method': 'internal_pin',
                'pin_verified': True,
                'validation_method': 'pin_verification'
            })
        
        # Validation juridique supplémentaire
        legal_validation = {
            'consent_confirmed': data.get('consent_confirmed', False),
            'identity_verified': data.get('identity_verified', False),
            'terms_accepted': data.get('terms_accepted', False),
            'signature_intent': data.get('signature_intent', 'agree'),
            'legal_framework': 'EU_eIDAS',  # Framework juridique européen
            'authentication_level': 'substantial',  # basic, substantial, high
        }
        
        # Vérifications obligatoires
        if not legal_validation['consent_confirmed']:
            return jsonify({'success': False, 'message': 'Consentement à la signature électronique requis'}), 400
        
        if not legal_validation['terms_accepted']:
            return jsonify({'success': False, 'message': 'Acceptation des conditions requise'}), 400
        
        # Génération d'un hash de signature pour intégrité
        signature_hash = hashlib.sha256(
            (str(document_id) + str(user.id) + str(datetime.now()) + 
             json.dumps(signature_metadata, sort_keys=True)).encode()
        ).hexdigest()
        
        # Enregistrement de la signature
        cursor.execute("""
            UPDATE customer_documents
            SET 
                is_signed = TRUE,
                signed_at = NOW(),
                signed_by = %s,
                signature_type = %s,
                signature_metadata = %s,
                signature_hash = %s,
                legal_validation = %s,
                updated_at = NOW()
            WHERE id = %s
        """, [
            user.id,
            signature_type,
            json.dumps(signature_metadata),
            signature_hash,
            json.dumps(legal_validation),
            document_id
        ])
        
        # Log de l'activité de signature
        log_activity(
            user.id, 'sign_document',
            entity_type='document', entity_id=document_id,
            details=f'Document signé: {document["title"]}, Méthode: {signature_type}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Log d'accès pour audit
        cursor.execute("""
            INSERT INTO customer_document_access_log
            (document_id, customer_id, accessed_by, access_type, details, ip_address, user_agent, accessed_at)
            VALUES (%s, %s, %s, 'signature', %s, %s, %s, NOW())
        """, [
            document_id, document['customer_id'], user.id,
            f'Signature {signature_type}: {signature_hash[:16]}',
            request.remote_addr, request.headers.get('User-Agent')
        ])
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Document signé avec succès',
            'signature': {
                'hash': signature_hash,
                'type': signature_type,
                'timestamp': signature_metadata['timestamp'],
                'legal_validation': legal_validation,
                'document_id': document_id
            }
        })
        
    except Exception as e:
        log_error(f"Erreur signature document {document_id}: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de la signature'}), 500
        
        signature_data = data.get('signature_data', '{}')
        signature_provider = data.get('provider', 'internal')
        signed_by = data.get('signed_by', '')
        signature_reference = data.get('signature_reference', '')
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get document info
        cursor.execute("""
            SELECT id, customer_id, title, is_signed 
            FROM customer_documents 
            WHERE id = %s
        """, [document_id])
        document = cursor.fetchone()
        
        if not document:
            return jsonify({'success': False, 'message': 'Document non trouvé'}), 404
            
        if document['is_signed']:
            return jsonify({'success': False, 'message': 'Document déjà signé'}), 400
        
        # Update document signature status
        cursor.execute("""
            UPDATE customer_documents SET
            is_signed = TRUE,
            signed_at = NOW(),
            signed_by = %s,
            signature_provider = %s,
            signature_reference = %s,
            signature_data = %s,
            updated_at = NOW()
            WHERE id = %s
        """, [signed_by, signature_provider, signature_reference, signature_data, document_id])
        
        # Log access
        user_id = session.get('user_id')
        cursor.execute("""
            INSERT INTO customer_document_access_log
            (document_id, customer_id, accessed_by, access_type, ip_address, accessed_at)
            VALUES (%s, %s, %s, 'signature', %s, NOW())
        """, [document_id, document['customer_id'], user_id, request.remote_addr])
        
        # Activity will be logged by database trigger
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Document signé avec succès',
            'signed_at': datetime.now().isoformat(),
            'signed_by': signed_by
        })
    except Exception as e:
        log_error(f"Erreur signature document {document_id}: {e}")
        return jsonify({'success': False, 'message': 'Erreur signature document'}), 500


@bp.route('/documents/<int:document_id>', methods=['DELETE'])
@require_role('admin', 'manager', 'staff')
def delete_document(document_id):
    """Supprime un document (soft delete)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get document info
        cursor.execute("""
            SELECT customer_id, title, filename, file_path
            FROM customer_documents
            WHERE id = %s
        """, [document_id])
        document = cursor.fetchone()
        
        if not document:
            return jsonify({'success': False, 'message': 'Document non trouvé'}), 404
        
        # Soft delete by moving to archive or marking as deleted
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archived_title = f"[SUPPRIMÉ_{timestamp}] {document['title']}"
        
        cursor.execute("""
            UPDATE customer_documents
            SET title = %s, access_level = 'admin', updated_at = NOW()
            WHERE id = %s
        """, [archived_title, document_id])
        
        # Log activity
        user_id = session.get('user_id')
        log_customer_activity(
            document['customer_id'], 'document', document_id, 'customer_documents',
            f'Document supprimé: {document["title"]}',
            f'Fichier: {document["filename"]}',
            user_id
        )
        
        # Log access
        cursor.execute("""
            INSERT INTO customer_document_access_log
            (document_id, customer_id, accessed_by, access_type, ip_address, accessed_at)
            VALUES (%s, %s, %s, 'delete', %s, NOW())
        """, [document_id, document['customer_id'], user_id, request.remote_addr])
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Document supprimé'
        })
    except Exception as e:
        log_error(f"Erreur suppression document {document_id}: {e}")
        return jsonify({'success': False, 'message': 'Erreur suppression document'}), 500


# =====================================================
# BALANCE & PAYMENT HISTORY
# =====================================================

@bp.route('/<int:customer_id>/balance-history', methods=['GET'])
@require_role('admin', 'manager', 'staff')
def get_balance_history(customer_id):
    """Récupère l'historique des soldes d'un client"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        event_type = request.args.get('event_type')
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Build query
        where_conditions = ["customer_id = %s"]
        params = [customer_id]
        
        if event_type:
            where_conditions.append("event_type = %s")
            params.append(event_type)
        
        where_clause = " AND ".join(where_conditions)
        
        # Count total
        count_query = f"SELECT COUNT(*) as count FROM customer_balance_history WHERE {where_clause}"
        cursor.execute(count_query, params)
        total = cursor.fetchone()['count']
        
        # Get history with pagination
        query = f"""
            SELECT cbh.*, u.name as processed_by_name
            FROM customer_balance_history cbh
            LEFT JOIN users u ON cbh.processed_by = u.id
            WHERE {where_clause}
            ORDER BY cbh.created_at DESC
            LIMIT %s OFFSET %s
        """
        offset = (page - 1) * per_page
        params.extend([per_page, offset])
        
        cursor.execute(query, params)
        history = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        pagination = MiniPagination(total=total, page=page, per_page=per_page)
        
        return jsonify({
            'success': True,
            'history': history,
            'pagination': {
                'total': pagination.total,
                'page': pagination.page,
                'per_page': pagination.per_page,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
    except Exception as e:
        log_error(f"Erreur historique soldes client {customer_id}: {e}")
        return jsonify({'success': False, 'message': 'Erreur récupération historique'}), 500


@bp.route('/<int:customer_id>/balance-history', methods=['POST'])
@require_role('admin', 'manager', 'staff')
def add_balance_entry(customer_id):
    """Ajoute une entrée à l'historique des soldes"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        event_type = data.get('event_type', 'adjustment')
        amount = float(data.get('amount', 0))
        description = data.get('description', '')
        reference_id = data.get('reference_id')
        reference_table = data.get('reference_table')
        reference_number = data.get('reference_number', '')
        
        if amount == 0:
            return jsonify({'success': False, 'message': 'Montant requis'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get current balance
        cursor.execute("""
            SELECT balance_after FROM customer_balance_history
            WHERE customer_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, [customer_id])
        result = cursor.fetchone()
        balance_before = result['balance_after'] if result else 0.0
        
        balance_after = balance_before + amount
        user_id = session.get('user_id')
        
        # Add balance history entry
        cursor.execute("""
            INSERT INTO customer_balance_history
            (customer_id, event_type, reference_id, reference_table, reference_number,
             amount, balance_before, balance_after, description, processed_by, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, [
            customer_id, event_type, reference_id, reference_table, reference_number,
            amount, balance_before, balance_after, description, user_id
        ])
        
        # Log activity
        log_customer_activity(
            customer_id, 'system', None, 'customer_balance_history',
            f'Ajustement de solde: {amount}',
            f'Nouveau solde: {balance_after} - {description}',
            user_id
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Entrée ajoutée à l\'historique',
            'balance_after': balance_after
        })
    except Exception as e:
        log_error(f"Erreur ajout historique solde: {e}")
        return jsonify({'success': False, 'message': 'Erreur ajout entrée historique'}), 500


# =====================================================
# EXTENSIONS SPRINT 5-6 - CUSTOMER 360 AVANCÉ
# =====================================================

@bp.route('/<int:customer_id>/timeline/export')
def export_customer_timeline(customer_id):
    """Exporte la timeline en différents formats"""
    try:
        format_type = request.args.get('format', 'csv')
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Récupérer toutes les activités
        cursor.execute("""
            SELECT ca.*, u.name as actor_name
            FROM customer_activity ca
            LEFT JOIN users u ON ca.actor_id = u.id
            WHERE ca.customer_id = %s
            ORDER BY ca.created_at DESC
        """, [customer_id])
        activities = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if format_type == 'csv':
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Date', 'Type', 'Titre', 'Description', 'Acteur'])
            
            for activity in activities:
                writer.writerow([
                    activity['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                    activity['activity_type'],
                    activity['title'],
                    activity['description'] or '',
                    activity['actor_name'] or 'Système'
                ])
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=timeline_client_{customer_id}.csv'
            return response
        
        elif format_type == 'json':
            # Conversion datetime pour JSON
            for activity in activities:
                if isinstance(activity['created_at'], datetime):
                    activity['created_at'] = activity['created_at'].isoformat()
            
            response = make_response(json.dumps(activities, indent=2, ensure_ascii=False))
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Disposition'] = f'attachment; filename=timeline_client_{customer_id}.json'
            return response
        
        else:
            return jsonify({'success': False, 'message': 'Format non supporté'}), 400
            
    except Exception as e:
        log_error(f"Erreur export timeline: {e}")
        return jsonify({'success': False, 'message': 'Erreur export timeline'}), 500

@bp.route('/<int:customer_id>/documents/complete', methods=['GET'])
def get_customer_documents_complete(customer_id):
    """Liste complète des documents d'un client avec filtres"""
    try:
        document_type = request.args.get('type')
        signed_only = request.args.get('signed') == 'true'
        category = request.args.get('category')
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        query = """
            SELECT cd.*, u.name as created_by_name,
                   CASE 
                       WHEN cd.expires_at IS NOT NULL AND cd.expires_at < NOW() THEN 'expired'
                       WHEN cd.is_signed = 1 THEN 'signed'
                       ELSE 'pending'
                   END as status
            FROM customer_documents cd
            LEFT JOIN users u ON cd.created_by = u.id
            WHERE cd.customer_id = %s
        """
        params = [customer_id]
        
        if document_type:
            query += " AND cd.document_type = %s"
            params.append(document_type)
        
        if signed_only:
            query += " AND cd.is_signed = 1"
        
        if category:
            query += " AND cd.category = %s"
            params.append(category)
        
        query += " ORDER BY cd.created_at DESC"
        
        cursor.execute(query, params)
        documents = cursor.fetchall()
        
        # Statistiques des documents
        cursor.execute("""
            SELECT 
                COUNT(*) as total_documents,
                SUM(CASE WHEN is_signed = 1 THEN 1 ELSE 0 END) as signed_documents,
                SUM(CASE WHEN expires_at IS NOT NULL AND expires_at < NOW() THEN 1 ELSE 0 END) as expired_documents,
                SUM(file_size) as total_size
            FROM customer_documents
            WHERE customer_id = %s
        """, [customer_id])
        stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({
                'success': True, 
                'documents': documents,
                'stats': stats
            })
            
        return render_template(
            'customers/documents.html', 
            customer_id=customer_id,
            documents=documents,
            stats=stats
        )
    except Exception as e:
        log_error(f"Erreur récupération documents: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur récupération documents'}), 500
        flash('Erreur chargement documents', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))

@bp.route('/<int:customer_id>/documents/upload', methods=['POST'])
def upload_customer_document(customer_id):
    """Upload sécurisé de document avec calcul de hash"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Aucun fichier fourni'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Aucun fichier sélectionné'}), 400
        
        # Validation des paramètres
        document_type = request.form.get('document_type')
        title = request.form.get('title', 'Document sans titre')
        category = request.form.get('category', 'administrative')
        access_level = request.form.get('access_level', 'private')
        
        if not document_type:
            return jsonify({'success': False, 'message': 'Type de document requis'}), 400
        
        # Validation du type de fichier
        allowed_extensions = {'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif'}
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_extension not in allowed_extensions:
            return jsonify({'success': False, 'message': f'Type de fichier non autorisé. Types acceptés: {", ".join(allowed_extensions)}'}), 400
        
        # Configuration upload
        upload_base = current_app.config.get('UPLOAD_FOLDER', '/tmp')
        upload_dir = os.path.join(upload_base, 'customers', str(customer_id), 'documents')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Nom de fichier sécurisé avec timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{secure_filename(file.filename)}"
        file_path = os.path.join(upload_dir, filename)
        
        # Sauvegarde du fichier
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        # Calcul hash SHA-256 pour intégrité
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        file_hash = sha256_hash.hexdigest()
        
        # Utilisateur courant
        user_id = session.get('user_id')  # Adaptation selon votre système d'auth
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Enregistrement en base
        cursor.execute("""
            INSERT INTO customer_documents
            (customer_id, document_type, category, title, filename, file_path, 
             file_size, mime_type, hash_sha256, access_level, created_by, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, [
            customer_id, document_type, category, title, filename, file_path,
            file_size, file.content_type, file_hash, access_level, user_id
        ])
        document_id = cursor.lastrowid
        
        # Log d'activité
        log_customer_activity_sprint56(
            customer_id, 
            'document', 
            f"Document ajouté: {title}",
            f"Type: {document_type}, Taille: {file_size} bytes",
            document_id,
            'customer_documents',
            user_id
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Document téléversé avec succès',
            'document': {
                'id': document_id,
                'title': title,
                'filename': filename,
                'size': file_size,
                'type': document_type,
                'hash': file_hash
            }
        })
        
    except Exception as e:
        log_error(f"Erreur upload document: {e}")
        return jsonify({'success': False, 'message': 'Erreur upload document'}), 500

@bp.route('/<int:customer_id>/finances/summary', methods=['GET'])
def get_customer_financial_summary(customer_id):
    """Résumé financier complet du client"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Profil financier de base
        cursor.execute("SELECT * FROM customer_finances WHERE customer_id = %s", [customer_id])
        finance_profile = cursor.fetchone()
        
        # Créer profil par défaut si inexistant
        if not finance_profile:
            cursor.execute("""
                INSERT INTO customer_finances (customer_id, created_at)
                VALUES (%s, NOW())
            """, [customer_id])
            conn.commit()
            
            cursor.execute("SELECT * FROM customer_finances WHERE customer_id = %s", [customer_id])
            finance_profile = cursor.fetchone()
        
        # Calcul du solde actuel depuis les factures existantes
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN status IN ('open', 'sent') THEN 1 END) as open_invoices,
                COALESCE(SUM(CASE WHEN status IN ('open', 'sent') THEN total_amount ELSE 0 END), 0) as total_outstanding,
                COALESCE(SUM(CASE WHEN status IN ('open', 'sent') AND due_date < NOW() THEN total_amount ELSE 0 END), 0) as overdue_amount,
                MIN(CASE WHEN status IN ('open', 'sent') THEN due_date END) as earliest_due_date
            FROM invoices
            WHERE customer_id = %s
        """, [customer_id])
        ar_summary = cursor.fetchone()
        
        # Historique des paiements (6 derniers mois)
        cursor.execute("""
            SELECT 
                DATE_FORMAT(created_at, '%%Y-%%m') as month,
                COUNT(*) as invoice_count,
                SUM(total_amount) as total_invoiced
            FROM invoices
            WHERE customer_id = %s 
            AND created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(created_at, '%%Y-%%m')
            ORDER BY month DESC
        """, [customer_id])
        payment_history = cursor.fetchall()
        
        # Calcul score de risque
        risk_factors = {
            'overdue_amount': float(ar_summary['overdue_amount'] or 0),
            'days_overdue': 0,
            'payment_history_score': 85,  # Score par défaut
            'credit_utilization': 0
        }
        
        if ar_summary['earliest_due_date'] and ar_summary['earliest_due_date'] < datetime.now().date():
            risk_factors['days_overdue'] = (datetime.now().date() - ar_summary['earliest_due_date']).days
        
        # Score de risque simplifié (0-100, plus élevé = plus risqué)
        risk_score = min(100, max(0, 
            (risk_factors['days_overdue'] * 2) + 
            (risk_factors['overdue_amount'] / 1000 * 10)
        ))
        
        cursor.close()
        conn.close()
        
        financial_summary = {
            'finance_profile': finance_profile,
            'ar_summary': ar_summary,
            'payment_history': payment_history,
            'risk_score': round(risk_score, 1),
            'risk_factors': risk_factors
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'financial_summary': financial_summary})
        
        return render_template(
            'customers/finances.html',
            customer_id=customer_id,
            **financial_summary
        )
        
    except Exception as e:
        log_error(f"Erreur résumé financier: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur résumé financier'}), 500
        flash('Erreur chargement résumé financier', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))

@bp.route('/<int:customer_id>/dashboard-360', methods=['GET'])
def customer_360_dashboard(customer_id):
    """Tableau de bord Client 360 unifié"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Informations client de base
        cursor.execute("SELECT * FROM customers WHERE id = %s", [customer_id])
        customer = cursor.fetchone()
        
        if not customer:
            return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
        
        # Timeline récente (10 dernières activités)
        cursor.execute("""
            SELECT ca.*, u.name as actor_name
            FROM customer_activity ca
            LEFT JOIN users u ON ca.actor_id = u.id
            WHERE ca.customer_id = %s
            ORDER BY ca.created_at DESC
            LIMIT 10
        """, [customer_id])
        recent_timeline = cursor.fetchall()
        
        # Véhicules et statuts
        cursor.execute("""
            SELECT v.*, 
                   COUNT(wo.id) as total_work_orders,
                   SUM(CASE WHEN wo.status = 'open' THEN 1 ELSE 0 END) as open_work_orders,
                   MAX(wo.scheduled_date) as last_service_date
            FROM vehicles v
            LEFT JOIN work_orders wo ON v.id = wo.vehicle_id
            WHERE v.customer_id = %s
            GROUP BY v.id
            ORDER BY v.created_at DESC
        """, [customer_id])
        vehicles = cursor.fetchall()
        
        # Résumé financier
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN status IN ('open', 'sent') THEN 1 END) as open_invoices,
                SUM(CASE WHEN status IN ('open', 'sent') THEN total_amount ELSE 0 END) as outstanding_amount,
                SUM(CASE WHEN status = 'paid' THEN total_amount ELSE 0 END) as paid_amount
            FROM invoices
            WHERE customer_id = %s
        """, [customer_id])
        financial_summary = cursor.fetchone()
        
        # Métriques de communication
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN activity_type = 'communication' THEN 1 ELSE 0 END) as total_communications,
                SUM(CASE WHEN activity_type = 'communication' AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as recent_communications
            FROM customer_activity
            WHERE customer_id = %s
        """, [customer_id])
        communication_stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        dashboard_data = {
            'customer': customer,
            'recent_timeline': recent_timeline,
            'vehicles': vehicles,
            'financial_summary': financial_summary,
            'communication_stats': communication_stats,
            'summary_cards': {
                'total_vehicles': len(vehicles),
                'open_work_orders': sum(v['open_work_orders'] for v in vehicles),
                'outstanding_amount': financial_summary['outstanding_amount'] or 0,
                'total_communications': communication_stats['total_communications'] or 0
            }
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'dashboard': dashboard_data})
        
        return render_template(
            'customers/dashboard_360.html',
            customer_id=customer_id,
            **dashboard_data
        )
        
    except Exception as e:
        log_error(f"Erreur dashboard Client 360: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur dashboard Client 360'}), 500
        flash('Erreur chargement dashboard Client 360', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))

# =====================================================
# FONCTIONS HELPER POUR LES EXTENSIONS
# =====================================================

def log_customer_activity_sprint56(customer_id, activity_type, title, description=None, related_id=None, related_table=None, actor_id=None):
    """Log une activité dans la timeline client"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Métadonnées contextuelles
        metadata = {
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
            'timestamp': datetime.now().isoformat()
        }
        
        cursor.execute("""
            INSERT INTO customer_activity 
            (customer_id, activity_type, title, description, related_id, related_table, actor_id, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, [
            customer_id, activity_type, title, description, 
            related_id, related_table, actor_id, json.dumps(metadata)
        ])
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        log_error(f"Erreur log activité client: {e}")

def format_time_ago(timestamp):
    """Formate un timestamp en format 'il y a X temps'"""
    if not timestamp:
        return "Date inconnue"
    
    now = datetime.now()
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    diff = now - timestamp
    
    if diff.days > 0:
        return f"il y a {diff.days} jour{'s' if diff.days > 1 else ''}"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"il y a {hours} heure{'s' if hours > 1 else ''}"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"il y a {minutes} minute{'s' if minutes > 1 else ''}"
    else:
        return "à l'instant"

# --- Sprint 7-8: Fonctionnalités avancées ---

@bp.route('/<int:customer_id>/analytics', methods=['GET'])
@require_role('admin', 'manager', 'staff')
def get_customer_analytics(customer_id):
    """Récupère les analytics avancées d'un client (RFM, LTV, etc.)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Récupérer les analytics RFM
        cursor.execute("""
            SELECT * FROM customer_analytics 
            WHERE customer_id = %s
        """, [customer_id])
        analytics = cursor.fetchone()
        
        # Récupérer les KPIs
        cursor.execute("""
            SELECT * FROM customer_kpis 
            WHERE customer_id = %s
        """, [customer_id])
        kpis = cursor.fetchone()
        
        # Récupérer les recommandations actives
        cursor.execute("""
            SELECT * FROM customer_recommendations 
            WHERE customer_id = %s AND is_active = TRUE
            ORDER BY score DESC
            LIMIT 10
        """, [customer_id])
        recommendations = cursor.fetchall()
        
        # Récupérer les récompenses de fidélité
        cursor.execute("""
            SELECT * FROM loyalty_rewards 
            WHERE customer_id = %s 
            ORDER BY earned_date DESC
            LIMIT 5
        """, [customer_id])
        loyalty_rewards = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        data = {
            'analytics': analytics,
            'kpis': kpis,
            'recommendations': recommendations,
            'loyalty_rewards': loyalty_rewards
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, **data})
        
        return render_template('customers/analytics.html', customer_id=customer_id, **data)
    except Exception as e:
        log_error(f"Erreur analytics client: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur analytics'}), 500
        flash('Erreur chargement analytics', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))

@bp.route('/<int:customer_id>/rfm/calculate', methods=['POST'])
@require_role('admin', 'manager')
def calculate_customer_rfm(customer_id):
    """Calcule et met à jour le score RFM d'un client"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Appel de la procédure stockée
        cursor.callproc('CalculateCustomerRFM', [customer_id])
        
        # Récupérer le résultat mis à jour
        cursor.execute("""
            SELECT rfm_segment, recency_score, frequency_score, monetary_score, calculated_at
            FROM customer_analytics 
            WHERE customer_id = %s
        """, [customer_id])
        result = cursor.fetchone()
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Score RFM calculé avec succès',
            'rfm_data': {
                'segment': result[0] if result else None,
                'recency_score': result[1] if result else 0,
                'frequency_score': result[2] if result else 0,
                'monetary_score': result[3] if result else 0,
                'calculated_at': result[4].isoformat() if result and result[4] else None
            }
        })
    except Exception as e:
        log_error(f"Erreur calcul RFM: {e}")
        return jsonify({'success': False, 'message': 'Erreur calcul RFM'}), 500

@bp.route('/duplicates', methods=['GET'])
@require_role('admin', 'manager')
def list_customer_duplicates():
    """Liste les doublons de clients détectés"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        status_filter = request.args.get('status', 'detected')
        
        cursor.execute("""
            SELECT 
                cd.*,
                c1.nom as primary_name,
                c1.email as primary_email,
                c1.telephone as primary_phone,
                c2.nom as duplicate_name,
                c2.email as duplicate_email,
                c2.telephone as duplicate_phone
            FROM customer_duplicates cd
            JOIN customers c1 ON cd.customer_id_primary = c1.id
            JOIN customers c2 ON cd.customer_id_duplicate = c2.id
            WHERE cd.status = %s
            ORDER BY cd.confidence_score DESC, cd.created_at DESC
        """, [status_filter])
        duplicates = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'duplicates': duplicates})
        
        return render_template('customers/duplicates.html', duplicates=duplicates, status_filter=status_filter)
    except Exception as e:
        log_error(f"Erreur liste doublons: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur liste doublons'}), 500
        flash('Erreur chargement doublons', 'error')
        return redirect(url_for('customers.index'))

@bp.route('/duplicates/<int:duplicate_id>/review', methods=['POST'])
@require_role('admin', 'manager')
def review_duplicate(duplicate_id):
    """Traite un doublon (fusion ou ignorer)"""
    try:
        data = request.get_json()
        action = data.get('action')  # 'merge' ou 'ignore'
        notes = data.get('notes', '')
        
        if action not in ['merge', 'ignore']:
            return jsonify({'success': False, 'message': 'Action invalide'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Récupérer le doublon
        cursor.execute("SELECT * FROM customer_duplicates WHERE id = %s", [duplicate_id])
        duplicate = cursor.fetchone()
        
        if not duplicate:
            return jsonify({'success': False, 'message': 'Doublon non trouvé'}), 404
        
        if action == 'merge':
            # Fusionner les clients - transférer toutes les données vers le client principal
            primary_id = duplicate['customer_id_primary']
            duplicate_customer_id = duplicate['customer_id_duplicate']
            
            # Transférer les véhicules
            cursor.execute("""
                UPDATE vehicles SET customer_id = %s WHERE customer_id = %s
            """, [primary_id, duplicate_customer_id])
            
            # Transférer les interventions
            cursor.execute("""
                UPDATE interventions SET customer_id = %s WHERE customer_id = %s
            """, [primary_id, duplicate_customer_id])
            
            # Transférer les factures
            cursor.execute("""
                UPDATE invoices SET customer_id = %s WHERE customer_id = %s
            """, [primary_id, duplicate_customer_id])
            
            # Désactiver le client doublon
            cursor.execute("""
                UPDATE customers SET is_active = 0, 
                       nom = CONCAT(nom, ' [FUSIONNÉ]'),
                       updated_at = NOW()
                WHERE id = %s
            """, [duplicate_customer_id])
            
            status = 'merged'
            message = 'Clients fusionnés avec succès'
        else:
            status = 'ignored'
            message = 'Doublon ignoré'
        
        # Mettre à jour le statut du doublon
        cursor.execute("""
            UPDATE customer_duplicates 
            SET status = %s, notes = %s, reviewed_at = NOW(), reviewed_by = %s
            WHERE id = %s
        """, [status, notes, session.get('user_id'), duplicate_id])
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        log_error(f"Erreur review doublon: {e}")
        return jsonify({'success': False, 'message': 'Erreur traitement doublon'}), 500

@bp.route('/duplicates/detect', methods=['POST'])
@require_role('admin', 'manager')
def detect_duplicates():
    """Détecte automatiquement les doublons de clients"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Algorithme de détection simple basé sur email, téléphone et nom
        duplicates_found = 0
        
        # Détection par email identique
        cursor.execute("""
            SELECT c1.id as id1, c2.id as id2, c1.email
            FROM customers c1
            JOIN customers c2 ON c1.email = c2.email 
            WHERE c1.id < c2.id 
            AND c1.email IS NOT NULL 
            AND c1.email != ''
            AND c1.is_active = 1 
            AND c2.is_active = 1
        """)
        email_duplicates = cursor.fetchall()
        
        for dup in email_duplicates:
            # Vérifier si le doublon n'existe pas déjà
            cursor.execute("""
                SELECT id FROM customer_duplicates 
                WHERE (customer_id_primary = %s AND customer_id_duplicate = %s)
                OR (customer_id_primary = %s AND customer_id_duplicate = %s)
            """, [dup['id1'], dup['id2'], dup['id2'], dup['id1']])
            
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO customer_duplicates 
                    (customer_id_primary, customer_id_duplicate, confidence_score, match_criteria, status, created_at)
                    VALUES (%s, %s, 0.95, %s, 'detected', NOW())
                """, [dup['id1'], dup['id2'], json.dumps({'email': True})])
                duplicates_found += 1
        
        # Détection par téléphone identique
        cursor.execute("""
            SELECT c1.id as id1, c2.id as id2, c1.telephone
            FROM customers c1
            JOIN customers c2 ON c1.telephone = c2.telephone 
            WHERE c1.id < c2.id 
            AND c1.telephone IS NOT NULL 
            AND c1.telephone != ''
            AND c1.is_active = 1 
            AND c2.is_active = 1
        """)
        phone_duplicates = cursor.fetchall()
        
        for dup in phone_duplicates:
            cursor.execute("""
                SELECT id FROM customer_duplicates 
                WHERE (customer_id_primary = %s AND customer_id_duplicate = %s)
                OR (customer_id_primary = %s AND customer_id_duplicate = %s)
            """, [dup['id1'], dup['id2'], dup['id2'], dup['id1']])
            
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO customer_duplicates 
                    (customer_id_primary, customer_id_duplicate, confidence_score, match_criteria, status, created_at)
                    VALUES (%s, %s, 0.90, %s, 'detected', NOW())
                """, [dup['id1'], dup['id2'], json.dumps({'phone': True})])
                duplicates_found += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'{duplicates_found} doublon(s) détecté(s)',
            'duplicates_found': duplicates_found
        })
        
    except Exception as e:
        log_error(f"Erreur détection doublons: {e}")
        return jsonify({'success': False, 'message': 'Erreur détection doublons'}), 500

@bp.route('/delivery-routes', methods=['GET'])
@require_role('admin', 'manager', 'staff')
def delivery_routes():
    """Interface de planification des routes de livraison"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Filtres
        selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        technician_filter = request.args.get('technician')
        status_filter = request.args.get('status')
        
        # Récupérer les routes selon les filtres
        query = """
            SELECT 
                dr.*,
                t.prenom as technician_name,
                COUNT(rs.id) as stop_count,
                SUM(CASE WHEN rs.status = 'completed' THEN 1 ELSE 0 END) as completed_stops
            FROM delivery_routes dr
            LEFT JOIN technicians t ON dr.technician_id = t.id
            LEFT JOIN route_stops rs ON dr.id = rs.route_id
            WHERE dr.route_date = %s
        """
        params = [selected_date]
        
        if technician_filter:
            query += " AND dr.technician_id = %s"
            params.append(technician_filter)
        
        if status_filter:
            query += " AND dr.status = %s"
            params.append(status_filter)
        
        query += " GROUP BY dr.id ORDER BY dr.created_at DESC"
        
        cursor.execute(query, params)
        routes = cursor.fetchall()
        
        # Récupérer les arrêts pour chaque route
        for route in routes:
            cursor.execute("""
                SELECT rs.*, c.nom as customer_name
                FROM route_stops rs
                JOIN customers c ON rs.customer_id = c.id
                WHERE rs.route_id = %s
                ORDER BY rs.stop_order
            """, [route['id']])
            route['stops'] = cursor.fetchall()
        
        # Récupérer les techniciens
        cursor.execute("SELECT id, prenom, nom FROM technicians WHERE is_active = 1")
        technicians = cursor.fetchall()
        
        # Récupérer les clients disponibles pour nouvelles routes
        cursor.execute("""
            SELECT id, nom, prenom, adresse, ville 
            FROM customers 
            WHERE is_active = 1 
            ORDER BY nom, prenom
        """)
        available_customers = cursor.fetchall()
        
        # Statistiques
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN total_distance IS NOT NULL THEN total_distance ELSE 0 END) as total_km,
                SUM((SELECT COUNT(*) FROM route_stops WHERE route_id = dr.id)) as total_stops
            FROM delivery_routes dr
            WHERE dr.route_date = %s
        """, [selected_date])
        route_stats = cursor.fetchone() or {'total': 0, 'total_km': 0, 'total_stops': 0}
        
        cursor.close()
        conn.close()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({
                'success': True,
                'routes': routes,
                'technicians': technicians,
                'route_stats': route_stats
            })
        
        return render_template('customers/delivery_routes.html', 
                             routes=routes, 
                             technicians=technicians,
                             available_customers=available_customers,
                             route_stats=route_stats,
                             selected_date=selected_date,
                             technician_filter=technician_filter,
                             status_filter=status_filter)
        
    except Exception as e:
        log_error(f"Erreur routes livraison: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur routes livraison'}), 500
        flash('Erreur chargement routes livraison', 'error')
        return redirect(url_for('customers.index'))

@bp.route('/export', methods=['GET'])
@require_role('admin', 'manager')
def export_customers():
    """Exporte la liste des clients selon les filtres appliqués"""
    try:
        # Récupérer les paramètres de filtre depuis l'URL
        search = request.args.get('search', '')
        customer_type = request.args.get('customer_type', '')
        status = request.args.get('status', '')
        city = request.args.get('city', '')
        format_type = request.args.get('format', 'csv')
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Construire la requête avec les mêmes filtres que l'index
        query = "SELECT * FROM customers WHERE 1=1"
        params = []
        
        if search:
            query += " AND (nom LIKE %s OR prenom LIKE %s OR email LIKE %s OR telephone LIKE %s OR company LIKE %s)"
            search_term = f"%{search}%"
            params.extend([search_term] * 5)
        
        if customer_type:
            query += " AND customer_type = %s"
            params.append(customer_type)
        
        if status:
            if status == 'active':
                query += " AND is_active = 1"
            elif status == 'inactive':
                query += " AND is_active = 0"
        
        if city:
            query += " AND ville LIKE %s"
            params.append(f"%{city}%")
        
        query += " ORDER BY nom, prenom"
        
        cursor.execute(query, params)
        customers = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if format_type == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # En-têtes
            writer.writerow([
                'ID', 'Type', 'Nom', 'Prénom', 'Entreprise', 'Email', 'Téléphone',
                'Adresse', 'Ville', 'Code Postal', 'Statut', 'Date Création'
            ])
            
            # Données
            for customer in customers:
                writer.writerow([
                    customer['id'],
                    customer.get('customer_type', ''),
                    customer.get('nom', ''),
                    customer.get('prenom', ''),
                    customer.get('company', ''),
                    customer.get('email', ''),
                    customer.get('telephone', ''),
                    customer.get('adresse', ''),
                    customer.get('ville', ''),
                    customer.get('code_postal', ''),
                    'Actif' if customer.get('is_active') else 'Inactif',
                    customer.get('created_at', '').strftime('%Y-%m-%d %H:%M:%S') if customer.get('created_at') else ''
                ])
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename=clients_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            return response
        
        elif format_type == 'json':
            # Conversion des dates pour JSON
            for customer in customers:
                for key, value in customer.items():
                    if isinstance(value, datetime):
                        customer[key] = value.isoformat()
            
            response = make_response(json.dumps(customers, indent=2, ensure_ascii=False))
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename=clients_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            return response
        
        else:
            return jsonify({'success': False, 'message': 'Format non supporté'}), 400
        
    except Exception as e:
        log_error(f"Erreur export clients: {e}")
        return jsonify({'success': False, 'message': 'Erreur export clients'}), 500


@bp.route('/rfm-segments')
def get_rfm_segments():
    """
    Affiche la page des segments RFM
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les segments RFM
        cursor.execute("""
            SELECT 
                segment,
                COUNT(*) as customer_count,
                AVG(CAST(recency AS FLOAT)) as avg_recency,
                AVG(CAST(frequency AS FLOAT)) as avg_frequency,
                AVG(CAST(monetary AS FLOAT)) as avg_monetary
            FROM customer_rfm 
            GROUP BY segment
            ORDER BY segment
        """)
        
        segments = cursor.fetchall()
        
        # Récupérer les clients par segment
        cursor.execute("""
            SELECT 
                cr.*,
                c.nom,
                c.prenom,
                c.company,
                c.email
            FROM customer_rfm cr
            JOIN customers c ON cr.customer_id = c.id
            ORDER BY cr.segment, cr.rfm_score DESC
        """)
        
        customers_rfm = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('customers/rfm_segments.html', 
                             segments=segments, 
                             customers_rfm=customers_rfm)
        
    except Exception as e:
        log_error(f"Erreur segments RFM: {e}")
        flash('Erreur lors de la récupération des segments RFM', 'error')
        return redirect(url_for('customers.index'))
