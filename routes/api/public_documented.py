"""
Sprint 6 - API Publique Documentée avec Swagger/OpenAPI
Routes API pour intégrations partenaires avec documentation automatique
"""

from flask import Blueprint, request, jsonify, session, current_app
from flask_restx import Api, Resource, fields, Namespace
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, NotFound
import pymysql
from core.database import get_db_connection
from core.rbac_advanced import permission_manager, audit_logger, security_logger
from core.utils import log_info, log_error
import hashlib
import secrets
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional

# Création du blueprint principal
api_public_bp = Blueprint('api_public', __name__, url_prefix='/api/v1')

# Configuration Flask-RESTX pour Swagger
api = Api(
    api_public_bp,
    version='1.0',
    title='ChronoTech API',
    description='API publique pour intégrations partenaires - Système de gestion d\'interventions',
    doc='/docs/',  # URL de la documentation Swagger
    contact='support@chronotech.fr',
    license='Propriétaire',
    authorizations={
        'Bearer': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'Token d\'authentification au format: Bearer <token>'
        },
        'ApiKey': {
            'type': 'apiKey',
            'in': 'header', 
            'name': 'X-API-Key',
            'description': 'Clé API fournie par ChronoTech'
        }
    },
    security=['Bearer', 'ApiKey']
)

# ============================================================================
# GESTION DES TOKENS API
# ============================================================================

class APITokenManager:
    """Gestionnaire des tokens API pour les partenaires"""
    
    @staticmethod
    def generate_token(partner_name: str, permissions: List[str], created_by: int,
                      expires_days: int = 365, rate_limit: int = 1000) -> tuple:
        """Génère un nouveau token API"""
        # Générer le token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        expires_at = datetime.now() + timedelta(days=expires_days)
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO api_tokens 
                        (token_name, token_hash, partner_name, permissions, 
                         rate_limit_per_hour, created_by, expires_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        f"{partner_name}_api_token",
                        token_hash,
                        partner_name,
                        json.dumps(permissions),
                        rate_limit,
                        created_by,
                        expires_at
                    ))
                    
                    token_id = conn.insert_id()
                    conn.commit()
                    
                    log_info(f"Token API créé pour {partner_name} avec {len(permissions)} permissions")
                    
                    return raw_token, token_id
                    
        except Exception as e:
            log_error(f"Erreur lors de la création du token API: {e}")
            return None, None
    
    @staticmethod
    def validate_token(token: str) -> Optional[Dict]:
        """Valide un token API et retourne les informations associées"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT * FROM api_tokens 
                        WHERE token_hash = %s 
                        AND is_active = TRUE 
                        AND (expires_at IS NULL OR expires_at > NOW())
                    """, (token_hash,))
                    
                    token_data = cursor.fetchone()
                    
                    if token_data:
                        # Mettre à jour les statistiques d'usage
                        cursor.execute("""
                            UPDATE api_tokens 
                            SET last_used_at = NOW(), usage_count = usage_count + 1
                            WHERE id = %s
                        """, (token_data['id'],))
                        conn.commit()
                        
                        return token_data
                    
        except Exception as e:
            log_error(f"Erreur lors de la validation du token: {e}")
            
        return None
    
    @staticmethod
    def log_api_usage(token_id: int, endpoint: str, method: str, 
                     status: int, response_time: int = None):
        """Log l'utilisation de l'API"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO api_usage_logs 
                        (token_id, endpoint, http_method, ip_address, 
                         response_status, response_time_ms)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        token_id,
                        endpoint,
                        method,
                        request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
                        status,
                        response_time
                    ))
                    conn.commit()
        except Exception as e:
            log_error(f"Erreur lors du logging d'usage API: {e}")

# ============================================================================
# DÉCORATEURS D'AUTHENTIFICATION API
# ============================================================================

def require_api_auth(required_permissions: List[str] = None):
    """Décorateur pour l'authentification API"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            # Vérifier le token dans les headers
            auth_header = request.headers.get('Authorization', '')
            api_key = request.headers.get('X-API-Key', '')
            
            token = None
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
            elif api_key:
                token = api_key
            
            if not token:
                return {'error': 'Token d\'authentification requis'}, 401
            
            # Valider le token
            token_data = APITokenManager.validate_token(token)
            if not token_data:
                security_logger.log_unauthorized_access(
                    None, request.endpoint,
                    request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
                    request.headers.get('User-Agent', ''),
                    {'reason': 'Invalid API token'}
                )
                return {'error': 'Token invalide ou expiré'}, 401
            
            # Vérifier les permissions si requises
            if required_permissions:
                token_permissions = json.loads(token_data.get('permissions', '[]'))
                
                missing_permissions = set(required_permissions) - set(token_permissions)
                if missing_permissions:
                    return {
                        'error': 'Permissions insuffisantes',
                        'required': list(missing_permissions)
                    }, 403
            
            # Stocker les infos du token pour usage dans la route
            request.api_token = token_data
            
            # Logger l'utilisation
            start_time = datetime.now()
            try:
                result = f(*args, **kwargs)
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                APITokenManager.log_api_usage(
                    token_data['id'], request.endpoint, request.method, 
                    200, int(execution_time)
                )
                return result
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                APITokenManager.log_api_usage(
                    token_data['id'], request.endpoint, request.method, 
                    500, int(execution_time)
                )
                raise
        
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

