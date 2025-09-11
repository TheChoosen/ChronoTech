"""
Sprint 6 - API Publique Simplifiée avec Documentation
Routes API pour intégrations partenaires
"""

from flask import Blueprint, request, jsonify, session, render_template_string
import pymysql
from core.database import get_db_connection
from core.rbac_advanced import permission_manager, audit_logger, security_logger
from core.utils import log_info, log_error
import hashlib
import secrets
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional

# Création du blueprint
api_public_bp = Blueprint('api_public', __name__, url_prefix='/api/v1')

# ============================================================================
# GESTION DES TOKENS API
# ============================================================================

class APITokenManager:
    """Gestionnaire des tokens API pour les partenaires"""
    
    @staticmethod
    def generate_token(partner_name: str, permissions: List[str], created_by: int,
                      expires_days: int = 365, rate_limit: int = 1000) -> tuple:
        """Génère un nouveau token API"""
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
# DÉCORATEUR D'AUTHENTIFICATION API
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
                return jsonify({'error': 'Token d\'authentification requis'}), 401
            
            # Valider le token
            token_data = APITokenManager.validate_token(token)
            if not token_data:
                security_logger.log_unauthorized_access(
                    None, request.endpoint,
                    request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
                    request.headers.get('User-Agent', ''),
                    {'reason': 'Invalid API token'}
                )
                return jsonify({'error': 'Token invalide ou expiré'}), 401
            
            # Vérifier les permissions si requises
            if required_permissions:
                token_permissions = json.loads(token_data.get('permissions', '[]'))
                
                missing_permissions = set(required_permissions) - set(token_permissions)
                if missing_permissions:
                    return jsonify({
                        'error': 'Permissions insuffisantes',
                        'required': list(missing_permissions)
                    }), 403
            
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
# ROUTES WORK ORDERS API
# ============================================================================

