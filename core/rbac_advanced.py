"""
Sprint 6 - RBAC Avancé avec Permissions Dynamiques
Module de gestion des permissions et contrôle d'accès basé sur les rôles
"""

import pymysql
from flask import session, request, g, jsonify
from functools import wraps
from core.database import get_db_connection
from core.utils import log_info, log_error, log_warning
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import hashlib
import secrets

class PermissionManager:
    """Gestionnaire des permissions dynamiques"""
    
    def __init__(self):
        self._permission_cache = {}
        self._cache_timeout = 300  # 5 minutes
        
    def get_user_permissions(self, user_id: int) -> List[str]:
        """Récupère toutes les permissions effectives d'un utilisateur"""
        cache_key = f"user_permissions_{user_id}"
        
        # Vérifier le cache
        if cache_key in self._permission_cache:
            cached_data = self._permission_cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < timedelta(seconds=self._cache_timeout):
                return cached_data['permissions']
        
        permissions = []
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Récupérer les permissions via la vue
                    cursor.execute("""
                        SELECT DISTINCT permission_name 
                        FROM user_effective_permissions 
                        WHERE user_id = %s 
                        AND source != 'user_denied'
                    """, (user_id,))
                    
                    permissions = [row['permission_name'] for row in cursor.fetchall()]
                    
                    # Mettre en cache
                    self._permission_cache[cache_key] = {
                        'permissions': permissions,
                        'timestamp': datetime.now()
                    }
                    
        except Exception as e:
            log_error(f"Erreur lors de la récupération des permissions pour l'utilisateur {user_id}: {e}")
            
        return permissions
    
    def user_has_permission(self, user_id: int, permission: str) -> bool:
        """Vérifie si un utilisateur a une permission spécifique"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT user_has_permission(%s, %s) as has_permission", 
                                 (user_id, permission))
                    result = cursor.fetchone()
                    return bool(result['has_permission']) if result else False
        except Exception as e:
            log_error(f"Erreur lors de la vérification de permission {permission} pour {user_id}: {e}")
            return False
    
    def get_user_role_permissions(self, user_id: int) -> Dict:
        """Récupère les détails des permissions d'un utilisateur avec leur source"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT permission_name, resource, action, source, role_name
                        FROM user_effective_permissions 
                        WHERE user_id = %s
                        ORDER BY resource, action
                    """, (user_id,))
                    
                    permissions = cursor.fetchall()
                    
                    # Organiser par ressource
                    organized = {}
                    for perm in permissions:
                        resource = perm['resource']
                        if resource not in organized:
                            organized[resource] = []
                        organized[resource].append(perm)
                    
                    return organized
        except Exception as e:
            log_error(f"Erreur lors de la récupération des détails de permissions pour {user_id}: {e}")
            return {}
    
    def grant_permission(self, user_id: int, permission_name: str, granted_by: int, 
                        expires_at: Optional[datetime] = None, reason: str = None) -> bool:
        """Accorde une permission spécifique à un utilisateur"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Récupérer l'ID de la permission
                    cursor.execute("SELECT id FROM system_permissions WHERE name = %s", (permission_name,))
                    perm_result = cursor.fetchone()
                    
                    if not perm_result:
                        log_error(f"Permission {permission_name} introuvable")
                        return False
                        
                    permission_id = perm_result['id']
                    
                    # Insérer ou mettre à jour
                    cursor.execute("""
                        INSERT INTO user_permissions 
                        (user_id, permission_id, is_granted, granted_by, expires_at, reason)
                        VALUES (%s, %s, TRUE, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        is_granted = TRUE,
                        granted_by = %s,
                        expires_at = %s,
                        reason = %s,
                        granted_at = NOW()
                    """, (user_id, permission_id, granted_by, expires_at, reason,
                          granted_by, expires_at, reason))
                    
                    # Invalider le cache
                    cache_key = f"user_permissions_{user_id}"
                    if cache_key in self._permission_cache:
                        del self._permission_cache[cache_key]
                    
                    conn.commit()
                    log_info(f"Permission {permission_name} accordée à l'utilisateur {user_id}")
                    return True
                    
        except Exception as e:
            log_error(f"Erreur lors de l'octroi de permission {permission_name} à {user_id}: {e}")
            return False
    
    def revoke_permission(self, user_id: int, permission_name: str, revoked_by: int, 
                         reason: str = None) -> bool:
        """Révoque une permission spécifique d'un utilisateur"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Récupérer l'ID de la permission
                    cursor.execute("SELECT id FROM system_permissions WHERE name = %s", (permission_name,))
                    perm_result = cursor.fetchone()
                    
                    if not perm_result:
                        return False
                        
                    permission_id = perm_result['id']
                    
                    # Marquer comme révoquée
                    cursor.execute("""
                        INSERT INTO user_permissions 
                        (user_id, permission_id, is_granted, granted_by, reason)
                        VALUES (%s, %s, FALSE, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        is_granted = FALSE,
                        granted_by = %s,
                        reason = %s,
                        granted_at = NOW()
                    """, (user_id, permission_id, revoked_by, reason, revoked_by, reason))
                    
                    # Invalider le cache
                    cache_key = f"user_permissions_{user_id}"
                    if cache_key in self._permission_cache:
                        del self._permission_cache[cache_key]
                    
                    conn.commit()
                    log_info(f"Permission {permission_name} révoquée pour l'utilisateur {user_id}")
                    return True
                    
        except Exception as e:
            log_error(f"Erreur lors de la révocation de permission {permission_name} pour {user_id}: {e}")
            return False

class SecurityEventLogger:
    """Logger pour les événements de sécurité"""
    
    @staticmethod
    def log_unauthorized_access(user_id: Optional[int], resource: str, 
                               ip_address: str, user_agent: str, details: Dict = None):
        """Log une tentative d'accès non autorisé"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO security_events 
                        (event_type, severity, user_id, ip_address, user_agent, 
                         requested_resource, details)
                        VALUES ('unauthorized_access', 'medium', %s, %s, %s, %s, %s)
                    """, (user_id, ip_address, user_agent, resource, 
                          json.dumps(details) if details else None))
                    conn.commit()
        except Exception as e:
            log_error(f"Erreur lors du logging d'événement sécurité: {e}")
    
    @staticmethod
    def log_permission_denied(user_id: int, permission: str, resource: str,
                             ip_address: str, user_agent: str):
        """Log un refus de permission"""
        details = {
            'permission_requested': permission,
            'resource': resource,
            'timestamp': datetime.now().isoformat()
        }
        
        SecurityEventLogger.log_unauthorized_access(
            user_id, resource, ip_address, user_agent, details
        )
    
    @staticmethod
    def get_security_events(limit: int = 100, severity: str = None) -> List[Dict]:
        """Récupère les événements de sécurité récents"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    where_clause = ""
                    params = []
                    
                    if severity:
                        where_clause = "WHERE severity = %s"
                        params.append(severity)
                    
                    cursor.execute(f"""
                        SELECT se.*, u.name as user_name, u.email as user_email
                        FROM security_events se
                        LEFT JOIN users u ON se.user_id = u.id
                        {where_clause}
                        ORDER BY se.created_at DESC
                        LIMIT %s
                    """, params + [limit])
                    
                    return cursor.fetchall()
        except Exception as e:
            log_error(f"Erreur lors de la récupération des événements de sécurité: {e}")
            return []

class AuditLogger:
    """Logger d'audit pour toutes les actions système"""
    
    @staticmethod
    def log_action(user_id: Optional[int], action: str, resource_type: str, 
                  resource_id: str = None, old_values: Dict = None, 
                  new_values: Dict = None, endpoint: str = None,
                  http_method: str = None, response_status: int = None,
                  execution_time_ms: int = None):
        """Log une action dans le système d'audit"""
        try:
            # Récupérer les informations de la requête si disponibles
            ip_address = None
            user_agent = None
            session_id = None
            
            if request:
                ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
                user_agent = request.headers.get('User-Agent', '')
                session_id = session.get('session_id')
            
            # Récupérer l'email utilisateur
            user_email = None
            if user_id:
                try:
                    with get_db_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
                            result = cursor.fetchone()
                            if result:
                                user_email = result['email']
                except Exception:
                    pass
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO audit_logs 
                        (user_id, user_email, action, resource_type, resource_id,
                         old_values, new_values, ip_address, user_agent, session_id,
                         api_endpoint, http_method, response_status, execution_time_ms)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, user_email, action, resource_type, resource_id,
                          json.dumps(old_values) if old_values else None,
                          json.dumps(new_values) if new_values else None,
                          ip_address, user_agent, session_id, endpoint,
                          http_method, response_status, execution_time_ms))
                    conn.commit()
                    
        except Exception as e:
            log_error(f"Erreur lors du logging d'audit: {e}")
    
    @staticmethod
    def get_audit_logs(user_id: int = None, resource_type: str = None, 
                      action: str = None, limit: int = 100, 
                      date_from: datetime = None, date_to: datetime = None) -> List[Dict]:
        """Récupère les logs d'audit avec filtres"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    where_conditions = []
                    params = []
                    
                    if user_id:
                        where_conditions.append("user_id = %s")
                        params.append(user_id)
                    
                    if resource_type:
                        where_conditions.append("resource_type = %s")
                        params.append(resource_type)
                    
                    if action:
                        where_conditions.append("action = %s")
                        params.append(action)
                    
                    if date_from:
                        where_conditions.append("created_at >= %s")
                        params.append(date_from)
                    
                    if date_to:
                        where_conditions.append("created_at <= %s")
                        params.append(date_to)
                    
                    where_clause = ""
                    if where_conditions:
                        where_clause = "WHERE " + " AND ".join(where_conditions)
                    
                    cursor.execute(f"""
                        SELECT * FROM audit_logs 
                        {where_clause}
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, params + [limit])
                    
                    return cursor.fetchall()
        except Exception as e:
            log_error(f"Erreur lors de la récupération des logs d'audit: {e}")
            return []
    
    @staticmethod
    def export_audit_logs(format_type: str = 'json', **filters) -> Union[str, List[Dict]]:
        """Exporte les logs d'audit dans différents formats"""
        logs = AuditLogger.get_audit_logs(**filters)
        
        if format_type.lower() == 'json':
            # Convertir les datetime en string pour JSON
            for log in logs:
                for key, value in log.items():
                    if isinstance(value, datetime):
                        log[key] = value.isoformat()
            return json.dumps(logs, indent=2, ensure_ascii=False)
        
        elif format_type.lower() == 'csv':
            import csv
            import io
            
            if not logs:
                return ""
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=logs[0].keys())
            writer.writeheader()
            
            for log in logs:
                # Convertir les objets complexes en string
                row = {}
                for key, value in log.items():
                    if isinstance(value, (dict, list)):
                        row[key] = json.dumps(value)
                    elif isinstance(value, datetime):
                        row[key] = value.isoformat()
                    else:
                        row[key] = str(value) if value is not None else ""
                writer.writerow(row)
            
            return output.getvalue()
        
        return logs