# ============================================================================
# MODÈLES SWAGGER POUR LA DOCUMENTATION
# ============================================================================

# Modèles de base
error_model = api.model('Error', {
    'error': fields.String(required=True, description='Message d\'erreur'),
    'code': fields.Integer(description='Code d\'erreur'),
    'details': fields.Raw(description='Détails supplémentaires')
})

pagination_model = api.model('Pagination', {
    'page': fields.Integer(required=True, description='Numéro de page'),
    'per_page': fields.Integer(required=True, description='Éléments par page'),
    'total': fields.Integer(required=True, description='Total d\'éléments'),
    'pages': fields.Integer(required=True, description='Nombre total de pages')
})

# Modèles Work Orders
work_order_model = api.model('WorkOrder', {
    'id': fields.Integer(required=True, description='ID unique'),
    'claim_number': fields.String(required=True, description='Numéro de réclamation'),
    'title': fields.String(required=True, description='Titre du bon de travail'),
    'description': fields.String(description='Description détaillée'),
    'status': fields.String(required=True, description='Statut', enum=['pending', 'assigned', 'in_progress', 'completed', 'cancelled']),
    'priority': fields.String(required=True, description='Priorité', enum=['low', 'normal', 'high', 'urgent']),
    'customer_id': fields.Integer(required=True, description='ID du client'),
    'customer_name': fields.String(description='Nom du client'),
    'assigned_technician_id': fields.Integer(description='ID du technicien assigné'),
    'assigned_technician_name': fields.String(description='Nom du technicien'),
    'scheduled_date': fields.DateTime(description='Date prévue'),
    'completed_date': fields.DateTime(description='Date de completion'),
    'created_at': fields.DateTime(required=True, description='Date de création'),
    'updated_at': fields.DateTime(description='Date de dernière modification')
})

work_order_create_model = api.model('WorkOrderCreate', {
    'title': fields.String(required=True, description='Titre du bon de travail'),
    'description': fields.String(description='Description détaillée'),
    'priority': fields.String(required=True, description='Priorité', enum=['low', 'normal', 'high', 'urgent']),
    'customer_id': fields.Integer(required=True, description='ID du client'),
    'scheduled_date': fields.DateTime(description='Date prévue'),
    'assigned_technician_id': fields.Integer(description='ID du technicien à assigner')
})

# Modèles Customer
customer_model = api.model('Customer', {
    'id': fields.Integer(required=True, description='ID unique'),
    'name': fields.String(required=True, description='Nom du client'),
    'email': fields.String(description='Adresse email'),
    'phone': fields.String(description='Téléphone'),
    'type': fields.String(required=True, description='Type de client', enum=['individual', 'company', 'government']),
    'address': fields.String(description='Adresse'),
    'city': fields.String(description='Ville'),
    'postal_code': fields.String(description='Code postal'),
    'is_active': fields.Boolean(description='Client actif'),
    'created_at': fields.DateTime(required=True, description='Date de création')
})

customer_create_model = api.model('CustomerCreate', {
    'name': fields.String(required=True, description='Nom du client'),
    'email': fields.String(description='Adresse email'),
    'phone': fields.String(description='Téléphone'),
    'type': fields.String(required=True, description='Type de client', enum=['individual', 'company', 'government']),
    'address': fields.String(description='Adresse'),
    'city': fields.String(description='Ville'),
    'postal_code': fields.String(description='Code postal')
})