@api_public_bp.route('/work_orders', methods=['GET'])
@require_api_auth(['work_orders.view_all'])
def get_work_orders():
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
                
                # Convertir les datetime en string pour JSON
                for wo in work_orders:
                    for key, value in wo.items():
                        if isinstance(value, datetime):
                            wo[key] = value.isoformat()
                
                # Calculer les pages
                pages = (total + per_page - 1) // per_page
                
                return jsonify({
                    'success': True,
                    'data': work_orders,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'pages': pages
                    }
                })
                
    except Exception as e:
        log_error(f"Erreur API get_work_orders: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@api_public_bp.route('/work_orders', methods=['POST'])
@require_api_auth(['work_orders.create'])
def create_work_order():
    """Crée un nouveau bon de travail"""
    try:
        data = request.get_json()
        
        # Validation des données requises
        required_fields = ['title', 'priority', 'customer_id']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Champ requis manquant: {field}'}), 400
        
        # Vérifier que le client existe
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM customers WHERE id = %s", (data['customer_id'],))
                if not cursor.fetchone():
                    return jsonify({'error': 'Client introuvable'}), 400
                
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
                
                # Convertir datetime pour JSON
                for key, value in created_wo.items():
                    if isinstance(value, datetime):
                        created_wo[key] = value.isoformat()
                
                # Logger l'action
                audit_logger.log_action(
                    None, 'create', 'work_orders', str(work_order_id),
                    new_values=data,
                    endpoint=request.endpoint,
                    http_method=request.method,
                    response_status=201
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Bon de travail créé avec succès',
                    'data': created_wo
                }), 201
                
    except Exception as e:
        log_error(f"Erreur API create_work_order: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@api_public_bp.route('/work_orders/<int:work_order_id>', methods=['GET'])
@require_api_auth(['work_orders.view_all'])
def get_work_order(work_order_id):
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
                    return jsonify({'error': 'Bon de travail introuvable'}), 404
                
                # Convertir datetime pour JSON
                for key, value in work_order.items():
                    if isinstance(value, datetime):
                        work_order[key] = value.isoformat()
                
                return jsonify({
                    'success': True,
                    'data': work_order
                })
                
    except Exception as e:
        log_error(f"Erreur API get_work_order: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

# ============================================================================
# ROUTES CUSTOMERS API
# ============================================================================

@api_public_bp.route('/customers', methods=['GET'])
@require_api_auth(['customers.view'])
def get_customers():
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
                
                # Convertir datetime pour JSON
                for customer in customers:
                    for key, value in customer.items():
                        if isinstance(value, datetime):
                            customer[key] = value.isoformat()
                
                pages = (total + per_page - 1) // per_page
                
                return jsonify({
                    'success': True,
                    'data': customers,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'pages': pages
                    }
                })
                
    except Exception as e:
        log_error(f"Erreur API get_customers: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@api_public_bp.route('/customers', methods=['POST'])
@require_api_auth(['customers.create'])
def create_customer():
    """Crée un nouveau client"""
    try:
        data = request.get_json()
        
        # Validation
        if not data.get('name'):
            return jsonify({'error': 'Le nom est requis'}), 400
        
        if not data.get('type') or data['type'] not in ['individual', 'company', 'government']:
            return jsonify({'error': 'Type de client invalide'}), 400
        
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
                
                # Convertir datetime pour JSON
                for key, value in created_customer.items():
                    if isinstance(value, datetime):
                        created_customer[key] = value.isoformat()
                
                audit_logger.log_action(
                    None, 'create', 'customers', str(customer_id),
                    new_values=data,
                    endpoint=request.endpoint,
                    http_method=request.method,
                    response_status=201
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Client créé avec succès',
                    'data': created_customer
                }), 201
                
    except Exception as e:
        log_error(f"Erreur API create_customer: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

# ============================================================================
# DOCUMENTATION API STATIQUE
# ============================================================================

@api_public_bp.route('/docs')
def api_documentation():
    """Documentation API en HTML statique"""
    doc_html = """
<!DOCTYPE html>
<html>
<head>
    <title>ChronoTech API Documentation</title>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        h3 { color: #7f8c8d; }
        .endpoint { background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .method { display: inline-block; padding: 3px 8px; border-radius: 3px; color: white; font-size: 12px; font-weight: bold; }
        .get { background: #27ae60; }
        .post { background: #e74c3c; }
        .put { background: #f39c12; }
        .delete { background: #e67e22; }
        .code { background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto; }
        .auth-info { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .response-example { background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; margin: 10px 0; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #f2f2f2; }
    </style>
</head>
<body>
    <div class="container">
        <h1>ChronoTech API Documentation v1.0</h1>
        <p>API publique pour intégrations partenaires - Système de gestion d'interventions</p>
        
        <div class="auth-info">
            <h3>🔐 Authentification</h3>
            <p>Toutes les requêtes API doivent inclure un token d'authentification dans l'en-tête :</p>
            <div class="code">Authorization: Bearer YOUR_API_TOKEN</div>
            <p>ou</p>
            <div class="code">X-API-Key: YOUR_API_TOKEN</div>
            <p>Contactez votre administrateur ChronoTech pour obtenir un token API.</p>
        </div>

        <h2>📋 Endpoints Work Orders</h2>
        
        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/v1/work_orders</h3>
            <p>Récupère la liste des bons de travail avec pagination</p>
            <h4>Paramètres de requête:</h4>
            <table>
                <tr><th>Paramètre</th><th>Type</th><th>Description</th></tr>
                <tr><td>page</td><td>int</td><td>Numéro de page (défaut: 1)</td></tr>
                <tr><td>per_page</td><td>int</td><td>Éléments par page (défaut: 50, max: 200)</td></tr>
                <tr><td>status</td><td>string</td><td>Filtrer par statut (pending, assigned, in_progress, completed, cancelled)</td></tr>
                <tr><td>priority</td><td>string</td><td>Filtrer par priorité (low, normal, high, urgent)</td></tr>
                <tr><td>technician_id</td><td>int</td><td>Filtrer par technicien assigné</td></tr>
            </table>
            <h4>Permissions requises:</h4>
            <ul><li>work_orders.view_all</li></ul>
            <div class="response-example">
                <strong>Exemple de réponse:</strong>
                <div class="code">{
  "success": true,
  "data": [
    {
      "id": 123,
      "claim_number": "WO-20250908-A1B2C3D4",
      "title": "Réparation système électrique",
      "description": "Intervention urgente sur le tableau principal",
      "status": "assigned",
      "priority": "high",
      "customer_id": 456,
      "customer_name": "Entreprise ABC Inc.",
      "assigned_technician_id": 789,
      "assigned_technician_name": "Jean Dupont",
      "scheduled_date": "2025-09-10T09:00:00",
      "created_at": "2025-09-08T14:30:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 127,
    "pages": 3
  }
}</div>
            </div>
        </div>

        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/v1/work_orders</h3>
            <p>Crée un nouveau bon de travail</p>
            <h4>Corps de la requête (JSON):</h4>
            <table>
                <tr><th>Champ</th><th>Type</th><th>Requis</th><th>Description</th></tr>
                <tr><td>title</td><td>string</td><td>✓</td><td>Titre du bon de travail</td></tr>
                <tr><td>description</td><td>string</td><td></td><td>Description détaillée</td></tr>
                <tr><td>priority</td><td>string</td><td>✓</td><td>Priorité (low, normal, high, urgent)</td></tr>
                <tr><td>customer_id</td><td>int</td><td>✓</td><td>ID du client</td></tr>
                <tr><td>scheduled_date</td><td>datetime</td><td></td><td>Date prévue (format ISO 8601)</td></tr>
                <tr><td>assigned_technician_id</td><td>int</td><td></td><td>ID du technicien à assigner</td></tr>
            </table>
            <h4>Permissions requises:</h4>
            <ul><li>work_orders.create</li></ul>
        </div>

        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/v1/work_orders/{id}</h3>
            <p>Récupère les détails d'un bon de travail spécifique</p>
            <h4>Permissions requises:</h4>
            <ul><li>work_orders.view_all</li></ul>
        </div>

        <h2>👥 Endpoints Customers</h2>

        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/v1/customers</h3>
            <p>Récupère la liste des clients avec pagination</p>
            <h4>Paramètres de requête:</h4>
            <table>
                <tr><th>Paramètre</th><th>Type</th><th>Description</th></tr>
                <tr><td>page</td><td>int</td><td>Numéro de page (défaut: 1)</td></tr>
                <tr><td>per_page</td><td>int</td><td>Éléments par page (défaut: 50, max: 200)</td></tr>
                <tr><td>type</td><td>string</td><td>Filtrer par type (individual, company, government)</td></tr>
                <tr><td>search</td><td>string</td><td>Recherche par nom ou email</td></tr>
            </table>
            <h4>Permissions requises:</h4>
            <ul><li>customers.view</li></ul>
        </div>

        <div class="endpoint">
            <h3><span class="method post">POST</span> /api/v1/customers</h3>
            <p>Crée un nouveau client</p>
            <h4>Corps de la requête (JSON):</h4>
            <table>
                <tr><th>Champ</th><th>Type</th><th>Requis</th><th>Description</th></tr>
                <tr><td>name</td><td>string</td><td>✓</td><td>Nom du client</td></tr>
                <tr><td>email</td><td>string</td><td></td><td>Adresse email</td></tr>
                <tr><td>phone</td><td>string</td><td></td><td>Numéro de téléphone</td></tr>
                <tr><td>type</td><td>string</td><td>✓</td><td>Type (individual, company, government)</td></tr>
                <tr><td>address</td><td>string</td><td></td><td>Adresse</td></tr>
                <tr><td>city</td><td>string</td><td></td><td>Ville</td></tr>
                <tr><td>postal_code</td><td>string</td><td></td><td>Code postal</td></tr>
            </table>
            <h4>Permissions requises:</h4>
            <ul><li>customers.create</li></ul>
        </div>

        <h2>🔧 Endpoint Utilitaire</h2>

        <div class="endpoint">
            <h3><span class="method get">GET</span> /api/v1/health</h3>
            <p>Vérification de l'état de l'API</p>
            <p>Aucune authentification requise</p>
            <div class="response-example">
                <strong>Réponse:</strong>
                <div class="code">{
  "status": "healthy",
  "version": "1.0",
  "timestamp": "2025-09-08T16:45:30",
  "endpoints": {
    "documentation": "/api/v1/docs/",
    "work_orders": "/api/v1/work_orders",
    "customers": "/api/v1/customers"
  }
}</div>
            </div>
        </div>

        <h2>📊 Codes de Réponse</h2>
        <table>
            <tr><th>Code</th><th>Description</th></tr>
            <tr><td>200</td><td>Succès</td></tr>
            <tr><td>201</td><td>Créé avec succès</td></tr>
            <tr><td>400</td><td>Requête invalide</td></tr>
            <tr><td>401</td><td>Non authentifié</td></tr>
            <tr><td>403</td><td>Permissions insuffisantes</td></tr>
            <tr><td>404</td><td>Ressource introuvable</td></tr>
            <tr><td>500</td><td>Erreur serveur</td></tr>
        </table>

        <h2>💡 Exemples d'Utilisation</h2>
        
        <h3>Créer un bon de travail avec curl:</h3>
        <div class="code">curl -X POST https://yourserver/api/v1/work_orders \\
  -H "Authorization: Bearer YOUR_API_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "Maintenance préventive système HVAC",
    "description": "Inspection annuelle et remplacement filtres",
    "priority": "normal",
    "customer_id": 123,
    "scheduled_date": "2025-09-15T10:00:00"
  }'</div>

        <h3>Récupérer les bons de travail urgents:</h3>
        <div class="code">curl -X GET "https://yourserver/api/v1/work_orders?priority=urgent&status=pending" \\
  -H "Authorization: Bearer YOUR_API_TOKEN"</div>

        <p><strong>Contact Support:</strong> support@chronotech.fr</p>
        <p><strong>Version API:</strong> 1.0 | <strong>Dernière mise à jour:</strong> Sept 2025</p>
    </div>
</body>
</html>
    """
    return doc_html

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
            'success': True,
            'token': token,
            'token_id': token_id,
            'partner_name': data['partner_name'],
            'permissions': data['permissions'],
            'expires_days': data.get('expires_days', 365),
            'warning': 'Sauvegardez ce token - il ne sera plus affiché'
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
                
                # Convertir datetime pour JSON
                for token in tokens:
                    for key, value in token.items():
                        if isinstance(value, datetime):
                            token[key] = value.isoformat()
                        elif key == 'permissions':
                            token[key] = json.loads(value) if value else []
                
                return jsonify({'success': True, 'tokens': tokens})
                
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
            'documentation': '/api/v1/docs',
            'work_orders': '/api/v1/work_orders',
            'customers': '/api/v1/customers'
        }
    })
