"""
Utilitaires système pour ChronoTech
Fonctions helpers, validation, formatage et outils divers
"""

import os
import re
import json
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from werkzeug.utils import secure_filename
from email_validator import validate_email, EmailNotValidError
import phonenumbers
from phonenumbers import NumberParseException

logger = logging.getLogger(__name__)

# Configuration des fichiers autorisés
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_DOC_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS.union(ALLOWED_DOC_EXTENSIONS)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

class ValidationError(Exception):
    """Exception pour les erreurs de validation"""
    pass

class FileUploadError(Exception):
    """Exception pour les erreurs d'upload de fichiers"""
    pass

def generate_secure_token(length=32):
    """Générer un token sécurisé"""
    return secrets.token_urlsafe(length)

def hash_password(password, salt=None):
    """Hasher un mot de passe avec salt"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Utilisation de PBKDF2 pour hasher le mot de passe
    import hashlib
    pwd_hash = hashlib.pbkdf2_hmac('sha256', 
                                   password.encode('utf-8'), 
                                   salt.encode('utf-8'), 
                                   100000)  # 100k iterations
    
    return f"{salt}${pwd_hash.hex()}"

def verify_password(password, hashed_password):
    """Vérifier un mot de passe contre son hash"""
    try:
        salt, pwd_hash = hashed_password.split('$')
        return hash_password(password, salt) == hashed_password
    except ValueError:
        return False

def validate_email_address(email):
    """Valider une adresse email"""
    try:
        # Normaliser l'email
        validation = validate_email(email)
        return validation.email
    except EmailNotValidError:
        raise ValidationError("Adresse email invalide")

def validate_phone_number(phone, country_code='FR'):
    """Valider un numéro de téléphone"""
    try:
        parsed_number = phonenumbers.parse(phone, country_code)
        if phonenumbers.is_valid_number(parsed_number):
            return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        else:
            raise ValidationError("Numéro de téléphone invalide")
    except NumberParseException:
        raise ValidationError("Format de numéro de téléphone invalide")

def validate_work_order_data(data):
    """Valider les données d'un bon de travail"""
    errors = []
    
    # Validation du numéro de réclamation
    if not data.get('claim_number'):
        errors.append("Le numéro de réclamation est requis")
    elif not re.match(r'^WO-\d{4}-\d{3,}$', data['claim_number']):
        errors.append("Format du numéro de réclamation invalide (format attendu: WO-YYYY-XXX)")
    
    # Validation du nom du client
    if not data.get('customer_name') or len(data['customer_name'].strip()) < 2:
        errors.append("Le nom du client est requis (minimum 2 caractères)")
    
    # Validation de l'adresse
    if not data.get('customer_address') or len(data['customer_address'].strip()) < 5:
        errors.append("L'adresse du client est requise (minimum 5 caractères)")
    
    # Validation du téléphone
    if data.get('customer_phone'):
        try:
            validate_phone_number(data['customer_phone'])
        except ValidationError as e:
            errors.append(f"Téléphone invalide: {e}")
    
    # Validation de la description
    if not data.get('description') or len(data['description'].strip()) < 10:
        errors.append("La description est requise (minimum 10 caractères)")
    
    # Validation de la priorité
    valid_priorities = ['low', 'medium', 'high', 'urgent']
    if data.get('priority') not in valid_priorities:
        errors.append(f"Priorité invalide. Valeurs autorisées: {', '.join(valid_priorities)}")
    
    # Validation de la durée estimée
    if data.get('estimated_duration'):
        try:
            duration = int(data['estimated_duration'])
            if duration <= 0 or duration > 480:  # Max 8 heures
                errors.append("La durée estimée doit être entre 1 et 480 minutes")
        except (ValueError, TypeError):
            errors.append("La durée estimée doit être un nombre entier")
    
    # Validation de la date programmée
    if data.get('scheduled_date'):
        try:
            scheduled = datetime.fromisoformat(data['scheduled_date'].replace('Z', '+00:00'))
            if scheduled < datetime.now():
                errors.append("La date programmée ne peut pas être dans le passé")
        except ValueError:
            errors.append("Format de date programmée invalide")
    
    if errors:
        raise ValidationError("; ".join(errors))
    
    return True