# ============================================================================
# NAMESPACE WORK ORDERS
# ============================================================================

work_orders_ns = Namespace('work_orders', description='Gestion des bons de travail')

@work_orders_ns.route('/')
class WorkOrdersList(Resource):
    @api.doc('get_work_orders')
    @api.marshal_list_with(work_order_model)
    @api.param('page', 'Numéro de page', type=int, default=1)
    @api.param('per_page', 'Éléments par page', type=int, default=50)
    @api.param('status', 'Filtrer par statut')
    @api.param('priority', 'Filtrer par priorité')
    @api.param('technician_id', 'Filtrer par technicien', type=int)
    @api.response(200, 'Liste des bons de travail')
    @api.response(401, 'Non authentifié', error_model)
    @api.response(403, 'Permissions insuffisantes', error_model)
    @require_api_auth(['work_orders.view_all'])
    def get(self):
        """Récupère la liste des bons de travail avec pagination"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 50, type=int), 200)  # Max 200
            status = request.args.get('status')
            priority = request.args.get('priority')
            technician_id = request.args.get('technician_id', type=int)
            
            offset = (page - 1) * per_page
            
            # Construction de la requête avec filtres
            where_conditions = []
            params = []
            
            if status:
                where_conditions.append("wo.status = %s")
                params.append(status)
            
            if priority:
                where_conditions.append("wo.priority = %s") 
                params.append(priority)
                
            if technician_id:
                where_conditions.append("wo.assigned_technician_id = %s")
                params.append(technician_id)
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Compter le total
                    cursor.execute(f"""
                        SELECT COUNT(*) as total 
                        FROM work_orders wo 
                        {where_clause}
                    """, params)
                    total = cursor.fetchone()['total']
                    
                    # Récupérer les données
                    cursor.execute(f"""
                        SELECT wo.*, c.name as customer_name, u.name as assigned_technician_name
                        FROM work_orders wo
                        LEFT JOIN customers c ON wo.customer_id = c.id
                        LEFT JOIN users u ON wo.assigned_technician_id = u.id
                        {where_clause}
                        ORDER BY wo.created_at DESC
                        LIMIT %s OFFSET %s
                    """, params + [per_page, offset])
                    
                    work_orders = cursor.fetchall()
                    
                    # Calculer les pages
                    pages = (total + per_page - 1) // per_page
                    
                    return {
                        'data': work_orders,
                        'pagination': {
                            'page': page,
                            'per_page': per_page,
                            'total': total,
                            'pages': pages
                        }
                    }
                    
        except Exception as e:
            log_error(f"Erreur API get_work_orders: {e}")
            return {'error': 'Erreur serveur'}, 500
    
    @api.doc('create_work_order')
    @api.expect(work_order_create_model)
    @api.marshal_with(work_order_model, code=201)
    @api.response(201, 'Bon de travail créé')
    @api.response(400, 'Données invalides', error_model)
    @api.response(401, 'Non authentifié', error_model)
    @api.response(403, 'Permissions insuffisantes', error_model)
    @require_api_auth(['work_orders.create'])
    def post(self):
        """Crée un nouveau bon de travail"""
        try:
            data = request.get_json()
            
            # Validation des données requises
            required_fields = ['title', 'priority', 'customer_id']
            for field in required_fields:
                if field not in data or not data[field]:
                    return {'error': f'Champ requis manquant: {field}'}, 400
            
            # Vérifier que le client existe
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM customers WHERE id = %s", (data['customer_id'],))
                    if not cursor.fetchone():
                        return {'error': 'Client introuvable'}, 400
                    
                    # Générer un numéro de réclamation unique
                    import uuid
                    claim_number = f"WO-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
                    
                    # Insérer le bon de travail
                    cursor.execute("""
                        INSERT INTO work_orders 
                        (claim_number, title, description, priority, customer_id, 
                         scheduled_date, assigned_technician_id, status, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', NOW())
                    """, (
                        claim_number,
                        data['title'],
                        data.get('description', ''),
                        data['priority'],
                        data['customer_id'],
                        data.get('scheduled_date'),
                        data.get('assigned_technician_id')
                    ))
                    
                    work_order_id = conn.insert_id()
                    conn.commit()
                    
                    # Récupérer le bon de travail créé avec les détails
                    cursor.execute("""
                        SELECT wo.*, c.name as customer_name, u.name as assigned_technician_name
                        FROM work_orders wo
                        LEFT JOIN customers c ON wo.customer_id = c.id
                        LEFT JOIN users u ON wo.assigned_technician_id = u.id
                        WHERE wo.id = %s
                    """, (work_order_id,))
                    
                    created_wo = cursor.fetchone()
                    
                    # Logger l'action
                    audit_logger.log_action(
                        None, 'create', 'work_orders', str(work_order_id),
                        new_values=data,
                        endpoint=request.endpoint,
                        http_method=request.method,
                        response_status=201
                    )
                    
                    return created_wo, 201
                    
        except Exception as e:
            log_error(f"Erreur API create_work_order: {e}")
            return {'error': 'Erreur serveur'}, 500

@work_orders_ns.route('/<int:work_order_id>')
class WorkOrderDetail(Resource):
    @api.doc('get_work_order')
    @api.marshal_with(work_order_model)
    @api.response(200, 'Détails du bon de travail')
    @api.response(404, 'Bon de travail introuvable', error_model)
    @api.response(401, 'Non authentifié', error_model)
    @api.response(403, 'Permissions insuffisantes', error_model)
    @require_api_auth(['work_orders.view_all'])
    def get(self, work_order_id):
        """Récupère les détails d'un bon de travail"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT wo.*, c.name as customer_name, u.name as assigned_technician_name
                        FROM work_orders wo
                        LEFT JOIN customers c ON wo.customer_id = c.id
                        LEFT JOIN users u ON wo.assigned_technician_id = u.id
                        WHERE wo.id = %s
                    """, (work_order_id,))
                    
                    work_order = cursor.fetchone()
                    
                    if not work_order:
                        return {'error': 'Bon de travail introuvable'}, 404
                    
                    return work_order
                    
        except Exception as e:
            log_error(f"Erreur API get_work_order: {e}")
            return {'error': 'Erreur serveur'}, 500

# ============================================================================
# NAMESPACE CUSTOMERS
# ============================================================================

customers_ns = Namespace('customers', description='Gestion des clients')

@customers_ns.route('/')
class CustomersList(Resource):
    @api.doc('get_customers')
    @api.marshal_list_with(customer_model)
    @api.param('page', 'Numéro de page', type=int, default=1)
    @api.param('per_page', 'Éléments par page', type=int, default=50)
    @api.param('type', 'Filtrer par type de client')
    @api.param('search', 'Recherche par nom ou email')
    @api.response(200, 'Liste des clients')
    @api.response(401, 'Non authentifié', error_model)
    @api.response(403, 'Permissions insuffisantes', error_model)
    @require_api_auth(['customers.view'])
    def get(self):
        """Récupère la liste des clients avec pagination"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 50, type=int), 200)
            customer_type = request.args.get('type')
            search = request.args.get('search')
            
            offset = (page - 1) * per_page
            
            # Construction de la requête avec filtres
            where_conditions = ["is_active = TRUE"]
            params = []
            
            if customer_type:
                where_conditions.append("type = %s")
                params.append(customer_type)
            
            if search:
                where_conditions.append("(name LIKE %s OR email LIKE %s)")
                search_term = f"%{search}%"
                params.extend([search_term, search_term])
            
            where_clause = "WHERE " + " AND ".join(where_conditions)
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Compter le total
                    cursor.execute(f"""
                        SELECT COUNT(*) as total 
                        FROM customers 
                        {where_clause}
                    """, params)
                    total = cursor.fetchone()['total']
                    
                    # Récupérer les données
                    cursor.execute(f"""
                        SELECT * FROM customers 
                        {where_clause}
                        ORDER BY name ASC
                        LIMIT %s OFFSET %s
                    """, params + [per_page, offset])
                    
                    customers = cursor.fetchall()
                    
                    pages = (total + per_page - 1) // per_page
                    
                    return {
                        'data': customers,
                        'pagination': {
                            'page': page,
                            'per_page': per_page,
                            'total': total,
                            'pages': pages
                        }
                    }
                    
        except Exception as e:
            log_error(f"Erreur API get_customers: {e}")
            return {'error': 'Erreur serveur'}, 500

    @api.doc('create_customer')
    @api.expect(customer_create_model)
    @api.marshal_with(customer_model, code=201)
    @api.response(201, 'Client créé')
    @api.response(400, 'Données invalides', error_model)
    @api.response(401, 'Non authentifié', error_model)
    @api.response(403, 'Permissions insuffisantes', error_model)
    @require_api_auth(['customers.create'])
    def post(self):
        """Crée un nouveau client"""
        try:
            data = request.get_json()
            
            # Validation
            if not data.get('name'):
                return {'error': 'Le nom est requis'}, 400
            
            if not data.get('type') or data['type'] not in ['individual', 'company', 'government']:
                return {'error': 'Type de client invalide'}, 400
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO customers 
                        (name, email, phone, type, address, city, postal_code, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        data['name'],
                        data.get('email'),
                        data.get('phone'),
                        data['type'],
                        data.get('address'),
                        data.get('city'),
                        data.get('postal_code')
                    ))
                    
                    customer_id = conn.insert_id()
                    conn.commit()
                    
                    # Récupérer le client créé
                    cursor.execute("SELECT * FROM customers WHERE id = %s", (customer_id,))
                    created_customer = cursor.fetchone()
                    
                    audit_logger.log_action(
                        None, 'create', 'customers', str(customer_id),
                        new_values=data,
                        endpoint=request.endpoint,
                        http_method=request.method,
                        response_status=201
                    )
                    
                    return created_customer, 201
                    
        except Exception as e:
            log_error(f"Erreur API create_customer: {e}")
            return {'error': 'Erreur serveur'}, 500

