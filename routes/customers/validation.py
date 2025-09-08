"""
Module de validation pour les formulaires clients
"""

import re
from flask import request, jsonify
from core.utils import log_error
from .utils import require_role, get_current_user
from .geocoding import geocode_address

# Configuration de validation avancée des formulaires
FORM_VALIDATION_CONFIG = {
    'business_rules': {
        'siret': {
            'required_for_business': True,
            'format': r'^[0-9]{14}$',
            'api_validation': False  # Désactivé pour éviter les appels externes
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
        postal_patterns = {
            'FR': r'^[0-9]{5}$',
            'BE': r'^[0-9]{4}$',
            'CH': r'^[0-9]{4}$',
            'DE': r'^[0-9]{5}$',
            'ES': r'^[0-9]{5}$',
            'IT': r'^[0-9]{5}$',
            'GB': r'^[A-Z]{1,2}[0-9R][0-9A-Z]? [0-9][A-Z]{2}$',
            'US': r'^[0-9]{5}(-[0-9]{4})?$',
            'CA': r'^[A-Z][0-9][A-Z] [0-9][A-Z][0-9]$'  # Format canadien K1A 0A6
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


# Route API pour validation en temps réel (à importer dans le blueprint principal)
def setup_validation_routes(bp):
    """Configure les routes de validation"""
    
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