def validate_user_data(data, is_update=False):
    """Valider les données utilisateur"""
    errors = []
    
    # Validation du nom
    if not is_update or 'name' in data:
        if not data.get('name') or len(data['name'].strip()) < 2:
            errors.append("Le nom est requis (minimum 2 caractères)")
    
    # Validation de l'email
    if not is_update or 'email' in data:
        if not data.get('email'):
            errors.append("L'email est requis")
        else:
            try:
                validate_email_address(data['email'])
            except ValidationError as e:
                errors.append(f"Email invalide: {e}")
    
    # Validation du mot de passe
    if not is_update or 'password' in data:
        if not data.get('password'):
            if not is_update:  # Mot de passe requis pour création
                errors.append("Le mot de passe est requis")
        else:
            password = data['password']
            if len(password) < 8:
                errors.append("Le mot de passe doit contenir au moins 8 caractères")
            if not re.search(r'[A-Za-z]', password):
                errors.append("Le mot de passe doit contenir au moins une lettre")
            if not re.search(r'\d', password):
                errors.append("Le mot de passe doit contenir au moins un chiffre")
    
    # Validation du rôle
    if not is_update or 'role' in data:
        valid_roles = ['admin', 'manager', 'supervisor', 'technician']
        if data.get('role') not in valid_roles:
            errors.append(f"Rôle invalide. Valeurs autorisées: {', '.join(valid_roles)}")
    
    if errors:
        raise ValidationError("; ".join(errors))
    
    return True

def allowed_file(filename):
    """Vérifier si le fichier est autorisé"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Déterminer le type de fichier"""
    if not filename:
        return 'unknown'
    
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return 'image'
    elif ext in ALLOWED_DOC_EXTENSIONS:
        return 'document'
    else:
        return 'unknown'

def generate_unique_filename(filename, upload_folder=None):
    """Générer un nom de fichier unique"""
    # Sécuriser le nom de fichier
    filename = secure_filename(filename)
    
    # Générer un nom unique avec timestamp
    name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = secrets.token_hex(4)
    
    new_filename = f"{name}_{timestamp}_{unique_id}{ext}"
    
    # Vérifier l'unicité si dossier fourni
    if upload_folder and os.path.exists(upload_folder):
        counter = 1
        base_filename = new_filename
        while os.path.exists(os.path.join(upload_folder, new_filename)):
            name_part, ext_part = os.path.splitext(base_filename)
            new_filename = f"{name_part}_{counter}{ext_part}"
            counter += 1
    
    return new_filename

