"""
Routes API pour Customer 360 - Support du lazy loading et intégration temps réel
"""

from flask import Blueprint, jsonify, render_template, request, current_app
from core.database import DatabaseManager
import json
from datetime import datetime, timedelta
import logging

# Blueprint pour les API Customer 360
customer360_api = Blueprint('customer360_api', __name__, url_prefix='/api/customers')

logger = logging.getLogger(__name__)

# Instance du gestionnaire de base de données
db_manager = DatabaseManager()

@customer360_api.route('/<int:customer_id>/profile')
def get_customer_profile(customer_id):
    """
    Récupère les informations de profil d'un client
    """
    try:
        connection = db_manager.get_connection()
        if not connection:
            return jsonify({'success': False, 'error': 'Erreur de connexion à la base de données'}), 500
            
        cursor = connection.cursor()
        
        # Récupérer les informations de base du client
        query = """
        SELECT id, name, company, email, phone, mobile, customer_type, 
               created_at, last_activity_date, status, is_active
        FROM customers 
        WHERE id = %s
        """
        cursor.execute(query, (customer_id,))
        customer = cursor.fetchone()
        
        if not customer:
            return jsonify({'success': False, 'error': 'Client non trouvé'}), 404
            
        # Convertir en dict si nécessaire (PyMySQL retourne déjà des dicts avec DictCursor)
        if isinstance(customer, tuple):
            customer = {
                'id': customer[0],
                'name': customer[1], 
                'company': customer[2],
                'email': customer[3],
                'phone': customer[4],
                'mobile': customer[5],
                'customer_type': customer[6],
                'created_at': customer[7],
                'last_activity_date': customer[8],
                'status': customer[9],
                'is_active': customer[10]
            }
        
        # Récupérer quelques statistiques rapides
        stats_query = """
        SELECT 
            COUNT(DISTINCT wo.id) as total_work_orders,
            COUNT(DISTINCT v.id) as total_vehicles,
            COALESCE(SUM(COALESCE(wo.actual_cost, wo.estimated_cost, 0)), 0) as total_revenue
        FROM customers c
        LEFT JOIN work_orders wo ON c.id = wo.customer_id  
        LEFT JOIN vehicles v ON c.id = v.customer_id
        WHERE c.id = %s
        """
        cursor.execute(stats_query, (customer_id,))
        stats = cursor.fetchone()
        
        if isinstance(stats, tuple):
            stats = {
                'total_work_orders': stats[0] or 0,
                'total_vehicles': stats[1] or 0, 
                'total_revenue': float(stats[2]) if stats[2] else 0.0
            }
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'customer': customer,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du profil pour le client {customer_id}: {e}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500


@customer360_api.route('/<int:customer_id>/sections/<section_name>')
def load_section(customer_id, section_name):
    """
    Endpoint pour le lazy loading des sections Customer 360
    """
    try:
        # Vérifier que la section est valide
        valid_sections = ['profile', 'activity', 'finances', 'documents', 'analytics', 'consents']
        if section_name not in valid_sections:
            return jsonify({'error': 'Section invalide'}), 400
        
        # Récupérer les données du client
        customer = get_customer_data(customer_id)
        if not customer:
            return jsonify({'error': 'Client non trouvé'}), 404
        
        # Charger les données spécifiques à la section
        section_data = get_section_data(customer_id, section_name)
        
        # Rendre le template de la section
        template_path = f'customers/_sections/{section_name}.html'
        
        # Préparer le contexte selon la section
        context = prepare_section_context(customer, section_name, section_data)
        
        html = render_template(template_path, **context)
        return html
        
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la section {section_name} pour le client {customer_id}: {str(e)}")
        return jsonify({'error': 'Erreur serveur'}), 500