# Enregistrer les namespaces
api.add_namespace(work_orders_ns)
api.add_namespace(customers_ns)

# ============================================================================
# ROUTES D'ADMINISTRATION DES TOKENS API
# ============================================================================

@api_public_bp.route('/admin/tokens', methods=['POST'])
def create_api_token():
    """Crée un nouveau token API (admin seulement)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Vérifier les permissions admin
    if not permission_manager.user_has_permission(session['user_id'], 'system.api_management'):
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.get_json()
    
    if not data.get('partner_name') or not data.get('permissions'):
        return jsonify({'error': 'partner_name et permissions requis'}), 400
    
    token, token_id = APITokenManager.generate_token(
        data['partner_name'],
        data['permissions'],
        session['user_id'],
        data.get('expires_days', 365),
        data.get('rate_limit', 1000)
    )
    
    if token:
        return jsonify({
            'token': token,
            'token_id': token_id,
            'partner_name': data['partner_name'],
            'permissions': data['permissions'],
            'expires_days': data.get('expires_days', 365)
        }), 201
    else:
        return jsonify({'error': 'Erreur lors de la création du token'}), 500

@api_public_bp.route('/admin/tokens', methods=['GET'])
def list_api_tokens():
    """Liste tous les tokens API (admin seulement)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    if not permission_manager.user_has_permission(session['user_id'], 'system.api_management'):
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, token_name, partner_name, permissions, 
                           rate_limit_per_hour, is_active, created_at, 
                           expires_at, last_used_at, usage_count
                    FROM api_tokens
                    ORDER BY created_at DESC
                """)
                
                tokens = cursor.fetchall()
                return jsonify({'tokens': tokens})
                
    except Exception as e:
        log_error(f"Erreur lors de la récupération des tokens: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

# ============================================================================
# ROUTE DE TEST DE L'API
# ============================================================================

@api_public_bp.route('/health', methods=['GET'])
def health_check():
    """Point de santé de l'API"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'documentation': '/api/v1/docs/',
            'work_orders': '/api/v1/work_orders/',
            'customers': '/api/v1/customers/'
        }
    })

# Point d'entrée pour la documentation
@api_public_bp.route('/docs')
def api_docs():
    """Redirection vers la documentation Swagger"""
    from flask import redirect
    return redirect('/api/v1/docs/')

# Route pour obtenir le schéma OpenAPI
@api_public_bp.route('/openapi.json')
def openapi_spec():
    """Retourne la spécification OpenAPI au format JSON"""
    return jsonify(api.__schema__)