def format_file_size(size_bytes):
    """Formater la taille de fichier en format lisible"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def validate_file_upload(file, max_size=MAX_FILE_SIZE):
    """Valider un fichier uploadé"""
    if not file:
        raise FileUploadError("Aucun fichier sélectionné")
    
    if file.filename == '':
        raise FileUploadError("Nom de fichier vide")
    
    if not allowed_file(file.filename):
        raise FileUploadError(f"Type de fichier non autorisé. Types acceptés: {', '.join(ALLOWED_EXTENSIONS)}")
    
    # Vérifier la taille du fichier si possible
    if hasattr(file, 'content_length') and file.content_length:
        if file.content_length > max_size:
            raise FileUploadError(f"Fichier trop volumineux. Taille maximale: {format_file_size(max_size)}")
    
    return True

def sanitize_html(text):
    """Nettoyer le HTML basique (très simple)"""
    if not text:
        return text
    
    # Suppression des balises HTML de base
    import html
    text = html.escape(text)
    
    return text

def format_datetime(dt, format_str='%d/%m/%Y %H:%M'):
    """Formater une date/heure"""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return dt
    
    if dt:
        return dt.strftime(format_str)
    return ''

def format_duration(minutes):
    """Formater une durée en minutes vers un format lisible"""
    if not minutes:
        return '0 min'
    
    try:
        total_minutes = int(minutes)
        hours = total_minutes // 60
        remaining_minutes = total_minutes % 60
        
        if hours > 0:
            if remaining_minutes > 0:
                return f"{hours}h {remaining_minutes}min"
            else:
                return f"{hours}h"
        else:
            return f"{remaining_minutes}min"
    except (ValueError, TypeError):
        return str(minutes)

def get_priority_label(priority):
    """Obtenir le label français pour une priorité"""
    priority_labels = {
        'low': 'Basse',
        'medium': 'Moyenne',
        'high': 'Haute',
        'urgent': 'Urgente'
    }
    return priority_labels.get(priority, priority)

def get_status_label(status):
    """Obtenir le label français pour un statut"""
    status_labels = {
        'pending': 'En attente',
        'assigned': 'Assigné',
        'in_progress': 'En cours',
        'completed': 'Terminé',
        'cancelled': 'Annulé',
        'on_hold': 'En pause'
    }
    return status_labels.get(status, status)

def get_status_color(status):
    """Obtenir la couleur CSS pour un statut"""
    status_colors = {
        'pending': 'warning',
        'assigned': 'info',
        'in_progress': 'primary',
        'completed': 'success',
        'cancelled': 'danger',
        'on_hold': 'secondary'
    }
    return status_colors.get(status, 'secondary')

def get_priority_color(priority):
    """Obtenir la couleur CSS pour une priorité"""
    priority_colors = {
        'low': 'success',
        'medium': 'warning',
        'high': 'orange',
        'urgent': 'danger'
    }
    return priority_colors.get(priority, 'secondary')

def paginate_query_results(query_results, page=1, per_page=20):
    """Paginer les résultats d'une requête"""
    if not query_results:
        return {
            'items': [],
            'total': 0,
            'page': page,
            'per_page': per_page,
            'pages': 0,
            'has_prev': False,
            'has_next': False,
            'prev_num': None,
            'next_num': None
        }
    
    total = len(query_results)
    pages = (total + per_page - 1) // per_page
    
    start = (page - 1) * per_page
    end = start + per_page
    items = query_results[start:end]
    
    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': pages,
        'has_prev': page > 1,
        'has_next': page < pages,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if page < pages else None
    }

def search_in_text(search_term, text_fields):
    """Rechercher un terme dans plusieurs champs texte"""
    if not search_term or not text_fields:
        return False
    
    search_term = search_term.lower().strip()
    
    for field in text_fields:
        if field and search_term in str(field).lower():
            return True
    
    return False

def generate_claim_number():
    """Générer un numéro de réclamation unique"""
    year = datetime.now().year
    timestamp = datetime.now().strftime('%m%d%H%M')
    random_suffix = secrets.token_hex(2).upper()
    
    return f"WO-{year}-{timestamp}{random_suffix}"

def calculate_work_order_stats(work_orders):
    """Calculer les statistiques des bons de travail"""
    if not work_orders:
        return {
            'total': 0,
            'pending': 0,
            'in_progress': 0,
            'completed': 0,
            'urgent': 0,
            'avg_duration': 0
        }
    
    stats = {
        'total': len(work_orders),
        'pending': 0,
        'in_progress': 0,
        'completed': 0,
        'urgent': 0,
        'total_duration': 0,
        'count_with_duration': 0
    }
    
    for wo in work_orders:
        # Compter par statut
        status = wo.get('status', '')
        if status == 'pending':
            stats['pending'] += 1
        elif status == 'in_progress':
            stats['in_progress'] += 1
        elif status == 'completed':
            stats['completed'] += 1
        
        # Compter les urgents
        if wo.get('priority') == 'urgent':
            stats['urgent'] += 1
        
        # Calculer durée moyenne
        duration = wo.get('estimated_duration')
        if duration:
            try:
                stats['total_duration'] += int(duration)
                stats['count_with_duration'] += 1
            except (ValueError, TypeError):
                pass
    
    # Calculer la durée moyenne
    if stats['count_with_duration'] > 0:
        stats['avg_duration'] = stats['total_duration'] // stats['count_with_duration']
    else:
        stats['avg_duration'] = 0
    
    # Nettoyer les champs temporaires
    del stats['total_duration']
    del stats['count_with_duration']
    
    return stats