@customer360_api.route('/<int:customer_id>/activity')
def get_customer_activity(customer_id):
    """
    API pour récupérer l'activité client avec pagination et filtres
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        search = request.args.get('search', '')
        activity_type = request.args.get('type', '')
        period = request.args.get('period', '')
        
        # Construire la requête
        connection = db_manager.get_connection()
        cursor = connection.cursor()
        
        # Base query
        base_query = """
        SELECT 
            id,
            activity_type,
            title,
            description,
            reference_data,
            created_at,
            actor_name
        FROM customer_activities 
        WHERE customer_id = %s
        """
        
        params = [customer_id]
        conditions = []
        
        # Ajouter les filtres
        if search:
            conditions.append("(title LIKE %s OR description LIKE %s)")
            params.extend([f'%{search}%', f'%{search}%'])
        
        if activity_type:
            conditions.append("activity_type = %s")
            params.append(activity_type)
        
        if period:
            period_conditions = get_period_condition(period)
            if period_conditions:
                conditions.append(period_conditions['condition'])
                params.extend(period_conditions['params'])
        
        # Ajouter les conditions à la requête
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        # Compter le total
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as filtered"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['total']
        
        # Ajouter la pagination
        base_query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(base_query, params)
        activities = cursor.fetchall()
        
        # Formater les dates
        for activity in activities:
            if activity['created_at']:
                activity['created_at'] = activity['created_at'].isoformat()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'activities': activities,
            'total_count': total_count,
            'has_more': (page * per_page) < total_count,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'activité pour le client {customer_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500

@customer360_api.route('/<int:customer_id>/invoices')
def get_customer_invoices(customer_id):
    """
    API pour récupérer les factures client avec filtres
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        status = request.args.get('status', '')
        
        connection = db_manager.get_connection()
        cursor = connection.cursor()
        
        base_query = """
        SELECT 
            id,
            number,
            created_at,
            due_date,
            total_amount,
            status
        FROM invoices 
        WHERE customer_id = %s
        """
        
        params = [customer_id]
        
        if status:
            base_query += " AND status = %s"
            params.append(status)
        
        # Compter le total
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as filtered"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['total']
        
        # Ajouter la pagination
        base_query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(base_query, params)
        invoices = cursor.fetchall()
        
        # Formater les données
        for invoice in invoices:
            if invoice['created_at']:
                invoice['created_at'] = invoice['created_at'].isoformat()
            if invoice['due_date']:
                invoice['due_date'] = invoice['due_date'].isoformat()
            invoice['total_amount'] = float(invoice['total_amount']) if invoice['total_amount'] else 0
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'invoices': invoices,
            'total_count': total_count,
            'has_more': (page * per_page) < total_count
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des factures pour le client {customer_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500

@customer360_api.route('/<int:customer_id>/documents')
def get_customer_documents(customer_id):
    """
    API pour récupérer les documents client avec filtres
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 12))
        search = request.args.get('search', '')
        doc_type = request.args.get('type', '')
        status = request.args.get('status', '')
        
        connection = db_manager.get_connection()
        cursor = connection.cursor()
        
        base_query = """
        SELECT 
            id,
            title,
            filename,
            file_size,
            document_type,
            status,
            is_signed,
            created_at,
            updated_at
        FROM customer_documents 
        WHERE customer_id = %s
        """
        
        params = [customer_id]
        conditions = []
        
        if search:
            conditions.append("(title LIKE %s OR filename LIKE %s)")
            params.extend([f'%{search}%', f'%{search}%'])
        
        if doc_type:
            conditions.append("document_type = %s")
            params.append(doc_type)
        
        if status:
            conditions.append("status = %s")
            params.append(status)
        
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        # Compter le total
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as filtered"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['total']
        
        # Ajouter la pagination
        base_query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(base_query, params)
        documents = cursor.fetchall()
        
        # Formater les données
        for doc in documents:
            if doc['created_at']:
                doc['created_at'] = doc['created_at'].isoformat()
            if doc['updated_at']:
                doc['updated_at'] = doc['updated_at'].isoformat()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'documents': documents,
            'total_count': total_count,
            'has_more': (page * per_page) < total_count
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des documents pour le client {customer_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500

@customer360_api.route('/<int:customer_id>/analytics')
def get_customer_analytics(customer_id):
    """
    API pour récupérer les données analytics du client
    """
    try:
        period = request.args.get('period', '6m')
        
        # Récupérer les données analytics
        analytics_data = calculate_customer_analytics(customer_id, period)
        
        return jsonify({
            'success': True,
            **analytics_data
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des analytics pour le client {customer_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500

@customer360_api.route('/<int:customer_id>/revenue-chart')
def get_revenue_chart_data(customer_id):
    """
    API pour les données du graphique de revenus
    """
    try:
        period = request.args.get('period', '6m')
        
        # Calculer les données selon la période
        end_date = datetime.now()
        if period == '6m':
            start_date = end_date - timedelta(days=180)
            interval = 'month'
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
            interval = 'month'
        elif period == '2y':
            start_date = end_date - timedelta(days=730)
            interval = 'quarter'
        else:
            start_date = end_date - timedelta(days=180)
            interval = 'month'
        
        connection = db_manager.get_connection()
        cursor = connection.cursor()
        
        # Requête pour les revenus par période
        if interval == 'month':
            query = """
            SELECT 
                DATE_FORMAT(created_at, '%%Y-%%m') as period,
                SUM(total_amount) as revenue
            FROM invoices 
            WHERE customer_id = %s 
            AND created_at >= %s 
            AND status = 'paid'
            GROUP BY DATE_FORMAT(created_at, '%%Y-%%m')
            ORDER BY period
            """
        else:  # quarter
            query = """
            SELECT 
                CONCAT(YEAR(created_at), '-Q', QUARTER(created_at)) as period,
                SUM(total_amount) as revenue
            FROM invoices 
            WHERE customer_id = %s 
            AND created_at >= %s 
            AND status = 'paid'
            GROUP BY YEAR(created_at), QUARTER(created_at)
            ORDER BY period
            """
        
        cursor.execute(query, [customer_id, start_date])
        results = cursor.fetchall()
        
        labels = [result['period'] for result in results]
        values = [float(result['revenue']) if result['revenue'] else 0 for result in results]
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'labels': labels,
            'values': values
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données de revenus pour le client {customer_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500

@customer360_api.route('/<int:customer_id>/consents')
def get_customer_consents(customer_id):
    """
    API pour récupérer les consentements RGPD du client
    """
    try:
        connection = db_manager.get_connection()
        cursor = connection.cursor()
        
        query = """
        SELECT 
            c.id,
            c.consent_type,
            c.purpose_description,
            c.legal_basis,
            c.is_active,
            c.consent_given_at,
            c.consent_withdrawn_at,
            c.source,
            c.created_at
        FROM customer_consents c
        WHERE c.customer_id = %s
        ORDER BY c.created_at DESC
        """
        
        cursor.execute(query, [customer_id])
        consents = cursor.fetchall()
        
        # Calculer le statut RGPD global
        gdpr_status = calculate_gdpr_status(customer_id, consents)
        
        # Formater les dates et adapter aux nouveaux noms de colonnes
        for consent in consents:
            if consent.get('consent_given_at'):
                consent['granted_at'] = consent['consent_given_at'].isoformat()
                consent['granted'] = consent['is_active']
            if consent.get('consent_withdrawn_at'):
                consent['withdrawn_at'] = consent['consent_withdrawn_at'].isoformat()
            consent['purpose'] = consent.get('consent_type')
            consent['description'] = consent.get('purpose_description')
            if consent['created_at']:
                consent['created_at'] = consent['created_at'].isoformat()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'consents': consents,
            'gdpr_status': gdpr_status
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des consentements pour le client {customer_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500

@customer360_api.route('/<int:customer_id>/send-email', methods=['POST'])
def send_customer_email(customer_id):
    """
    API pour envoyer un email rapide au client
    """
    try:
        data = request.get_json()
        subject = data.get('subject', 'Message de ChronoTech')
        message = data.get('message', '')
        
        if not message.strip():
            return jsonify({'success': False, 'error': 'Message requis'}), 400
        
        # Récupérer les infos du client
        customer = get_customer_data(customer_id)
        if not customer or not customer.get('email'):
            return jsonify({'success': False, 'error': 'Email client non trouvé'}), 400
        
        # Envoyer l'email (implémentation à adapter selon votre système d'email)
        success = send_email_to_customer(customer['email'], subject, message, customer)
        
        if success:
            # Enregistrer l'activité
            log_customer_activity(
                customer_id, 
                'communication', 
                'Email envoyé', 
                f'Objet: {subject}',
                json.dumps({'email': customer['email'], 'subject': subject})
            )
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Erreur lors de l\'envoi'}), 500
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi d'email pour le client {customer_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Erreur serveur'}), 500

# Fonctions utilitaires

def get_customer_data(customer_id):
    """Récupérer les données de base du client"""
    try:
        connection = db_manager.get_connection()
        cursor = connection.cursor()
        
        query = """
        SELECT 
            c.*,
            COUNT(DISTINCT v.id) as vehicles_count,
            COUNT(DISTINCT wo.id) as work_orders_count,
            COALESCE(SUM(i.total_amount), 0) as total_spent
        FROM customers c
        LEFT JOIN vehicles v ON c.id = v.customer_id
        LEFT JOIN work_orders wo ON c.id = wo.customer_id
        LEFT JOIN invoices i ON c.id = i.customer_id AND i.status = 'paid'
        WHERE c.id = %s
        GROUP BY c.id
        """
        
        cursor.execute(query, [customer_id])
        customer = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        return customer
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données client {customer_id}: {str(e)}")
        return None

def get_section_data(customer_id, section_name):
    """Récupérer les données spécifiques à une section"""
    data = {}
    
    try:
        if section_name == 'profile':
            # Charger les données pour la section profile
            data['vehicles'] = get_customer_vehicles(customer_id)
            data['addresses'] = get_customer_addresses_data(customer_id)
            data['contacts'] = get_customer_contacts(customer_id)
            data['customer_stats'] = get_customer_basic_stats(customer_id)
        
        elif section_name == 'activity':
            data['activities'] = get_customer_activities(customer_id, limit=5)
            data['activity_stats'] = get_activity_stats(customer_id)
        
        elif section_name == 'finances':
            data['invoices'] = get_customer_invoices_data(customer_id, limit=10)
            data['payments'] = get_customer_payments(customer_id, limit=5)
            data['financial_summary'] = get_financial_summary(customer_id)
        
        elif section_name == 'documents':
            data['documents'] = get_customer_documents_data(customer_id, limit=12)
            data['document_stats'] = get_document_stats(customer_id)
        
        elif section_name == 'analytics':
            data['analytics_data'] = calculate_customer_analytics(customer_id)
            data['analytics_insights'] = generate_customer_insights(customer_id)
            data['recommended_actions'] = get_recommended_actions(customer_id)
        
        elif section_name == 'consents':
            data['consents'] = get_customer_consents_data(customer_id)
            data['gdpr_status'] = calculate_gdpr_status(customer_id)
            data['gdpr_requests'] = get_gdpr_requests(customer_id)
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données pour la section {section_name}: {str(e)}")
    
    return data

def prepare_section_context(customer, section_name, section_data):
    """Préparer le contexte pour le rendu du template de section"""
    context = {
        'customer': customer,
        'active_tab': section_name,
        **section_data
    }
    
    return context

def get_period_condition(period):
    """Générer les conditions SQL pour les filtres de période"""
    now = datetime.now()
    
    conditions = {
        'today': {
            'condition': 'DATE(created_at) = CURDATE()',
            'params': []
        },
        'week': {
            'condition': 'created_at >= %s',
            'params': [now - timedelta(days=7)]
        },
        'month': {
            'condition': 'created_at >= %s',
            'params': [now - timedelta(days=30)]
        },
        'quarter': {
            'condition': 'created_at >= %s',
            'params': [now - timedelta(days=90)]
        },
        'year': {
            'condition': 'created_at >= %s',
            'params': [now - timedelta(days=365)]
        }
    }
    
    return conditions.get(period, None)

def calculate_customer_analytics(customer_id, period='6m'):
    """Calculer les métriques analytics pour un client"""
    # Implementation détaillée des calculs analytics
    # À adapter selon votre structure de données
    return {
        'lifetime_value': 0,
        'avg_frequency': 0,
        'avg_order_value': 0,
        'satisfaction_score': 0,
        'retention_rate': 0,
        'repeat_rate': 0,
        'churn_risk': 0
    }

def log_customer_activity(customer_id, activity_type, title, description, reference_data=None):
    """Enregistrer une activité client"""
    try:
        connection = db_manager.get_connection()
        cursor = connection.cursor()
        
        query = """
        INSERT INTO customer_activities 
        (customer_id, activity_type, title, description, reference_data, created_at, actor_name)
        VALUES (%s, %s, %s, %s, %s, NOW(), 'System')
        """
        
        cursor.execute(query, [customer_id, activity_type, title, description, reference_data])
        connection.commit()
        
        cursor.close()
        connection.close()
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement de l'activité: {str(e)}")
        return False

def send_email_to_customer(email, subject, message, customer):
    """Envoyer un email au client (à implémenter selon votre système)"""
    # Implémentation de l'envoi d'email
    # À adapter selon votre fournisseur d'email (SMTP, SendGrid, etc.)
    try:
        # Placeholder - remplacer par votre logique d'envoi d'email
        logger.info(f"Email envoyé à {email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi d'email: {str(e)}")
        return False

# Fonctions utilitaires additionnelles (stubs à implémenter)
def get_customer_activities(customer_id, limit=10): return []
def get_activity_stats(customer_id): return {}
def get_customer_invoices_data(customer_id, limit=10): return []
def get_customer_payments(customer_id, limit=5): return []
def get_financial_summary(customer_id): return {}
def get_customer_documents_data(customer_id, limit=12): return []
def get_document_stats(customer_id): return {}
def generate_customer_insights(customer_id): return []
def get_recommended_actions(customer_id): return []
def get_customer_consents_data(customer_id): return []
def calculate_gdpr_status(customer_id, consents=None): return {'compliant': True, 'issues': []}
def get_gdpr_requests(customer_id): return []

# Fonctions pour la section profile
def get_customer_vehicles(customer_id):
    """Récupérer les véhicules d'un client"""
    try:
        connection = db_manager.get_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT id, customer_id, make, model, year, license_plate, vin, color, notes, created_at, updated_at
            FROM vehicles 
            WHERE customer_id = %s 
            ORDER BY created_at DESC
        """, [customer_id])
        
        vehicles = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return vehicles or []
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des véhicules pour le client {customer_id}: {str(e)}")
        return []

def get_customer_addresses_data(customer_id):
    """Récupérer les adresses d'un client"""
    try:
        connection = db_manager.get_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT id, customer_id, address_type, label, address_line_1, address_line_2,
                   city, state_province, postal_code, country, latitude, longitude,
                   is_primary, is_verified, delivery_instructions, access_code,
                   contact_name, contact_phone, created_at, updated_at
            FROM customer_addresses 
            WHERE customer_id = %s 
            ORDER BY is_primary DESC, created_at DESC
        """, [customer_id])
        
        addresses = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return addresses or []
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des adresses pour le client {customer_id}: {str(e)}")
        return []

def get_customer_contacts(customer_id):
    """Récupérer les contacts d'un client"""
    try:
        connection = db_manager.get_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT id, customer_id, first_name, last_name, phone, email, role, is_primary, notes, created_at, updated_at
            FROM customer_contacts 
            WHERE customer_id = %s 
            ORDER BY is_primary DESC, created_at DESC
        """, [customer_id])
        
        contacts = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return contacts or []
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des contacts pour le client {customer_id}: {str(e)}")
        return []

def get_customer_basic_stats(customer_id):
    """Récupérer les statistiques de base d'un client"""
    try:
        connection = db_manager.get_connection()
        cursor = connection.cursor()
        
        # Statistiques de base
        stats = {
            'total_orders': 0,
            'total_revenue': 0,
            'total_interventions': 0,
            'avg_rating': 0
        }
        
        # Nombre de commandes/bons de travail
        cursor.execute("""
            SELECT COUNT(*) as total_orders, 
                   COALESCE(SUM(total_amount), 0) as total_revenue
            FROM work_orders 
            WHERE customer_id = %s
        """, [customer_id])
        
        result = cursor.fetchone()
        if result:
            stats['total_orders'] = result['total_orders'] or 0
            stats['total_revenue'] = float(result['total_revenue'] or 0)
        
        # Nombre d'interventions
        cursor.execute("""
            SELECT COUNT(*) as total_interventions
            FROM interventions 
            WHERE customer_id = %s
        """, [customer_id])
        
        result = cursor.fetchone()
        if result:
            stats['total_interventions'] = result['total_interventions'] or 0
        
        # Note moyenne (si vous avez un système de notation)
        # cursor.execute pour récupérer les évaluations si disponibles
        
        cursor.close()
        connection.close()
        
        return stats
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques pour le client {customer_id}: {str(e)}")
        return {'total_orders': 0, 'total_revenue': 0, 'total_interventions': 0, 'avg_rating': 0}