# Instances globales
permission_manager = PermissionManager()
security_logger = SecurityEventLogger()
audit_logger = AuditLogger()

# ============================================================================
# DÉCORATEURS POUR PROTECTION DES ROUTES
# ============================================================================

def require_permission(permission: str):
    """Décorateur pour exiger une permission spécifique"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                security_logger.log_unauthorized_access(
                    None, request.endpoint or 'unknown',
                    request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
                    request.headers.get('User-Agent', '')
                )
                return jsonify({'error': 'Authentication required'}), 401
            
            user_id = session['user_id']
            
            if not permission_manager.user_has_permission(user_id, permission):
                security_logger.log_permission_denied(
                    user_id, permission, request.endpoint or 'unknown',
                    request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
                    request.headers.get('User-Agent', '')
                )
                return jsonify({'error': 'Permission denied', 'required_permission': permission}), 403
            
            # Log de l'action autorisée
            audit_logger.log_action(
                user_id, 'access', 'endpoint', request.endpoint,
                endpoint=request.endpoint, http_method=request.method
            )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_any_permission(*permissions: str):
    """Décorateur pour exiger au moins une des permissions listées"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Authentication required'}), 401
            
            user_id = session['user_id']
            
            # Vérifier si l'utilisateur a au moins une des permissions
            has_permission = any(
                permission_manager.user_has_permission(user_id, perm) 
                for perm in permissions
            )
            
            if not has_permission:
                security_logger.log_permission_denied(
                    user_id, f"any_of_{','.join(permissions)}", 
                    request.endpoint or 'unknown',
                    request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
                    request.headers.get('User-Agent', '')
                )
                return jsonify({
                    'error': 'Permission denied', 
                    'required_permissions': list(permissions)
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_action(action: str, resource_type: str):
    """Décorateur pour logger automatiquement les actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            start_time = datetime.now()
            
            try:
                result = f(*args, **kwargs)
                
                # Calculer le temps d'exécution
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                # Logger l'action réussie
                audit_logger.log_action(
                    user_id, action, resource_type,
                    endpoint=request.endpoint,
                    http_method=request.method,
                    response_status=200,
                    execution_time_ms=int(execution_time)
                )
                
                return result
                
            except Exception as e:
                # Logger l'erreur
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                audit_logger.log_action(
                    user_id, action, resource_type,
                    endpoint=request.endpoint,
                    http_method=request.method,
                    response_status=500,
                    execution_time_ms=int(execution_time),
                    new_values={'error': str(e)}
                )
                raise
                
        return decorated_function
    return decorator

# ============================================================================
# UTILITAIRES RBAC
# ============================================================================

def get_current_user_permissions() -> List[str]:
    """Récupère les permissions de l'utilisateur actuel"""
    if 'user_id' not in session:
        return []
    return permission_manager.get_user_permissions(session['user_id'])

def current_user_can(permission: str) -> bool:
    """Vérifie si l'utilisateur actuel a une permission"""
    if 'user_id' not in session:
        return False
    return permission_manager.user_has_permission(session['user_id'], permission)

def filter_work_orders_by_permission(work_orders: List[Dict], user_id: int) -> List[Dict]:
    """Filtre les work orders selon les permissions de l'utilisateur (User Story principale)"""
    # Si l'utilisateur peut voir tous les bons de travail
    if permission_manager.user_has_permission(user_id, 'work_orders.view_all'):
        return work_orders
    
    # Si l'utilisateur peut voir seulement ses propres bons
    if permission_manager.user_has_permission(user_id, 'work_orders.view_own'):
        return [wo for wo in work_orders if wo.get('assigned_technician_id') == user_id]
    
    # Aucune permission = aucun bon de travail
    return []

def can_edit_work_order(work_order: Dict, user_id: int) -> bool:
    """Vérifie si un utilisateur peut modifier un work order spécifique"""
    # Admin/Manager peuvent tout éditer
    if permission_manager.user_has_permission(user_id, 'work_orders.edit_all'):
        return True
    
    # Technicien peut éditer seulement ses propres bons
    if permission_manager.user_has_permission(user_id, 'work_orders.edit_own'):
        return work_order.get('assigned_technician_id') == user_id
    
    return False

def get_allowed_actions(resource_type: str, resource_id: str = None) -> List[str]:
    """Récupère les actions autorisées pour une ressource donnée"""
    if 'user_id' not in session:
        return []
        
    user_id = session['user_id']
    permissions = permission_manager.get_user_permissions(user_id)
    
    # Filtrer les permissions pour cette ressource
    allowed_actions = []
    for perm in permissions:
        if perm.startswith(f"{resource_type}."):
            action = perm.split('.')[1]
            allowed_actions.append(action)
    
    return allowed_actions