def export_to_csv(data, filename, headers=None):
    """Exporter des données vers un fichier CSV"""
    import csv
    import io
    
    if not data:
        return None
    
    output = io.StringIO()
    
    if headers:
        fieldnames = headers
    elif isinstance(data[0], dict):
        fieldnames = data[0].keys()
    else:
        fieldnames = [f'Column_{i+1}' for i in range(len(data[0]))]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for row in data:
        if isinstance(row, dict):
            writer.writerow(row)
        else:
            writer.writerow(dict(zip(fieldnames, row)))
    
    output.seek(0)
    return output.getvalue()

def log_info(message, context=None):
    """Logger une information avec contexte"""
    log_msg = f"Info: {str(message)}"
    if context:
        log_msg += f" | Contexte: {context}"
    
    logger.info(log_msg)

def log_warning(message, context=None):
    """Logger un avertissement avec contexte"""
    log_msg = f"Avertissement: {str(message)}"
    if context:
        log_msg += f" | Contexte: {context}"
    
    logger.warning(log_msg)

def log_error(error, context=None):
    """Logger une erreur avec contexte"""
    error_msg = f"Erreur: {str(error)}"
    if context:
        error_msg += f" | Contexte: {context}"
    
    logger.error(error_msg)

def setup_upload_folders(base_path):
    """Créer les dossiers d'upload nécessaires"""
    folders = [
        'uploads',
        'uploads/work_orders',
        'uploads/interventions',
        'uploads/profiles',
        'uploads/temp'
    ]
    
    created_folders = []
    for folder in folders:
        folder_path = os.path.join(base_path, folder)
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path, mode=0o755)
                created_folders.append(folder_path)
                logger.info(f"Dossier créé: {folder_path}")
            except OSError as e:
                logger.error(f"Erreur lors de la création du dossier {folder_path}: {e}")
    
    return created_folders

