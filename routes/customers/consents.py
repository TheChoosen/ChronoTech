"""
Module de gestion des consentements RGPD et communications
"""

import json
import pymysql
from datetime import datetime, timedelta
from flask import request, jsonify, session
from core.utils import log_error
from core.database import log_activity
from .utils import get_db_connection, require_role, get_current_user

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
        'active_customer': 365 * 7,  # 7 ans pour client actif
        'inactive_customer': 365 * 3,  # 3 ans pour client inactif
        'technical_data': 365 * 5,  # 5 ans pour données techniques
        'communication': 365 * 2  # 2 ans pour communications
    },
    'audit_requirements': {
        'log_consent_changes': True,
        'log_data_access': True,
        'anonymize_after_retention': True,
        'consent_renewal_period': 365 * 2  # Renouvellement tous les 2 ans
    }
}


def fetch_customer_consents(customer_id):
    """Récupère les consentements d'un client (fonction utilitaire)"""
    try:
        conn = get_db_connection()
        if not conn:
            return {}
            
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
        if not conn:
            return False
            
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
        consents = fetch_customer_consents(customer_id)
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
        consents = fetch_customer_consents(customer_id)
        
        # Vérifications de base
        if 'data_processing' not in consents or not consents['data_processing']['granted']:
            return False, "Consentement traitement données manquant"
        
        if communication_type == 'marketing':
            if 'marketing' not in consents or not consents['marketing']['granted']:
                return False, "Consentement marketing manquant"
        
        # Vérifier si le client n'est pas en opposition
        conn = get_db_connection()
        if not conn:
            return False, "Erreur technique"
            
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


# Routes API pour les consentements (à importer dans le blueprint principal)
def setup_consent_routes(bp):
    """Configure les routes de gestion des consentements"""
    
    @bp.route('/api/customer/<int:customer_id>/consents', methods=['GET'])
    @require_role(['admin', 'manager', 'technician'])
    def get_customer_consents_api(customer_id):
        """API pour récupérer les consentements d'un client"""
        try:
            consents = fetch_customer_consents(customer_id)
            compliance = check_consent_compliance(customer_id)
            
            return jsonify({
                'success': True,
                'consents': consents,
                'compliance': compliance,
                'config': CONSENT_CONFIG['required_consents']
            })
        except Exception as e:
            log_error(f"Erreur API consentements: {e}")
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
            
            user = get_current_user()
            if not user:
                return jsonify({'success': False, 'message': 'Utilisateur non authentifié'}), 401
            
            success = update_customer_consent(customer_id, consent_type, granted, user.id, source)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f"Consentement {consent_type} mis à jour"
                })
            else:
                return jsonify({'success': False, 'message': 'Erreur mise à jour'}), 500
                
        except Exception as e:
            log_error(f"Erreur API mise à jour consentement: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/api/customer/<int:customer_id>/communication-check', methods=['POST'])
    @require_role(['admin', 'manager', 'technician'])
    def check_communication_permission(customer_id):
        """API pour vérifier les permissions de communication"""
        try:
            data = request.get_json()
            communication_type = data.get('type', 'marketing')
            
            allowed, message = can_send_communication(customer_id, communication_type)
            
            return jsonify({
                'success': True,
                'allowed': allowed,
                'message': message,
                'communication_type': communication_type
            })
        except Exception as e:
            log_error(f"Erreur vérification permission communication: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