# Filtres Jinja2 personnalisés
def init_template_filters(app):
    """Initialiser les filtres de template personnalisés"""
    
    @app.template_filter('datetime')
    def datetime_filter(value, format='%d/%m/%Y %H:%M'):
        return format_datetime(value, format)
    
    @app.template_filter('datetime_format')
    def datetime_format_filter(value, format_type='default'):
        """Format une date en fonction du type spécifié."""
        if not value:
            return ''
        
        try:
            if isinstance(value, str):
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                
            formats = {
                'default': '%d/%m/%Y %H:%M',
                'short': '%d/%m/%Y',
                'time': '%H:%M',
                'full': '%d/%m/%Y à %H:%M',
                'month_year': '%B %Y',
                'iso': '%Y-%m-%dT%H:%M:%S',
                'relative': 'relative'
            }
            
            selected_format = formats.get(format_type, '%d/%m/%Y %H:%M')
            
            if format_type == 'relative':
                # Calcul du temps relatif
                now = datetime.now()
                diff = now - value
                
                if diff.days < 0:
                    return f"Dans {abs(diff.days)} jour(s)"
                elif diff.days == 0:
                    hours = diff.seconds // 3600
                    minutes = (diff.seconds % 3600) // 60
                    if hours > 0:
                        return f"Il y a {hours}h"
                    elif minutes > 0:
                        return f"Il y a {minutes}min"
                    else:
                        return "À l'instant"
                elif diff.days == 1:
                    return "Hier"
                elif diff.days < 7:
                    return f"Il y a {diff.days} jours"
                elif diff.days < 30:
                    return f"Il y a {diff.days // 7} semaine(s)"
                elif diff.days < 365:
                    return f"Il y a {diff.days // 30} mois"
                else:
                    return f"Il y a {diff.days // 365} an(s)"
            
            return value.strftime(selected_format)
        except Exception as e:
            log_error(f"Erreur formatage date {value}: {e}")
            return str(value)
    
    @app.template_filter('duration')
    def duration_filter(value):
        return format_duration(value)
    
    @app.template_filter('filesize')
    def filesize_filter(value):
        return format_file_size(value)
    
    @app.template_filter('priority_label')
    def priority_label_filter(value):
        return get_priority_label(value)
    
    @app.template_filter('status_label')
    def status_label_filter(value):
        return get_status_label(value)
    
    @app.template_filter('status_color')
    def status_color_filter(value):
        return get_status_color(value)
    
    @app.template_filter('priority_color')
    def priority_color_filter(value):
        return get_priority_color(value)
        
    @app.template_filter('escapejs')
    def escapejs_filter(value):
        """Échapper les caractères problématiques pour l'inclusion de valeurs dans le JavaScript."""
        if value is None:
            return ''
        value = str(value)
        chars = {
            '\\': '\\\\',
            '"': '\\"',
            "'": "\\'",
            '\n': '\\n',
            '\r': '\\r',
            '\t': '\\t',
            '</script>': '<\\/script>',  # Pour éviter les injections XSS
            '<': '\\u003C',
            '>': '\\u003E'
        }
        for c, r in chars.items():
            value = value.replace(c, r)
        return value
        
    @app.template_filter('currency')
    def currency_filter(value):
        """Formater un nombre en devise (€)."""
        if value is None:
            return '0,00 €'
        try:
            # Convertir en float si c'est une chaîne
            if isinstance(value, str):
                value = float(value.replace(',', '.'))
            # Formater avec séparateur de milliers et 2 décimales
            return f"{value:,.2f} €".replace(',', ' ').replace('.', ',')
        except (ValueError, TypeError) as e:
            log_warning(f"Erreur formatage devise {value}: {e}")
            return f"{value} €"
    
    @app.template_filter('consent_status_badge')
    def consent_status_badge_filter(status):
        """Retourne la classe CSS pour le badge de statut de consentement."""
        status_classes = {
            'granted': 'badge-success',
            'denied': 'badge-danger',
            'pending': 'badge-warning',
            'expired': 'badge-secondary',
            'revoked': 'badge-dark'
        }
        return status_classes.get(status, 'badge-secondary')
    
    @app.template_filter('invoice_status_badge')
    def invoice_status_badge_filter(status):
        """Retourne la classe CSS pour le badge de statut de facture."""
        status_classes = {
            'draft': 'badge-secondary',
            'pending': 'badge-warning',
            'paid': 'badge-success',
            'overdue': 'badge-danger',
            'cancelled': 'badge-dark',
            'sent': 'badge-info'
        }
        return status_classes.get(status, 'badge-secondary')

    @app.template_filter('request_status_color')
    def request_status_color_filter(status):
        """Retourne la classe CSS pour la couleur de statut de demande RGPD."""
        status_classes = {
            'pending': 'bg-warning',
            'processed': 'bg-success',
            'rejected': 'bg-danger',
            'in_progress': 'bg-info'
        }
        return status_classes.get(status, 'bg-secondary')

    @app.template_filter('request_type_icon')
    def request_type_icon_filter(request_type):
        """Retourne l'icône FontAwesome pour le type de demande RGPD."""
        type_icons = {
            'access': 'fa-eye',
            'delete': 'fa-trash',
            'rectify': 'fa-edit',
            'portability': 'fa-download',
            'object': 'fa-exclamation-triangle'
        }
        return type_icons.get(request_type, 'fa-file')

    @app.template_filter('request_status_badge')
    def request_status_badge_filter(status):
        """Retourne la classe CSS pour le badge de statut de demande RGPD."""
        status_classes = {
            'pending': 'badge-warning',
            'processed': 'badge-success',
            'rejected': 'badge-danger',
            'in_progress': 'badge-info'
        }
        return status_classes.get(status, 'badge-secondary')

if __name__ == "__main__":
    # Tests des fonctions utilitaires
    print("Test des utilitaires système ChronoTech")
    
    # Test de validation email
    try:
        email = validate_email_address("test@chronotech.fr")
        print(f"Email valide: {email}")
    except ValidationError as e:
        print(f"Email invalide: {e}")
    
    # Test de validation téléphone
    try:
        phone = validate_phone_number("01 23 45 67 89")
        print(f"Téléphone valide: {phone}")
    except ValidationError as e:
        print(f"Téléphone invalide: {e}")
    
    # Test de génération de numéro de réclamation
    claim_number = generate_claim_number()
    print(f"Numéro de réclamation généré: {claim_number}")
    
    # Test de formatage de durée
    print(f"Durée formatée (125 min): {format_duration(125)}")
    print(f"Durée formatée (60 min): {format_duration(60)}")
    print(f"Durée formatée (45 min): {format_duration(45)}")
